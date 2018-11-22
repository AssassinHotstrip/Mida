from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

# 在Django中默认的AbstractUser用户模型类中增加手机属性(指定默认用户类型也需要改成User)
class User(AbstractUser):
    """自定义用户模型类"""
    # 增加手机属性
    mobile = models.CharField(max_length=11, unique=True, verbose_name='手机号')

    class Meta:
        db_table = 'tb_users'
        verbose_name = '用户'
        verbose_name_plural = verbose_name