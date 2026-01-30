from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("stocks/", include("stocks.urls")),  # stocks 앱의 url 연결
]
