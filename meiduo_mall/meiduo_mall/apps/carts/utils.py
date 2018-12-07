import pickle, base64
from django_redis import get_redis_connection


def merge_cart_cookie_to_redis(request, user, response):
    """登录时购物车的cookie合并到redis"""

    # 获取cookie中的购物车数据
    cookie_cart_str = request.COOKIES.get('cart')
    # cookie中没数据时:
    if not cookie_cart_str or cookie_cart_str == " ":
        return response

    cookie_cart_dict = pickle.loads(base64.b64decode(cookie_cart_str.encode()))
    if not len(cookie_cart_dict.keys()):  # 如果cookie中没有购物车数据直接返回,不要执行下面的合并代码
        return response

    # 获取redis中的购物车数据（获取时使用管道ｐｌ的话，取出来的是列表，若数据不是很多，一般不用管道）
    redis_conn = get_redis_connection('carts')
    redis_cart_dict = redis_conn.hgetall('cart_%s' % user.id)
    redis_selecteds = redis_conn.smembers('selected_%s' % user.id) # 取原本redis中所有商品勾选状态
    """
        redis_dict
        {sku_1: 1, sku_2: 2}


        cookie_dict
        {
            sku_1: {
                'count': 1
                'selected': True
            },
            sku_1: {
                'count': 2
                'selected': True
            }
        }
    """
    new_redis_cart_dict = {}  # 将（登录／未登录）数据合并到此字典，再存入redis中
    # 必须先对redis数据进行加入到new_redis_cart_dict 目的就是如果后续cookie中有相同商品,可以用cookie数据赋值redis数据
    for sku_id, count in redis_cart_dict.items():
        new_redis_cart_dict[int(sku_id)] = int(count)  # 注意数据类型转换问题（redis中遍历出来的key & value 都是bytes类型）

    # 将cookie字典数据向redis 哈希中字典格式靠拢
    for sku_id, cookie_dict in cookie_cart_dict.items():
        # sku_id存在，则覆盖，若sku_id不存在，则覆盖
        new_redis_cart_dict[sku_id] = cookie_dict['count']

        if cookie_dict['selected']:
            # 如果当前cookie中当前这件商品状态是勾选,那么就把此商品的sku_id添加到redis set集合
            # set.add(元素) 给无序集合添加新元素
            redis_selecteds.add(sku_id)

    pl = redis_conn.pipeline()
    # 把合并好的商品字典存储到redis的哈希里面
    pl.hmset('cart_%s' % user.id, new_redis_cart_dict)
    # 把商品勾选状态存入redis的set中（sadd传多个值时value前需要加＊）
    pl.sadd('selected_%s' % user.id, *redis_selecteds)
    # 执行管道
    pl.execute()

    # 传入response 是为了合并之后删除cookie数据
    response.delete_cookie('cart')
    return response


