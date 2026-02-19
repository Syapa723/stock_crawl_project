# config/urls.py
from django.contrib import admin
from django.urls import include, path

from stocks import views as stock_views  # stocks 앱의 views를 가져옴

urlpatterns = [
    path("admin/", admin.site.urls),
    # 1. 메인 페이지 (http://localhost:8000)
    # stocks 앱의 index 함수를 바라보게 합니다.
    path("", stock_views.index, name="index"),
    # 2. 주식 리스트 (http://localhost:8000/stocks/)
    # stocks 폴더 안의 urls.py로 토스합니다.
    path("stocks/", include("stocks.urls")),
]
