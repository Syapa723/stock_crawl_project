import pandas as pd
import pandas_ta as ta
from django.core.management.base import BaseCommand

from stocks.models import DailyPrice, Stock


class Command(BaseCommand):
    help = "모든 종목의 기술적 지표(MA, RSI)를 계산합니다."

    def handle(self, *args, **options):
        self.stdout.write("⚙️ 지표 계산을 시작합니다...")

        # 데이터가 있는 종목만 가져오기
        stocks = Stock.objects.all()
        count = 0

        for stock in stocks:
            # 1. 시세 데이터 가져오기 (날짜 오름차순)
            prices = DailyPrice.objects.filter(stock=stock).order_by("date")
            if prices.count() < 20:
                continue

            # 2. DataFrame 변환
            df = pd.DataFrame(list(prices.values("id", "close_price")))

            # 3. 지표 계산 (pandas-ta)
            df["ma5"] = ta.sma(df["close_price"], length=5)
            df["ma20"] = ta.sma(df["close_price"], length=20)
            df["ma60"] = ta.sma(df["close_price"], length=60)
            df["rsi"] = ta.rsi(df["close_price"], length=14)

            # 4. DB 업데이트 (최근 30일치만 업데이트)
            updates = []
            for i, row in df.tail(30).iterrows():
                if pd.isna(row["ma5"]):
                    continue

                updates.append(
                    DailyPrice(
                        id=row["id"],
                        ma5=row["ma5"],
                        ma20=row["ma20"],
                        ma60=row["ma60"],
                        rsi=row["rsi"],
                    )
                )

            if updates:
                DailyPrice.objects.bulk_update(updates, ["ma5", "ma20", "ma60", "rsi"])
                count += 1

        self.stdout.write(
            self.style.SUCCESS(f"✨ 총 {count}개 종목 지표 업데이트 완료!")
        )
