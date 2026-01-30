# stocks/views.py
from django.shortcuts import render, get_object_or_404, redirect
from .models import Stock, DailyPrice
from .services import fetch_and_save_stock_data


def stock_list(request):
    stocks = Stock.objects.all().order_by('name')
    return render(request, 'stocks/stock_list.html', {'stocks': stocks})


def stock_detail(request, stock_code):
    stock = get_object_or_404(Stock, code=stock_code)

    # 차트를 그리기 위해 날짜 오름차순(과거->현재)으로 데이터를 가져옵니다.
    prices = DailyPrice.objects.filter(stock=stock).order_by('date')

    # Chart.js에 넘겨줄 데이터 리스트 생성
    # 1. 날짜 리스트 (X축) -> 문자열로 변환 필요
    date_list = [p.date.strftime('%Y-%m-%d') for p in prices]

    # 2. 종가 리스트 (Y축)
    price_list = [p.close_price for p in prices]

    return render(request, 'stocks/stock_detail.html', {
        'stock': stock,
        'prices': prices,  # 표 그리기용 (기존)
        'date_list': date_list,  # 차트 X축 데이터
        'price_list': price_list,  # 차트 Y축 데이터
    })


def stock_update(request, stock_code):
    # 1. 크롤링 서비스 실행
    fetch_and_save_stock_data(stock_code)

    # 2. 작업이 끝나면 다시 상세 페이지로 이동
    return redirect('stocks:stock_detail', stock_code=stock_code)