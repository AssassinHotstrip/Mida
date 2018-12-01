from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 2  # 默认每页显示2个
    page_size_query_param = 'page_size'  # 指定分页前端查询字段 默认不写,为None
    max_page_size = 20  # 每页显示最大数量