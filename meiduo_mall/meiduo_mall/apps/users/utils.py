import re

from django.contrib.auth.backends import ModelBackend

from .models import User


def get_user_by_account(account):
    """
    根据account 动态查找用户
    :param account: 用户名/手机
    :return:
    """
    try:
        if re.match('^1[3-9]\d{9}$', account):
            user = User.objects.get(mobile=account)
        else:
            user = User.objects.get(username=account)
    except User.DoseNoteExist:
        return None
    else:
        return user




class UserNameMobileAuthBackend(ModelBackend):
    """修改用户认证系统后端，支持多账号登陆"""

    def authenticate(self, request, username=None, password=None, **kwargs):
        """

        :param request: 本次认证请求体
        :param username: 本次认证账号（用户名/手机号）
        :param password: 本次认证密码密码
        :param kwargs:
        :return: 认证成功后返回user对象
        """

        # 1.根据账户查询
        user = get_user_by_account(username)
        # 判断用户是否存在，并验证密码
        if user and user.check_password(password):
            return user



# 重写jwt登录成功后的返回函数，附加上自己需要的返回的id和username
def jwt_response_payload_handler(token, user=None, request=None):
    # 自定义jwt、认证成功返回数据
    return {
        'token': token,
        'id': user.id,
        'username': user.username
    }