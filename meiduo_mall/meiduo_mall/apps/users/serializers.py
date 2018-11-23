from django_redis import get_redis_connection
from rest_framework import serializers
import re


from .models import User

class CreateUserSerializer(serializers.ModelSerializer):
    """注册序列化器"""

    password2 = serializers.CharField(label='确认密码', write_only=True)
    sms_code = serializers.CharField(label='短信验证码', write_only=True)
    allow = serializers.CharField(label='同意协议', write_only=True)

    # 所有字段："id", "username", "password", "password2", "mobile", "sms_code", "allow"
    # 模型中字段："id", "username", "password", "mobile",
    # 序列化（输出/响应到前端）："id", "username", "mobile",
    # 反序列化（输入/校验）："username", "password", "password2","mobile", "sms_code", "allow"
    class Meta:
        model = User  # 使序列化器映射该模型中的字段
        # fields = ["id", "username", "password", "password2", "mobile", "sms_code", "allow"]
        fields = ['id', 'username', 'password', 'password2', 'mobile', 'sms_code', 'allow']
        extra_kwargs = {
            'username': {
                'min_length': 5,
                'max_length': 20,
                'error_messages': {
                    'min_length': '仅允许5-20个字符的用户名',
                    'max_length': '仅允许5-20个字符的用户名',
                }
            },
            'password': {
                'write_only': True,
                'min_length': 8,
                'max_length': 20,
                'error_messages': {
                    'min_length': '仅允许8-20个字符的密码',
                    'max_length': '仅允许8-20个字符的密码',
                }
            }
        }




    def validate_mobile(self, value):
        """验证手机号"""
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号格式错误')
        return value

    def validate_allow(self, value):
        """检验用户是否同意协议"""
        if value != 'true':
            raise serializers.ValidationError('请同意用户协议')
        return value

    def validate(self, data):
        # 判断两次密码
        if data['password'] != data['password2']:
            raise serializers.ValidationError('两次密码不一致')

        # 判断短信验证码
        redis_conn = get_redis_connection('verify_codes')
        mobile = data['mobile']
        real_sms_code = redis_conn.get('sms_%s' % mobile)
        if real_sms_code is None:
            raise serializers.ValidationError('无效的短信验证码')
        if data['sms_code'] != real_sms_code.decode():
            raise serializers.ValidationError('短信验证码错误')

        return data

    # 重写create方法:把不需要存到数据库字段排除
    def create(self, validated_data):

        # 把不需要存到数据库中的字段删除
        del validated_data['password2']
        del validated_data['sms_code']
        del validated_data['allow']

        # 创建用户模型
        user = User(**validated_data)

        # 给密码进行加密处理并覆盖原有数据
        user.set_password(user.password)

        user.save()  # 保存到数据库

        return user

