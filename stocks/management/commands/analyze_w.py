# stocks/management/commands/analyze_w.py
from django.core.management.base import BaseCommand

from stocks.models import Stock
from stocks.services import analyze_w_pattern


class Command(BaseCommand):
    help = "DB의 모든 종목을 전수 조사하여 W곡선(쌍바닥) 패턴을 분석합니다."

    def handle(self, *args, **kwargs):
        # 1. 분석 대상 가져오기
        stocks = Stock.objects.all()
        total = stocks.count()

        self.stdout.write(
            self.style.SUCCESS(f"🚀 총 {total}개 종목에 대한 W패턴 분석을 시작합니다.")
        )

        found_count = 0

        # 2. 전 종목 분석 루프
        for idx, stock in enumerate(stocks, 1):
            try:
                # services.py에서 만든 함수 호출
                is_w = analyze_w_pattern(stock.code)

                if is_w:
                    found_count += 1
                    # 패턴 발견 시 종목명 출력
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  [발견] {stock.name}({stock.code}) - 패턴 점수: {stock.w_score}점"
                        )
                    )

                # 100개마다 진행 상황 출력
                if idx % 100 == 0:
                    self.stdout.write(f"🔄 분석 진행 중... ({idx}/{total})")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  [에러] {stock.name}: {e}"))

        # 3. 결과 요약
        self.stdout.write("---" * 10)
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ 분석 완료! 총 {found_count}개의 W패턴 후보를 찾았습니다."
            )
        )
        self.stdout.write("---" * 10)
