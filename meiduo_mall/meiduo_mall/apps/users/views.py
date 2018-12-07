from django.shortcuts import render
from django_redis import get_redis_connection

from rest_framework import status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet
from rest_framework_jwt.views import ObtainJSONWebToken

from carts.utils import merge_cart_cookie_to_redis
from goods.models import SKU
from goods.serializers import SKUSerializer
from users import constants
from .models import User, Address
from .serializers import CreateUserSerializer, UserDetailSerializer, EmailSerializer, UserAddressSerializer, AddressTitleSerializer, UserBrowseHistorySerializer




# Create your views here.
# url(r'^authorizations/$', views.UserAuthorizeView.as_view()),
class UserAuthorizeView(ObtainJSONWebToken):
    """重写JWT_token认证类,目的为了让购物车合并,搭上账号登录的顺风车"""
    # obtain_jwt_token-->ObtainJSONWebToken  :重写ObtainJSONWebToken的post方法，在其登录时添加merge_cart_cookie_to_redis方法

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        serializer = self.get_serializer(data=request.data)
        # 验证
        if serializer.is_valid():
            # 获取user以传入merge_cart_cookie_to_redis()
            user = serializer.object.get('user') or request.user

            merge_cart_cookie_to_redis(request, user, response)

        return response







# POST browse_histories/
class  UserBrowseHistoryView(CreateAPIView):
    """保存用户浏览记录"""
    # 指定序列器进行数据的校验
    serializer_class = UserBrowseHistorySerializer

    # 指定只有登录用户才能访问此接口
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """获取用户的浏览记录"""
        # 获取user_id
        user_id = request.user.id
        # 创建redis连接
        redis_conn = get_redis_connection('history')

        # 取redis中的当前登录用户的所有浏览记录数据
        # lrange(key, start, end)
        sku_ids = redis_conn.lrange('history_%s' % user_id, 0, -1)

        sku_list = []  # 保存sku模型对象
        # 遍历sku_ids通过sku_id取出每一个sku商品模型对象
        for sku_id in sku_ids:
            sku_model = SKU.objects.get(id=sku_id)
            sku_list.append(sku_model)

        serializer = SKUSerializer(sku_list, many=True)
        return Response(serializer.data)



class AddressViewSet(mixins.CreateModelMixin, mixins.UpdateModelMixin, GenericViewSet):
    """用户地址"""
    # 指定序列化器
    serializer_class = UserAddressSerializer
    # 指定权限
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.addresses.filter(is_deleted=False)


    # GET /addresses/
    def list(self, request, *args, **kwargs):
        """
        用户地址列表数据
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        user = self.request.user
        return Response({
            'user_id': user.id,
            'default_address_id': user.default_address_id,
            'limit': constants.USER_ADDRESS_COUNTS_LIMIT,
            'addresses': serializer.data,
        })



    # POST /addresses/
    def create(self, request, *args, **kwargs):
        """新增地址"""

        # 限制每个用户地址个数
        count = request.user.addresses.all().count()
        # count = Address.objects.filter(user=request.user).count()  # 方式二
        if count >= constants.USER_ADDRESS_COUNTS_LIMIT:
            return Response({"message": "用户地址超过上限"},
        status=status.HTTP_400_BAD_REQUEST)
        return super(AddressViewSet, self).create(request, *args, **kwargs)
    #     常规创建功能CreateModelMixin中自动实现,不必再写
    #     # 创建序列化器进行反序列化
    #     serializer = self.get_serializer(data=request.data)
    #     # 数据校验
    #     serializer.is_valid(raise_exception=True)
    #     # 保存数据
    #     serializer.save()
    #     return Response(serializer.data)



    # delete /addresses/<pk>/
    def destroy(self, request, *args, **kwargs):
        """
        处理删除
        """
        address = self.get_object()

        # 进行逻辑删除
        address.is_deleted = True
        address.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

    # put /addresses/pk/status/
    @action(methods=['put'], detail=True)
    def status(self, request, pk=None):
        """
        设置默认地址
        """
        address = self.get_object()
        request.user.default_address = address
        request.user.save()
        return Response({'message': 'OK'}, status=status.HTTP_200_OK)

    # put /addresses/pk/title/
    # 需要请求体参数 title
    @action(methods=['put'], detail=True)
    def title(self, request, pk=None):
        """
        修改标题
        """
        address = self.get_object()
        serializer = AddressTitleSerializer(instance=address, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)





class VerifyEmailView(APIView):
    """验证激活链接"""

    def get(self, request):

        # 1.提取token
        token = request.query_params.get('token')
        if not token:
            return Response({'messsage': '缺少token'}, status=status.HTTP_400_BAD_REQUEST)

        # 2.校验token,是否原来那个
        user = User.check_verify_email_url(token)
        if not user:
            return Response({'messsage': 'token无效'}, status=status.HTTP_400_BAD_REQUEST)

        # 修改用户的邮箱激活状态 email_active = True
        user.email_active = True
        user.save()

        return Response({'message': 'ok'})


class EmailView(UpdateAPIView):
    """保存邮箱"""
    # 指定序列化器
    serializer_class = EmailSerializer
    # 指定当前用户权限(只有登录用户才能访问)
    permission_classes = [IsAuthenticated]

    # 重写getobject（self），返回用户详情模型对象
    def get_object(self):
        # 获取登录用户
        return self.request.user  # user代表当前用户



# url(r'^users/$', views.UserDetailView.as_view())
class UserDetailView(RetrieveAPIView):
    """获取用户详细信息"""

    # 指定序列化器
    serializer_class = UserDetailSerializer
    # 指定当前用户权限(只有登录用户才能访问)
    permission_classes = [IsAuthenticated]

    # 重写getobject（self），返回用户详情模型对象
    def get_object(self):
        # 获取登录用户
        return self.request.user  # user代表当前用户




class MobileCountView(APIView):
    """判断手机号是否已存在"""
    def get(self, request, mobile):

        # 查询数据库有有没有此手机号
        count = User.objects.filter(mobile=mobile).count()

        data = {
            'mobile': mobile,
            'count': count
        }
        return Response(data)


class UsernameCountView(APIView):
    """判断用户名是否已存在"""
    def get(self, request, username):

        # 查询数据库有有没有此用户名
        count = User.objects.filter(username=username).count()

        data = {
            'username': username,
            'count': count
        }
        return Response(data)


class Userview(CreateAPIView):
    """注册"""

    serializer_class = CreateUserSerializer


