from django.core.management.base import BaseCommand

from stocks.models import Stock
from stocks.trading_service import KisTrading


class Command(BaseCommand):
    help = "한국투자증권 API 연결 및 모의 매매 테스트"

    def handle(self, *args, **options):
        self.stdout.write("🔌 한국투자증권 API 연결 테스트 시작...")

        # 1. 트레이딩 봇 객체 생성
        try:
            bot = KisTrading()

            # [✨ 핵심 수정] 봇을 만들고 나서, '토큰 발급'을 명시적으로 실행해야 합니다!
            if bot._get_access_token():
                self.stdout.write(
                    self.style.SUCCESS(f"✅ 토큰 발급 성공! (API 연결 정상)")
                )
                self.stdout.write(f"👉 발급된 토큰(일부): {bot.access_token[:20]}...")
            else:
                self.stdout.write(
                    self.style.ERROR(
                        "❌ 토큰 발급 실패. (위의 디버그 로그를 확인하세요)"
                    )
                )
                return

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 초기화 중 에러 발생: {e}"))
            return

        # 2. 테스트용 종목 설정 (삼성전자: 005930)
        stock_code = "005930"
        # DB에 종목이 없으면 임시로 생성 (테스트를 위해)
        stock, created = Stock.objects.get_or_create(
            code=stock_code, defaults={"name": "삼성전자", "market": "KOSPI"}
        )

        self.stdout.write(f"\n📈 [{stock.name}] 1주 시장가 매수 주문 전송 중...")

        # 3. 매수 주문 실행
        success = bot.buy_stock(stock_code, quantity=1)

        if success:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ 테스트 완료! 모의투자 앱에서 주문 체결을 확인하세요."
                )
            )
        else:
            self.stdout.write(self.style.ERROR("❌ 매수 주문 전송 실패."))
