# stocks/views.py
from django.shortcuts import render, get_object_or_404, redirect
from .models import Stock, DailyPrice
from .services import fetch_and_save_stock_data
from .ai_service import analyze_stock_with_gemini


def stock_detail(request, stock_code):
    stock = get_object_or_404(Stock, code=stock_code)
    prices = DailyPrice.objects.filter(stock=stock).order_by('date')

    # 차트용 데이터
    date_list = [p.date.strftime('%Y-%m-%d') for p in prices]
    price_list = [p.close_price for p in prices]

    # [추가] AI 분석 결과 변수 초기화
    ai_result = None

    # [추가] POST 요청으로 'analyze' 키가 들어오면 AI 분석 실행
    if request.method == 'POST' and 'analyze' in request.POST:
        ai_result = analyze_stock_with_gemini(stock)

    return render(request, 'stocks/stock_detail.html', {
        'stock': stock,
        'prices': prices,
        'date_list': date_list,
        'price_list': price_list,
        'ai_result': ai_result,  # [추가] 템플릿으로 결과 전달
    })

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

    ai_result = None

    if request.method == 'POST':
        print(f"👉 [DEBUG] POST 요청 도착! 데이터: {request.POST}")  # 터미널 확인용 1

        if 'analyze' in request.POST:
            print(f"👉 [DEBUG] AI 분석 시작: {stock.name}")  # 터미널 확인용 2
            ai_result = analyze_stock_with_gemini(stock)
            print(f"👉 [DEBUG] AI 응답 완료: {ai_result[:50]}...")  # 터미널 확인용 3

    return render(request, 'stocks/stock_detail.html', {
        'stock': stock,
        'prices': prices,  # 표 그리기용 (기존)
        'date_list': date_list,  # 차트 X축 데이터
        'price_list': price_list,  # 차트 Y축 데이터
        'ai_result': ai_result,
    })


def stock_update(request, stock_code):
    # 1. 크롤링 서비스 실행
    fetch_and_save_stock_data(stock_code)

    # 2. 작업이 끝나면 다시 상세 페이지로 이동
    return redirect('stocks:stock_detail', stock_code=stock_code)