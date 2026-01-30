# stocks/services.py
import requests
import pandas as pd
from io import StringIO
from bs4 import BeautifulSoup
from .models import Stock, DailyPrice


def fetch_and_save_stock_data(stock_code):
    """
    네이버 증권에서 특정 종목의 일별 시세를 가져와 DB에 저장하는 서비스 함수
    """
    # 1. 종목 객체 가져오기 또는 생성
    stock, created = Stock.objects.get_or_create(
        code=stock_code,
        defaults={'name': f'Stock_{stock_code}'}
    )

    url = f"https://finance.naver.com/item/sise_day.nhn?code={stock_code}"
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}

    # 2. 네이버 서버에 요청 (1페이지 데이터)
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        main_url = f"https://finance.naver.com/item/main.nhn?code={stock_code}"
        main_response = requests.get(main_url, headers=headers)
        soup = BeautifulSoup(main_response.text, 'html.parser')

        # 네이버 금융 메인 페이지에서 종목명 태그 찾기
        name_tag = soup.select_one('.wrap_company h2 a')
        stock_name = name_tag.text if name_tag else f"Stock_{stock_code}"

        # [3] Stock 모델 업데이트 (get_or_create -> update_or_create로 변경하거나 이름 업데이트)
        stock, created = Stock.objects.get_or_create(code=stock_code)
        # 이미 존재하더라도 진짜 종목명으로 업데이트
        if stock.name != stock_name:
            stock.name = stock_name
            stock.save()

        df_list = pd.read_html(StringIO(response.text), encoding='cp949')
        if not df_list:
            return 0

        df = df_list[0].dropna()

        saved_count = 0
        # 3. 데이터프레임 순회하며 DB 저장
        for _, row in df.iterrows():
            # 날짜 형식 처리 (2024.01.30 -> 2024-01-30)
            date_str = row['날짜'].replace('.', '-')

            _, created = DailyPrice.objects.get_or_create(
                stock=stock,
                date=date_str,
                defaults={
                    'open_price': int(row['시가']),
                    'high_price': int(row['고가']),
                    'low_price': int(row['저가']),
                    'close_price': int(row['종가']),
                    'volume': int(row['거래량'])
                }
            )
            if created:
                saved_count += 1

        return saved_count
    except Exception as e:
        print(f"Error fetching data for {stock_code}: {e}")
        return 0


def update_all_stock_codes():
    """
    한국거래소(KRX)에서 상장된 모든 종목(KOSPI, KOSDAQ) 정보를 가져와 Stock 모델에 저장합니다.
    """
    # 1. KRX 상장법인 목록 다운로드 URL
    stock_code_url = 'http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13'

    try:
        # 2. pandas로 HTML(엑셀 형식) 읽기
        df = pd.read_html(stock_code_url, header=0, encoding='cp949')[0]

        # 3. 데이터 전처리
        # 종목코드가 숫자(5930)로 들어오므로 6자리 문자열(005930)로 변환
        df['종목코드'] = df['종목코드'].astype(str).str.zfill(6)

        # 필요한 컬럼만 선택 (회사명, 종목코드)
        df = df[['회사명', '종목코드']]

        # 4. DB에 저장 (update_or_create 사용)
        total_count = len(df)
        saved_count = 0

        for _, row in df.iterrows():
            name = row['회사명']
            code = row['종목코드']

            # 종목이 이미 있으면 이름 업데이트, 없으면 생성
            Stock.objects.update_or_create(
                code=code,
                defaults={'name': name}
            )
            saved_count += 1

        return saved_count, total_count

    except Exception as e:
        print(f"전체 종목 가져오기 실패: {e}")
        return 0, 0