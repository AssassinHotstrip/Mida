from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView
from rest_framework.views import APIView

from .models import User
from .serializers import CreateUserSerializer

# Create your views here.
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


