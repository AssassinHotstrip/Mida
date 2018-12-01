from rest_framework_jwt.settings import api_settings
from django_redis import get_redis_connection
from rest_framework import serializers
import re

from goods.models import SKU
from .models import User, Address
from celery_tasks.email.tasks import send_verify_email


# POST /browse_histories/
class UserBrowseHistorySerializer(serializers.Serializer):
    """反序列化用户浏览记录"""
    sku_id = serializers.IntegerField(label="商品SKU编码", min_value=1)

    def validate_sku_id(self, value):
        """单独到此处对sku_id进行额外验证"""
        try:
            SKU.objects.get(id=value)
        except SKU.DoseNotExist:
            raise serializers.ValidationError("sku id 不存在")
        # 校验成功,返回被校验值
        return value

    def create(self, validated_data):
        """重写create方法将浏览记录存到redis"""

        # 取出sku_id
        sku_id = validated_data.get("sku_id")
        # 获取用户id动态拼接做redis数据id
        user_id = self.context.get("request").user.id
        # 创建redis连接
        redis_conn = get_redis_connection("history")
        # 创建管道
        pl = redis_conn.pipeline()
        # 去重
        # (key, 允许重复个数, 被去重数据)
        pl.lrem('history_%s' % user_id, 0, sku_id)
        # 添加
        pl.lpush('history_%s' % user_id, sku_id)
        # 截取(截取五个)
        pl.ltrim('history_%s' % user_id, 0, 4)

        # 执行管道
        pl.execute()

        return validated_data


class AddressTitleSerializer(serializers.ModelSerializer):
    """
    地址标题
    """
    class Meta:
        model = Address
        fields = ('title',)


class UserAddressSerializer(serializers.ModelSerializer):
    """
    用户地址序列化器
    """
    province = serializers.StringRelatedField(read_only=True)
    city = serializers.StringRelatedField(read_only=True)
    district = serializers.StringRelatedField(read_only=True)
    province_id = serializers.IntegerField(label='省ID', required=True)
    city_id = serializers.IntegerField(label='市ID', required=True)
    district_id = serializers.IntegerField(label='区ID', required=True)

    class Meta:
        model = Address
        exclude = ('user', 'is_deleted', 'create_time', 'update_time')

    def validate_mobile(self, value):
        """
        验证手机号
        """
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号格式错误')
        return value

    def create(self, validated_data):
        # 在序列化器中取到user并把它添加到反序列化之后的字典中
        validated_data['user'] = self.context['request'].user  # 在视图中可以使用request.user直接获取到用户;但序列化器中获取不到,需要使用context['request'].user来获取当前登录用户
        # 创建并保存地址中间就为了  地址关联用户
        address = Address.objects.create(**validated_data)

        return address



class EmailSerializer(serializers.ModelSerializer):
    """邮箱序列化器"""
    class Meta:
        model = User
        fields = ['id', 'email']
        extra = {
            'email': {
                'required': True
            }
        }

    def update(self, instance, validated_data):
        """重写update： 1.只保存邮箱； 2.发激活邮件"""
        # 只保存邮箱
        instance.email = validated_data.get('email')
        instance.save()  # ORM 中的保存

        # 2.发激活邮件
        # 生成邮箱激活链接
        verify_url = instance.generate_verify_email_url()
        # # 异步任务                      收件人（当前用户）  激活链接
        # send_verify_email.delay(instance.email, verify_url)
        send_verify_email.delay(instance.email, verify_url)

        return instance




class UserDetailSerializer(serializers.ModelSerializer):
    """用户详细信息序列化器"""
    class Meta:
        model = User
        fields = ['id', 'username', 'mobile', 'email', 'email_active']



class CreateUserSerializer(serializers.ModelSerializer):
    """注册序列化器"""

    password2 = serializers.CharField(label='确认密码', write_only=True)
    sms_code = serializers.CharField(label='短信验证码', write_only=True)
    allow = serializers.CharField(label='同意协议', write_only=True)
    token = serializers.CharField(label='token', read_only=True)

    # 所有字段："id", "username", "password", "password2", "mobile", "sms_code", "allow"
    # 模型中字段："id", "username", "password", "mobile",
    # 序列化（输出/响应到前端）："id", "username", "mobile", 'token'
    # 反序列化（输入/校验）："username", "password", "password2","mobile", "sms_code", "allow", 'token'
    class Meta:
        model = User  # 使序列化器映射该模型中的字段
        # fields = ["id", "username", "password", "password2", "mobile", "sms_code", "allow"]
        fields = ['id', 'username', 'password', 'password2', 'mobile', 'sms_code', 'allow', 'token']
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


        # token并不需要存到数据库中，写在save后面
        # 手动创建jwt的token
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER  # 加载生成载荷的函数
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER  # 加载进行生成token的函数

        payload = jwt_payload_handler(user)  # 通过传入用户信息进行生成载荷
        token = jwt_encode_handler(payload)  # 根据载荷内部再拿到内部header，再取到SECERY_KEY进行加密并拼接为完整的token
        user.token = token

        return user

