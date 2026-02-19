import FinanceDataReader as fdr  # 새로 설치한 라이브러리
from django.core.management.base import BaseCommand

from stocks.models import Stock
from stocks.services import fetch_and_save_stock_data


class Command(BaseCommand):
    help = "FinanceDataReader를 이용해 KRX 전 종목을 가져오고 시세를 수집합니다."

    def handle(self, *args, **kwargs):
        self.stdout.write("📥 KRX 종목 리스트 다운로드 중 (via FinanceDataReader)...")

        try:
            # KRX 전체 리스트 가져오기 (KOSPI, KOSDAQ, KONEX 포함)
            # 컬럼: Code, Name, Market, Sector, Industry ...
            df_krx = fdr.StockListing("KRX")

            # 우선 KOSPI와 KOSDAQ만 필터링 (KONEX 제외)
            df = df_krx[df_krx["Market"].isin(["KOSPI", "KOSDAQ"])]

            total = len(df)
            self.stdout.write(f"✅ 총 {total}개 종목 발견 (KOSPI/KOSDAQ).")

            count = 0
            for index, row in df.iterrows():
                code = str(row["Code"])  # 005930
                name = row["Name"]  # 삼성전자
                market = row["Market"]  # KOSPI or KOSDAQ

                # DB에 저장 (시장 구분까지 확실하게!)
                stock, created = Stock.objects.update_or_create(
                    code=code,
                    defaults={
                        "name": name,
                        "market": market,  # 이제 여기서 정확히 저장됩니다!
                    },
                )

                # 진행 상황 표시 (20개마다 로그 찍기)
                if count % 20 == 0:
                    self.stdout.write(
                        f"[{count + 1}/{total}] {name}({market}) 저장 및 시세 수집 중..."
                    )

                # 시세 수집 실행 (services.py)
                # 이제 market이 확실하므로 services.py가 헤매지 않습니다.
                fetch_and_save_stock_data(code)

                count += 1

            self.stdout.write(
                self.style.SUCCESS(f"🎉 모든 작업 완료! 총 {count}개 종목 처리됨.")
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 실패: {e}"))
