# stocks/ai_service.py
from django.conf import settings
from google import genai

from .models import DailyPrice


def analyze_stock_with_gemini(stock):
    # 1. API 클라이언트 설정 (신형 방식)
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
    except Exception as e:
        return f"API 키 설정 오류: {str(e)}"

    # 2. 데이터 준비
    prices = DailyPrice.objects.filter(stock=stock).order_by("-date")[:30]

    if not prices:
        return "분석할 데이터가 부족합니다."

    data_text = "Date | Close | Open | High | Low | Volume\n"
    for p in reversed(prices):
        data_text += f"{p.date} | {p.close_price} | {p.open_price} | {p.high_price} | {p.low_price} | {p.volume}\n"

    # 3. 프롬프트 작성
    prompt = f"""
    너는 20년 경력의 주식 애널리스트야.
    '{stock.name}({stock.code})'의 최근 30일 데이터를 분석해줘.

    [데이터]
    {data_text}

    [요청사항]
    1. 현재 추세 (상승/하락/횡보)
    2. 주요 지지/저항 라인
    3. 거래량 특이사항
    4. 종합 투자 관점 (간결하게)

    마크다운 없이 줄글로 요약해서 답변해줘.
    """

    # 4. AI 호출 (신형 모델명 gemini-2.0-flash 사용 권장)
    try:
        response = client.models.generate_content(
            model="models/gemini-flash-latest", contents=prompt
        )
        return response.text
    except Exception as e:
        error_msg = str(e)

    if "429" in error_msg:
        return "⚠️ 현재 사용량이 많아 분석이 지연되고 있습니다. 잠시 후(약 1분 뒤) 다시 시도해주세요."

    return f"AI 분석 오류: {error_msg}"
