from django.shortcuts import render
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from QQLoginTool.QQtool import OAuthQQ
from django.conf import settings
import logging
from rest_framework_jwt.settings import api_settings

from .serializers import QQAuthUserSerializer
from oauth.utils import generate_save_user_token
from .models import OAuthQQUser
from carts.utils import merge_cart_cookie_to_redis

logger = logging.getLogger('django')


# url(r'^qq/user/$', views.QQAuthUserView.as_view()),
class QQAuthUserView(GenericAPIView):
    """OAuth2.0认证，获取到openid及判断是否已绑定用户"""
    def get(self, request):
        # 获取到前端传来的code
        code = request.query_params.get('code')
        if not code:
            return Response({'message': '缺少code'}, status=status.HTTP_400_BAD_REQUEST)
        # 构建参数数据
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                        client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URI,
                        state=next)
        try:
            # 拿code向QQ服务器获取access_token
            access_token = oauth.get_access_token(code)
            # 拿access_token获取openid
            openid = oauth.get_open_id(access_token)
        except Exception as error:
            logger.info(error)
            return Response({"message": "QQ服务器不可用"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        try:
            # 用openid查询是否绑定美多商城（绑定？登录：新建）
            oauthqquser_model = OAuthQQUser.objects.get(openid=openid)
        except OAuthQQUser.DoesNotExist:
            # 如果此openid没有绑定过美多商城用户返回一个openid
            # return Response({'access_token': openid})  # 如果此openid没有绑定过用户,那么把openid返回给前端
            openid_access_token = generate_save_user_token(openid)
            return Response({'access_token': openid_access_token})
        else:
            # 获取ｏａｕｔｈ＿ｕｓｅｒ关联的ｕｓｅｒ
            user = oauthqquser_model.user
            # 如果openid已绑定美多商城用户，直接生成JWT token，并返回
            jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
            jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

            payload = jwt_payload_handler(user)
            token = jwt_encode_handler(payload)


            response = Response({
                'token': token,
                'user_id': user.id,
                'username': user.username
            })

            # 在此处进行购物车合并:COOKIE合并到redis（已绑定ＱＱ且登录）
            response = merge_cart_cookie_to_redis(request, user, response)

            return response

    def post(self,request):
        """用openid绑定用户"""
        # 创建序列化器对象
        serializer = QQAuthUserSerializer(data=request.data)
        # 校验数据
        serializer.is_valid(raise_exception=True)
        # 保存到数据库
        user = serializer.save()
        # openid已绑定美多商城用户，直接生成JWT token，并返回
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)

        # 绑定成功

        # 响应
        response = Response({
            'token': token,
            'user_id': user.id,
            'username': user.username
        })

        # 在此处进行购物车合并:COOKIE合并到redis
        response = merge_cart_cookie_to_redis(request, user, response)

        return response

# url(r'^qq/authorization/$', views.QQAuthURLView.as_view()),
class QQAuthURLView(APIView):
    """返回QQ扫码登录页面的url"""
    def get(self, request):

        # login_url = 'https://graph.qq.com/oauth2.0/authorize'
        # parmas = 'response_type=None&client_id=None&redirect_uri=None&state=None'
        # login_url = login_url + parmas
        # 创建oauth对象
        # oauth = OAuthQQ(client_id=appid, client_secret=appkey, redirect_uri=授权成功后的回调地址, state=用户从哪来到登陆界面)
        next = request.query_params.get('next')
        if not next:
            next = '/'  # 如果不知道用户从哪到登录界面，则默认回到首页

        # 创建oauth对象
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                        client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URI,
                        state=next)

        login_url = oauth.get_qq_url()

        return Response({'login_url':  login_url})
