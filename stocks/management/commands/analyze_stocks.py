from django.core.management.base import BaseCommand

from stocks.models import Stock

# 방금 만든 알림 함수(send_discord_alert)를 추가로 임포트합니다.
from stocks.services import analyze_stock_trend, send_discord_alert


class Command(BaseCommand):
    help = "DB의 종목들을 분석하여 특이 종목을 찾아내고 디스코드 알림을 보냅니다."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("🔍 시장 분석을 시작합니다..."))

        # 테스트를 위해 우선 20개만 먼저 돌려봅니다 (나중엔 .all()로 변경)
        stocks = Stock.objects.all()[:20]

        found_count = 0
        for stock in stocks:
            result = analyze_stock_trend(stock.code)

            # 분석 결과가 있고(None 아님), 특이 종목(is_unusual)이라면?
            if result and result["is_unusual"]:
                message = f"🔥 특이종목 발견! [{stock.name}] 거래량 {result['volume_ratio']}% 폭증"
                self.stdout.write(self.style.WARNING(message))

                # [핵심] 여기서 디스코드 알림을 쏩니다! 🚀
                send_discord_alert(
                    stock_name=stock.name,
                    code=stock.code,
                    price=result["current_price"],
                    ratio=result["price_change_pct"],
                    volume_ratio=result["volume_ratio"],
                )

                found_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"✅ 분석 완료. 총 {found_count}개의 알림을 보냈습니다.")
        )
