# stocks/views.py
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .ai_service import analyze_stock_with_gemini
from .models import DailyPrice, Stock
from .services import fetch_and_save_stock_data


def stock_list(request):
    # 1. 사용자가 입력한 검색어 가져오기 (없으면 빈 문자열)
    query = request.GET.get("q", "")

    if query:
        # 2. 검색어가 있으면: 이름(name) OR 코드(code)에 포함된 것 필터링
        # icontains는 대소문자 구분 없이 검색한다는 뜻입니다.
        stocks = Stock.objects.filter(
            Q(name__icontains=query) | Q(code__icontains=query)
        ).order_by("name")
    else:
        # 3. 검색어가 없으면: 전체 리스트 보여주기
        stocks = Stock.objects.all().order_by("name")

    return render(
        request,
        "stocks/stock_list.html",
        {
            "stocks": stocks,
            "search_query": query,  # [3] 검색창에 입력했던 단어를 유지하기 위해 템플릿으로 전달
        },
    )


def stock_detail(request, stock_code):
    stock = get_object_or_404(Stock, code=stock_code)

    # 차트를 그리기 위해 날짜 오름차순(과거->현재)으로 데이터를 가져옵니다.
    prices = DailyPrice.objects.filter(stock=stock).order_by("date")

    # Chart.js에 넘겨줄 데이터 리스트 생성
    # 1. 날짜 리스트 (X축) -> 문자열로 변환 필요
    date_list = [p.date.strftime("%Y-%m-%d") for p in prices]

    # 2. 종가 리스트 (Y축)
    price_list = [p.close_price for p in prices]

    ai_result = None

    if request.method == "POST":
        print(f"👉 [DEBUG] POST 요청 도착! 데이터: {request.POST}")  # 터미널 확인용 1

        if "analyze" in request.POST:
            print(f"👉 [DEBUG] AI 분석 시작: {stock.name}")  # 터미널 확인용 2
            ai_result = analyze_stock_with_gemini(stock)
            print(f"👉 [DEBUG] AI 응답 완료: {ai_result[:50]}...")  # 터미널 확인용 3

    return render(
        request,
        "stocks/stock_detail.html",
        {
            "stock": stock,
            "prices": prices,  # 표 그리기용 (기존)
            "date_list": date_list,  # 차트 X축 데이터
            "price_list": price_list,  # 차트 Y축 데이터
            "ai_result": ai_result,
        },
    )


def stock_update(request, stock_code):
    # 1. 크롤링 서비스 실행
    fetch_and_save_stock_data(stock_code)

    # 2. 작업이 끝나면 다시 상세 페이지로 이동
    return redirect("stocks:stock_detail", stock_code=stock_code)


def index(request):
    """
    메인 페이지를 보여줍니다.
    예전에 만든 HTML 파일 이름이 'index.html'이라고 가정합니다.
    """
    return redirect("stocks:w_dashboard")


def w_pattern_dashboard(request):
    """
    W패턴(쌍바닥)이 감지된 종목들만 모아서 보여주는 대시보드입니다.
    """
    # 1. W패턴으로 판명된 종목들만 가져오고, 점수 높은 순으로 정렬
    w_stocks = Stock.objects.filter(is_w_pattern=True).order_by("-w_score")

    # 2. 검색 기능 (대시보드 내에서도 검색 가능하게)
    query = request.GET.get("q", "")
    if query:
        w_stocks = w_stocks.filter(Q(name__icontains=query) | Q(code__icontains=query))

    # [✨ 핵심 추가] 각 종목마다 최신 가격(DailyPrice)을 찾아서 넣어줍니다.
    for stock in w_stocks:
        # 해당 종목의 시세 데이터 중 가장 최신 날짜(-date)의 데이터를 하나 가져옵니다.
        latest = DailyPrice.objects.filter(stock=stock).order_by("-date").first()
        if latest:
            stock.current_price = (
                latest.close_price
            )  # 최신 종가를 'current_price'라는 이름으로 붙여줌
        else:
            stock.current_price = 0  # 시세 데이터가 없으면 0원으로 표시

    return render(
        request,
        "stocks/w_dashboard.html",
        {
            "w_stocks": w_stocks,
            "search_query": query,
            "total_count": w_stocks.count(),
        },
    )
