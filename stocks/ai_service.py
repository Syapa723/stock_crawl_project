import pandas as pd
from django.conf import settings
from google import genai

from .models import DailyPrice


def analyze_stock_with_gemini(stock):
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
    except Exception as e:
        return f"API 키 설정 오류: {str(e)}"

    # 1. 데이터 가져오기 (추세를 읽기 위해 30일치 가져옴)
    prices = DailyPrice.objects.filter(stock=stock).order_by("-date")[:30]

    if len(prices) < 20:
        return "데이터가 부족하여 기술적 분석을 할 수 없습니다 (최소 20일 필요)."

    # 최신 데이터가 위로 오도록 리스트 생성
    recent_list = list(prices)
    latest = recent_list[0]  # 가장 최신 날짜 데이터

    # [✨ 안전장치] None 값을 대비한 포맷팅 (에러 방지)
    rsi_display = f"{latest.rsi:.1f}" if latest.rsi is not None else "데이터 없음"
    ma5_display = f"{latest.ma5:,.0f}" if latest.ma5 is not None else "N/A"
    ma20_display = f"{latest.ma20:,.0f}" if latest.ma20 is not None else "N/A"
    ma60_display = f"{latest.ma60:,.0f}" if latest.ma60 is not None else "N/A"

    # AI에게 줄 데이터 테이블 구성
    # [✨ 추가] AI가 변동성을 쉽게 파악하도록 '전일비(Change)'를 계산해서 넣어줍니다.
    data_text = "날짜 | 종가 | 전일비(%) | MA5 | MA20 | MA60 | RSI | 거래량\n"
    data_text += "--- | --- | --- | --- | --- | --- | --- | ---\n"

    for i, p in enumerate(recent_list[:15]):  # 최근 15일치 상세 데이터 제공
        # 지표 안전 포맷팅
        p_rsi = f"{p.rsi:.1f}" if p.rsi is not None else "N/A"
        p_ma5 = f"{p.ma5:,.0f}" if p.ma5 is not None else "N/A"
        p_ma20 = f"{p.ma20:,.0f}" if p.ma20 is not None else "N/A"
        p_ma60 = f"{p.ma60:,.0f}" if p.ma60 is not None else "N/A"

        # 전일비 계산 (데이터가 존재할 경우)
        if i + 1 < len(recent_list):
            prev_close = recent_list[i + 1].close_price
            change_rate = ((p.close_price - prev_close) / prev_close) * 100
            change_str = f"{change_rate:+.2f}%"
        else:
            change_str = "0.00%"

        data_text += f"{p.date} | {p.close_price:,} | {change_str} | {p_ma5} | {p_ma20} | {p_ma60} | {p_rsi} | {p.volume:,}\n"

    # 이평선 배열 상태 파악
    curr_ma5 = latest.ma5 or 0
    curr_ma20 = latest.ma20 or 0
    curr_ma60 = latest.ma60 or 0
    ma_trend = (
        "정배열(상승추세)" if curr_ma5 > curr_ma20 > curr_ma60 else "역배열/혼조세"
    )

    # 2. 강화된 추론형 프롬프트 (Inference Strategy 적용)
    prompt = f"""
    너는 20년 경력의 월가 퀀트 투자 전문가이자 '패턴 추론(Pattern Inference)' 분석가야.
    단순히 현재 상태를 묘사하지 말고, 주어진 데이터를 근거로 **향후 5~10일 뒤의 주가 흐름을 시나리오별로 추론**해줘.

    [분석 대상: {stock.name} ({stock.code})]

    [기술적 지표 요약]
    - 현재가: {latest.close_price:,}원
    - 이동평균선 배열: {ma_trend}
    - 현재 RSI: {rsi_display} (30이하: 과매도, 70이상: 과매수)
    - 주요 이평선: MA5({ma5_display}), MA20({ma20_display}), MA60({ma60_display})

    [상세 데이터 (최근 15일)]
    {data_text}

    [🔥 핵심 추론 가이드라인]
    1. **RSI 다이버전스(Divergence) 추적**: 
       - 최근 주가가 신저가를 갱신하거나 하락 중인데, RSI 수치는 오히려 전저점보다 높아지는 현상이 있는지 찾아낼 것. (강력한 반등 신호)
    2. **거래량 고갈(Volume Dry-up) 확인**:
       - 주가가 바닥권에서 횡보하거나 눌림목을 줄 때, 거래량이 급감하며 '매도세가 고갈된 모습'을 보이는지 분석할 것.
    3. **W-패턴 시나리오**:
       - 현재가 W의 오른쪽 바닥(Right Bottom)을 만들고 있는 과정인지 추론할 것.
       - W패턴이 완성되기 위해 돌파해야 할 '넥라인(Neckline)' 가격대는 얼마인가?

    [최종 투자 리포트 작성 양식]
    - **추론 요약**: (한 줄로 핵심 상황 정리)
    - **상승 시그널**: (다이버전스 여부, 거래량 패턴 등 긍정적 요소)
    - **위험 요소**: (역배열 저항, 거래량 부족 등 부정적 요소)
    - **대응 시나리오**:
       * 📈 **진입 적기(Buy Zone)**: (구체적 가격대)
       * 🎯 **1차 목표가**: (단기 저항선 가격)
       * 🛡️ **손절가**: (생명선 이탈 가격)
    - **종합 매력도**: (0~100점)
    """

    try:
        response = client.models.generate_content(
            model="models/gemini-flash-latest", contents=prompt
        )
        return response.text
    except Exception as e:
        if "429" in str(e):
            return "⚠️ AI 분석 요청이 폭주 중입니다. 1분 뒤 다시 시도해주세요."
        return f"AI 분석 오류: {str(e)}"
