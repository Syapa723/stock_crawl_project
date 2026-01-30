# stocks/urls.py
from django.urls import path
from . import views

app_name = 'stocks'

urlpatterns = [
    path('', views.stock_list, name='stock_list'),
    path('<str:stock_code>/', views.stock_detail, name='stock_detail'),
    # 업데이트용 URL 추가
    path('<str:stock_code>/update/', views.stock_update, name='stock_update'),
]