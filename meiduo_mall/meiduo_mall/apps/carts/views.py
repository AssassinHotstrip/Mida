import base64

import pickle
from django.shortcuts import render
from rest_framework import status

from rest_framework.response import Response
from rest_framework.views import APIView
from django_redis import get_redis_connection

from goods.models import SKU
from .serializers import CartSerializer, CartSKUSerializer, CartSelectAllSerializer, CartDeleteSeriazlier


# Create your views here.
class CartView(APIView):
    """购物车视图:增删改查"""

    def perform_authentication(self, request):
        """
        重写认证:
        默认视图在进行请求分发时就会进行认证
        在视图中重写此方法,如果内部直接pass,表示在请求分发时,先不要认证,让请求可以正常访问
        目的:延后它的认证,为了让未登录用户也能先访问该视图
        将来自己去写认证

        说明:
        因为前端请求时携带了authorization请求头(主要是JWT),而如果用户未登录,此请求头的JWT没有意义,为了防止REST framework框架在验证此无意义的JWT时抛出401,在视图中需要做两个处理:
        重写perform_authentication()方法 (DRf检查用户身份的方法)
        获取request.user属性时捕获异常,rest framework在返回user时会检查authorization请求头,若无效则抛出异常
        """
        pass


    # 新增
    def post(self, request):
        """新增"""

        # 创建序列化器,进行反序列化
        serializer = CartSerializer(data=request.data)
        # 校验数据
        serializer.is_valid(raise_exception=True)

        # 取出校验之后的数据
        sku_id = serializer.validated_data.get('sku_id')
        count = serializer.validated_data.get('count')
        selected = serializer.validated_data.get('selected')

        try:
            user = request.user
        except Exception:
            user = None

        # 判断当前是否是登录用户
        if user is not None and user.is_authenticated:
            # 登录用户,redis
            # 获取到连接redis对象
            redis_conn = get_redis_connection('carts')
            # 创建管道
            pl = redis_conn.pipeline()

            # 用哈希来存放商品及其数量
            # card_dict = redis_conn.hgetall('cart_%s' % user.id, sku_id, count)
            # if sku_id in card_dict:
            #     origin_count = card_dict['sku_id']
            #     count += origin_count
            # 以上代码用hincrby(name, key, amount)实现:此方法如果要添加的key在原哈希中不存就是新增,如果key已经存在,就后面的value和原有value相加
            pl.hincrby('cart_%s' % user.id, sku_id, count)
            # 哈希格式:
            # cart_user_idA : {sku_id1: count, sku_id2: count}
            # cart_user_idB : {sku_id1: count, sku_id2: count}


            # 用set记录商品是否被选中:
            if selected:
                # sadd(name, *values)
                # 将被选中的商品sku_id存进该set中
                pl.sadd('selected_%s' % user.id, sku_id)
            # 执行管道
            pl.execute()

            # 响应
            return Response(serializer.data, status=status.HTTP_201_CREATED)



        else:
            # 未登录用户,cookie
            """
            为了方便后续redis数据和cookie数据进行统一的转换,现在把redis中的数据先转的和cookie中的字典数据格式一样
            {
                sku_id_1: {
                    'count': count,
                    'selected: True
                },
                sku_id_2: {
                    'count': count,
                    'selected: True
                }
            }
            """

            # 获取cookie中原有购物车数据
            cookie_str = request.COOKIES.get('cart')

            if cookie_str:
                # 把cookie_str转换成python中的标准字典:
                cart_dict = pickle.loads(base64.b64decode(cookie_str.encode()))
                # 分解:
                #  把cookie_str字符串转换成cookie_str_bytes
                # cookie_str_bytes = cookie_str.encode()
                # # 把cookie_str_bytes用b64转换为cookie_dict_bytes类型
                # cookie_dict_bytes = base64.b64decode(cookie_str_bytes)
                # # cookie_dict_bytes类型转换成Python中标准的字典
                # cart_dict = pickle.loads(cookie_dict_bytes)


                # 判断当前要新加入购物车的sku_id是否在原cookie中已存,如果存在,做增量,不存在新加入字典中
                if sku_id in cart_dict:
                    # 存在
                    origin_count = cart_dict[sku_id]['count']
                    count += origin_count  # count = origin_count + count
            else:
                # 第一次来添加到cookie购物车
                cart_dict = {}

                # 不管之前有没有这个商品都重新包一下
            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }

            # 把cart_dict 转换成cookie_str类型
            # 把Python的字典转换成cookie_dict_bytes字典的bytes类型
            cookie_dict_bytes = pickle.dumps(cart_dict)
            # 把cookie_dict_bytes字典的bytes类型转换成cookie_str_bytes字符串类型的bytes
            cookie_str_bytes = base64.b64encode(cookie_dict_bytes)
            # 把cookie_str_bytes类型转换成字符串
            cookie_str = cookie_str_bytes.decode()

            # 把cookie写入到浏览器
            # 创建响应对象
            response = Response(serializer.data, status=status.HTTP_201_CREATED)
            # 设置cookie
            response.set_cookie('cart', cookie_str)
            return response


    # 查询
    def get(self, request):
        """查询"""

        # 获取user
        try:
            user = request.user
        except Exception:
            user = None

        # 是否登录
        if user is not None and user.is_authenticated:
            # 登录用户从redis中获取数据
            # 获取redis连接
            redis_conn = get_redis_connection('carts')

            # 取出哈希数据 cart_user_id {sku_id1: count, sku_id2: count}
            redis_cart = redis_conn.hgetall('cart_%s' % user.id)
            # 取出set数据
            selected_cart = redis_conn.smembers('selected_%s' % user.id)

            card_dict = {}
            # 转换为python标准字典类型
            # items()  取出字典中的键值对
            for sku_id, count in redis_cart.items():
                # Python3中redis取出来的数据内部都是bytes类型
                card_dict[int(sku_id)] = {

                        'count': int(count),
                        # 'selected': True if sku_id in selected_cart else False
                        'selected': sku_id in selected_cart  #　判断该sku_id是否在selected的set集合中

                }

        else:
            # 未登录用户从cookie中获取数据
            cookie_cart = request.COOKIES.get('cart')
            if cookie_cart:
                # 把cookie字符串购物车数据转换到Python字典类型
                cookie_cart_str_bytes = cookie_cart.encode()
                cookie_cart_dict_bytes = base64.b64decode(cookie_cart_str_bytes)
                card_dict = pickle.loads(cookie_cart_dict_bytes)
            else:
                card_dict = {}

        # 将字典存进列表以进行序列化
        card_list = []
        for sku_id in card_dict:
            sku = SKU.objects.get(id=sku_id)
            # 给sku模型新增两个属性
            sku.count = card_dict[sku_id]['count']
            sku.selected = card_dict[sku_id]['selected']
            card_list.append(sku)


        serializer = CartSKUSerializer(card_list, many=True)
        return Response(serializer.data)


    # 修改(更新)
    def put(self, request):
        """修改"""

        # 创建序列化器,进行反序列化
        serializer = CartSerializer(data=request.data)
        # 校验数据
        serializer.is_valid(raise_exception=True)

        # 取出校验之后的数据
        sku_id = serializer.validated_data.get('sku_id')
        count = serializer.validated_data.get('count')
        selected = serializer.validated_data.get('selected')

        try:
            user = request.user
        except Exception:
            user = None

        # 判断当前是否是登录用户
        if user is not None and user.is_authenticated:
            # 登录用户,redis
            # 获取到连接redis对象
            redis_conn = get_redis_connection('carts')
            # 创建管道
            pl = redis_conn.pipeline()
            # hset(name＜键＞, key＜字段＞, value＜值＞)　若key不存在，创建新的哈希表，若存在，则更新ｖａｌｕｅ
            pl.hset('cart_%s' % user.id, sku_id, count)  #修改原有商品数据
            if selected:
                pl.sadd('selected_%s' % user.id, sku_id)  # 如果当前商品从未勾选变成了勾选就把这的sku_id加入到set无序集合
            else:
                pl.srem('selected_%s' % user.id, sku_id)  # 如果当前商品从勾选变成了未勾选,就把它的sku_id从set无序集合中删除
                # 执行管道
            pl.execute()
            return Response(serializer.data)
        else:
            # 未登录用户操作cookie购物车
            # 获取cookie中原有的购物车数据
            cookie_str = request.COOKIES.get('cart')
            if cookie_str:
                # 把cookie_str转换成python中的标准字典
                # 把cookie_str字符串转换成cookie_str_bytes
                cookie_str_bytes = cookie_str.encode()

                # 把cookie_str_bytes用b64转换为cookie_dict_bytes类型
                cookie_dict_bytes = base64.b64decode(cookie_str_bytes)

                # cookie_dict_bytes类型转换成Python中标准的字典
                cart_dict = pickle.loads(cookie_dict_bytes)
                # cart_dict = pickle.loads(base64.decode(cookie_str.encode()))

            else:  # 第一次来添加到cookie购物车
                cart_dict = {}

            # 不管之前有没有这个商品都重新包一下
            cart_dict[sku_id] = {
                'count': count,
                'selected': selected

            }

            # 把cart_dict 转换成cookie_str类型
            # 把Python的字典转换成cookie_dict_bytes字典的bytes类型
            cookie_dict_bytes = pickle.dumps(cart_dict)
            # 把cookie_dict_bytes字典的bytes类型转换成cookie_str_bytes字符串类型的bytes
            cookie_str_bytes = base64.b64encode(cookie_dict_bytes)
            # 把cookie_str_bytes类型转换成字符串
            cookie_str = cookie_str_bytes.decode()

            # 把cookie写入到浏览器
            # 创建响应对象
            response = Response(serializer.data)
            # 设置cookies
            response.set_cookie('cart', cookie_str)
            # 响应
            return response


    # 删除
    def delete(self, request):
        """删除"""

        # 创建序列化器(反序列化校验前端传入的sku_id)
        serializer = CartDeleteSeriazlier(data=request.data)
        # 校验
        serializer.is_valid(raise_exception=True)
        # 把校验后的sku_id取出来
        sku_id = serializer.validated_data.get('sku_id')

        # 获取user
        try:
            user = request.user
        except Exception:
            user = None


        # 创建响应对象
        response = Response(status=status.HTTP_204_NO_CONTENT)
        # 判断当前是否是登录用户
        if user is not None and user.is_authenticated:
            # 登录，操作redis
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()
            # 删除redis中商品
            pl.hdel('cart_%s' % user.id, sku_id)
            # 删除redis中勾选状态
            pl.srem('selected_%s' % user.id, sku_id)

            pl.execute()

        else:
            # 未登录，操作cookie
            cart_str = request.COOKIES.get('cart')
            if cart_str:  # 判断cookie是否有值
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                cart_dict = {}

            if sku_id in cart_dict:
                del cart_dict[sku_id]  # 把要删除的商品从字典中删除

                if len(cart_dict.keys()):  # 判断字典中是否还有数据

                    cookie_cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()

                    response.set_cookie('cart', cookie_cart_str)
                else:
                    response.delete_cookie('cart')  # 删除cookie中的购物车数据

        return response


# 购物车全选
class CartSelectAllView(APIView):
    """
    购物车全选
    """
    def perform_authentication(self, request):
        """
        重写父类的用户验证方法，不在进入视图前就检查JWT
        """
        pass


    def put(self,request):
        """购物⻋车商品全选"""

        # 序列列化器器使⽤用
        serializer = CartSelectAllSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        selected = serializer.validated_data['selected']

        try:
            user = request.user
        except Exception:
            # 验证失败，⽤用户未登录
            user = None

        if user is not None and user.is_authenticated:
            # ⽤用户已登录，操作redis购物⻋车
            redis_conn = get_redis_connection('carts')

            # 读取redis中的购物⻋车数据
            redis_dict_cart = redis_conn.hgetall('cart_%s' % user.id)
            # 将购物⻋车中所有的sku_id添加或者移除
            sku_ids = redis_dict_cart.keys()
            if selected:
                redis_conn.sadd('selected_%s' % user.id, *sku_ids)
            else:
                redis_conn.srem('selected_%s' % user.id, *sku_ids)

            # 响应结果
            return Response({'message': 'OK'})

        else:
            # ⽤用户未登录，操作cookie购物⻋车
            cart_str = request.COOKIES.get('cart')
            # 读取cookie中的购物⻋车数据
            if cart_str:
                cart_str_bytes = cart_str.encode()
                cart_dict_bytes = base64.b64decode(cart_str_bytes)
                cart_dict = pickle.loads(cart_dict_bytes)
            else:
                cart_dict = {}

            # 遍历购物⻋车字典将所有的sku_id对应的selected设置为⽤用户传⼊入的selected
            for sku_id in cart_dict:
                cart_dict[sku_id]['selected'] = selected

            # 构造购物⻋车字符串串
            cookie_cart_dict_bytes = pickle.dumps(cart_dict)
            cookie_cart_str_bytes = base64.b64encode(cookie_cart_dict_bytes)
            cookie_cart_str = cookie_cart_str_bytes.decode()

            # cookie中写⼊入购物⻋车字符串串
            response = Response({'message': 'OK'})
            response.set_cookie('cart', cookie_cart_str)
            return response
