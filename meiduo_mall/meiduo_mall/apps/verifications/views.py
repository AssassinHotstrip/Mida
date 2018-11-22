import random
import logging

from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django_redis import get_redis_connection


from meiduo_mall.libs.yuntongxun.sms import CCP
from . import constants
from celery_tasks.sms.tasks import send_sms_code


logger = logging.getLogger("django")   # 获取日志输入出器

# Create your views here.


class SMSCodeView(APIView):
    """发送短信视图"""

    def get(self, request, mobile):
        """
        GET /sms_codes/(?P<mobile>1[3-9]\d{9})/
        :param request: Request类型的请求对象
        :param mobile:  手机号
        :return: None
        """
        # 连接redis
        redis_conn = get_redis_connection("verify_code")

        # 获取send_flag
        send_flag = redis_conn.get("send_flag_%s" % mobile)

        # 判断send_flag是否有值(是否发送过短信)
        if send_flag:
            return Response({"message": "请勿频繁发送短信"}, status=status.HTTP_400_BAD_REQUEST)

        # 生成短信验证码
        sms_code = "%06d" % random.randint(0, 999999)
        logger.info(sms_code)

        # 利用管道技术将多条redis命令合并,避免多次访问redis,提升效率
        # 创建管道
        pl = redis_conn.pipeline()

        # 将验证码存到redis(key,  ex_time, value)
        # redis_conn.setex("sms_%s" % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        pl.setex("sms_%s" % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)

        # 在redis中存储一个标记,用于标记此号码已在60s内发送国短信
        # redis_conn.setex('send_flag_%s' % mobile, constants.SEND_FLAG_TIME_INTERVAL, 1)
        pl.setex('send_flag_%s' % mobile, constants.SEND_FLAG_TIME_INTERVAL, 1)

        # 执行管道
        pl.execute()

        # 发送短信(云通讯)
        #                         手机号     验证码      过期时间
        # 该方法是耗时操作,会阻塞响应
        # CCP().send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES // 60], 1)

        # 任务函数.delay(任务函数相应参数)
        # delay：延时函数，执行delay时celery才真正用上
        send_sms_code.delay(mobile, sms_code)



        return Response({'message': 'ok'})
