# stocks/management/commands/init_stocks.py
from django.core.management.base import BaseCommand

from stocks.services import update_all_stock_codes


class Command(BaseCommand):
    help = "한국거래소(KRX) 데이터를 이용하여 전체 종목 리스트를 초기화합니다."

    def handle(self, *args, **options):
        self.stdout.write("전체 종목 리스트 다운로드 및 DB 동기화 시작...")

        success_count, total_count = update_all_stock_codes()

        if total_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"총 {total_count}개 중 {success_count}개 종목 업데이트 완료!"
                )
            )
        else:
            self.stdout.write(self.style.ERROR("종목 정보를 가져오는데 실패했습니다."))
