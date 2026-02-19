import json
import os
from datetime import datetime, timedelta

import FinanceDataReader as fdr  # [✨ 교체] yfinance -> FinanceDataReader
import numpy as np
import pandas as pd
import requests
from django.utils import timezone

from .models import DailyPrice, Stock


# ---------------------------------------------------------
# 1. 전 종목 코드 수집 함수 (init_stocks에서 호출)
# ---------------------------------------------------------
def update_all_stock_codes():
    """
    한국 거래소(KRX)의 전 종목 코드를 가져와 Stock 모델에 저장합니다.
    """
    try:
        print("KRX 종목 리스트 다운로드 중...")
        # KRX 전체 종목 리스트 가져오기 (코스피, 코스닥, 코넥스 포함)
        df_krx = fdr.StockListing("KRX")

        if df_krx is None or df_krx.empty:
            print("❌ KRX 종목 리스트를 가져오지 못했습니다.")
            return 0, 0  # [✨ 수정] 실패 시 0, 0 반환

        # [옵션] 테스트를 위해 상위 50개만 저장하려면 .head(50) 사용
        # 실제 운영 시에는 전체를 다 해야 하므로 .head() 제거
        count = 0
        for index, row in df_krx.iterrows():
            try:
                code = str(row["Code"])
                name = row["Name"]
                market = row["Market"]

                # DB에 저장 (이미 있으면 업데이트)
                Stock.objects.update_or_create(
                    code=code, defaults={"name": name, "market": market}
                )
                count += 1
            except Exception as e:
                print(f"Error saving {row['Name']}: {e}")

        print(f"✅ 총 {count}개 종목 코드 업데이트 완료")

        return count, len(df_krx)

    except Exception as e:
        print(f"❌ 종목 코드 저장 실패: {e}")
        return 0, 0


# ---------------------------------------------------------
# 2. 일별 시세 수집 함수 (init_stocks 및 스케줄러에서 호출)
# ---------------------------------------------------------
def fetch_and_save_stock_data(stock_code):
    """
    특정 종목의 최근 일봉 데이터를 가져와 DailyPrice에 저장합니다.
    """
    try:
        stock = Stock.objects.get(code=stock_code)

        # 최근 60일치 데이터 가져오기 (W패턴 분석용)
        # FinanceDataReader는 날짜만 넣으면 알아서 가져옵니다.
        start_date = datetime.now() - timedelta(days=100)
        df = fdr.DataReader(stock_code, start_date)

        if df.empty:
            return False

        # 데이터 저장
        for date, row in df.iterrows():
            # 날짜 객체 변환 (Timestamp -> date)
            date_obj = date.date()

            # 이미 저장된 날짜면 건너뛰기 (중복 방지)
            if DailyPrice.objects.filter(stock=stock, date=date_obj).exists():
                continue

            DailyPrice.objects.create(
                stock=stock,
                date=date_obj,
                open_price=int(row["Open"]),
                high_price=int(row["High"]),
                low_price=int(row["Low"]),
                close_price=int(row["Close"]),
                volume=int(row["Volume"] if "Volume" in row else 0),
            )
        return True

    except Exception as e:
        print(f"Error fetching data for {stock_code}: {e}")
        return False


# ---------------------------------------------------------
# 3. W곡선(쌍바닥) 패턴 분석 함수 (기존 로직 유지)
# ---------------------------------------------------------
def analyze_w_pattern(stock_code):
    """
    최근 60거래일 데이터를 분석하여 W곡선 패턴을 감지하고 DB에 저장합니다.
    """
    try:
        stock = Stock.objects.get(code=stock_code)
        # 최근 60일치 데이터를 날짜순으로 가져옴
        prices = list(DailyPrice.objects.filter(stock=stock).order_by("date"))

        if len(prices) < 40:  # 최소 분석 데이터 부족
            return False

        close_prices = np.array([p.close_price for p in prices])

        # [Step 1] 1차 바닥(Low 1) 찾기 (전체 구간의 앞쪽 70% 중 최저점)
        search_range = int(len(close_prices) * 0.7)
        low1_idx = np.argmin(close_prices[:search_range])
        low1_price = close_prices[low1_idx]

        # [Step 2] 넥라인(Peak) 찾기 (1차 바닥 이후 최고점)
        after_low1 = close_prices[low1_idx:]
        if len(after_low1) < 2:
            return False

        peak_idx = low1_idx + np.argmax(after_low1)
        peak_price = close_prices[peak_idx]

        # [Step 3] 2차 바닥(Low 2) 찾기 (넥라인 이후 최저점)
        after_peak = close_prices[peak_idx:]
        if len(after_peak) < 5:
            return False

        low2_idx = peak_idx + np.argmin(after_peak)
        low2_price = close_prices[low2_idx]

        # --- 패턴 검증 로직 ---
        # 1. 두 바닥의 가격 차이가 5% 이내 (쌍바닥 조건 완화)
        price_diff_ratio = abs(low1_price - low2_price) / low1_price

        # 2. 넥라인이 바닥 대비 3% 이상 반등했는지 확인
        rebound_ratio = (peak_price - low1_price) / low1_price

        # 3. 현재가가 2차 바닥보다 높고 고개를 드는 중인지
        current_price = close_prices[-1]
        is_rebounding = current_price > low2_price

        # [결과 반영]
        if price_diff_ratio < 0.05 and rebound_ratio > 0.03 and is_rebounding:
            stock.is_w_pattern = True
            # 점수 계산: 바닥 차이가 적을수록, 반등폭이 클수록 높은 점수
            score = int((1 - price_diff_ratio) * 50 + (rebound_ratio * 100))
            stock.w_score = min(score, 100)  # 100점 만점 제한
        else:
            stock.is_w_pattern = False
            stock.w_score = 0

        stock.save()
        return stock.is_w_pattern

    except Exception as e:
        print(f"W-Pattern analysis failed for {stock_code}: {e}")
        return False
