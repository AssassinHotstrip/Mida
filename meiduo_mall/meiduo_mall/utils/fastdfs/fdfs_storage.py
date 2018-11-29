from django.conf import settings
from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client




class FastDFSStorage(Storage):
    """自定义文件管理系统类"""

    def __init__(self, client_conf=None, base_url=None):
        """初始化方法"""
        # self.client_conf = client_conf
        # if client_conf == None:
        #     self.client_conf = settings.FDFS_CLIENT_CONF
        self.client_conf = client_conf or settings.FDFS_CLIENT_CONF
        self.base_url = base_url or settings.FDFS_BASE_URL

    def _open(self, name, mode='rb'):
        """
        储存类用于打开文件,因为此处只上传并不打开文件,故pass
        :param name: 要打开的文件名
        :param mode: 文件读取模式
        :return:
        """
        pass

    def _save(self, name, content):
        """
        让django把图片用fdfs进行图片的上传储存
        :param name: 被存储文件名
        :param content: 被存储文件对象
        :return: file_id
        """

        # 加载fdfs的客户端配置文件来创建一个fdfs客户端
        # client = Fdfs_client('meiduo_mall/utils/fastdfs/client.conf')
        # client = Fdfs_client(settings.FDFS_CLIENT_CONF)
        client = Fdfs_client(self.client_conf)
        # 上传文件
        # ret = client.upload_by_filename('/home/python/Desktop/image/001.jpg')  # 此方式需要直到被上传文件的绝对路径
        ret = client.upload_by_buffer(content.read())  # content为传进来的数据
        """
        上传后ret返回值举例:
        {'Group name': 'group1',
        'Status': 'Upload successed.',
        'Storage IP': '192.168.170.211',
        'Remote file_id':'group1/M00/00/00/wKiq01v_yeKAIWw5AAO6A4VJCmk689.jpg',
        'Uploaded size': '238.00KB',
        'Local file name': '/home/python/Desktop/image/001.jpg'}
        """

        # 获取文件上传状态
        status = ret.get('Status')
        # 判断文件是否上传成功
        if status != 'Upload successed.':
            raise Exception('Upload failed')
        # 获取成功上传的文件id
        file_id = ret.get('Remote file_id')
        return file_id

    def exists(self, name):
        """
        判断上传的文件在storage服务器中是否存在
        :param name: 文件名
        :return: True:文件已存在,不再上传; False:文件不存在,调用save上传
        """
        return False


    def url(self, name):
        """
        返回要下载的图片的绝对路径
        :param name: fiel_id, 文件存储在storage中的相对路径
        :return: 文件绝对路径,如:http://192.168.170.211:8888/group1/M00/00/00/wKiq01v_yeKAIWw5AAO6A4VJCmk689.jpg
        """
        # return  "http://192.168.170.211:8888" + name
        # return  settings.FDFS_BASE_URL + name
        return  self.base_url + name