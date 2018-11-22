# 编辑耗时任务(定义异步任务)
from celery_tasks.main import celery_app
from . import constants
from .yuntongxun.sms import CCP

# 用装饰器将此函数装饰为异步任务(name=别名 )
@celery_app.task(name="send_sms_code")
def send_sms_code(mobile, sms_code):
    """发送短信"""
    # 发送短信(云通讯)
    #                         手机号     验证码      过期时间
    CCP().send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES // 60], 1)
