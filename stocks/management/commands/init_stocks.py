from django.core.management.base import BaseCommand

from stocks.models import Stock
from stocks.services import fetch_and_save_stock_data, update_all_stock_codes


class Command(BaseCommand):
    help = "한국거래소(KRX) 데이터를 이용하여 전체 종목을 초기화하고 가격 데이터를 수집합니다."

    def handle(self, *args, **options):
        # ---------------------------------------------------------
        # 1단계: 전체 종목 코드 리스트 업데이트
        # ---------------------------------------------------------
        self.stdout.write("1. 전체 종목 리스트 다운로드 및 DB 동기화 시작...")

        # [수정] services.py가 반환하는 2개의 값(성공수, 전체수)을 받습니다.
        try:
            success_count, total_count = update_all_stock_codes()
            self.stdout.write(
                f"   -> 결과: {total_count}개 중 {success_count}개 종목 코드 확보 완료."
            )
        except TypeError:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️ services.py에서 반환값이 오지 않았습니다. (코드 수집은 완료되었을 수 있음)"
                )
            )
            success_count, total_count = 0, 0

        # ---------------------------------------------------------
        # 2단계: 개별 종목 일봉 데이터 수집
        # ---------------------------------------------------------
        self.stdout.write("\n2. 개별 종목 일봉 데이터 수집 시작...")

        stocks = Stock.objects.all()
        total_stocks = stocks.count()

        if total_stocks == 0:
            self.stdout.write(
                self.style.ERROR("❌ 저장된 종목이 없습니다. 1단계를 확인해주세요.")
            )
            return

        # 진행 상황을 보기 위해 반복문 실행
        for i, stock in enumerate(stocks):
            # 로그가 너무 많으면 느려지므로 10개마다, 혹은 중요 종목만 출력
            # 여기서는 진행률을 100개 단위로 찍어줍니다.
            if i % 100 == 0:
                self.stdout.write(f"   ... [{i}/{total_stocks}] 데이터 수집 진행 중")

            fetch_and_save_stock_data(stock.code)

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✨ 모든 작업 완료! (총 {total_stocks}개 종목 처리됨)"
            )
        )
