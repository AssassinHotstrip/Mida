# celery启动入口
"""
1.创建celery客户端  Celery()
2.加载celery配置(耗时任务存放位置)
3.把耗时任务添加到任务队列
"""
from celery import Celery

# 为celery使⽤用django配置⽂文件进⾏行行设置
import os
if not os.getenv('DJANGO_SETTINGS_MODULE'):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'meiduo_mall.settings.dev'


# 创建celery客户端(参数为别名,无实际意义)
celery_app = Celery("meiduo_clr")

# 加载配置
celery_app.config_from_object("celery_tasks.config")

# 注册任务
celery_app.autodiscover_tasks(["celery_tasks.sms", "celery_tasks.email"])  # 任务有多个,一定要将任务放在列表中