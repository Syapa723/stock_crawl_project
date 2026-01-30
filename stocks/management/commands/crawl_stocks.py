from django.core.management.base import BaseCommand

from stocks.models import Stock
from stocks.services import fetch_and_save_stock_data


class Command(BaseCommand):
    help = "여러 종목의 주가 데이터를 크롤링합니다."

    def add_arguments(self, parser):
        # nargs='*' : 인자를 0개 이상 받을 수 있음을 의미합니다.
        # 인자가 없으면 빈 리스트 []가 들어옵니다.
        parser.add_argument(
            "codes",
            nargs="*",
            type=str,
            help="종목코드들 (공백으로 구분, 비워두면 모든 종목 업데이트)",
        )

    def handle(self, *args, **options):
        codes = options["codes"]

        # 1. 인자가 입력되지 않았다면 -> DB에 있는 '모든 종목'을 가져옵니다.
        if not codes:
            self.stdout.write(
                "종목 코드가 입력되지 않아, 저장된 모든 종목을 업데이트합니다."
            )
            # 저장된 모든 Stock 객체에서 코드만 리스트로 추출
            codes = [s.code for s in Stock.objects.all()]

            if not codes:
                self.stdout.write(
                    self.style.WARNING(
                        "저장된 종목이 없습니다. 코드를 입력해서 실행해주세요."
                    )
                )
                return

        # 2. 리스트에 있는 모든 코드를 순회하며 크롤링 실행
        total = len(codes)
        self.stdout.write(f"총 {total}개의 종목 작업을 시작합니다...")

        success_count = 0
        for index, code in enumerate(codes, 1):
            self.stdout.write(f"[{index}/{total}] {code} 크롤링 중...", ending="")

            # 서비스 함수 호출
            result = fetch_and_save_stock_data(code)

            if result > 0:
                self.stdout.write(self.style.SUCCESS(" 완료"))
                success_count += 1
            else:
                self.stdout.write(self.style.WARNING(" 실패/데이터없음"))

        self.stdout.write(
            self.style.SUCCESS(f"\n모든 작업 종료! ({success_count}/{total} 성공)")
        )
