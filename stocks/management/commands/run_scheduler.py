import asyncio
import logging
import os

import discord
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django_apscheduler.jobstores import DjangoJobStore

from stocks.models import DailyPrice, Stock
from stocks.trading_service import KisTrading  # [필수] 트레이딩 서비스 임포트

logger = logging.getLogger(__name__)


# ==========================================
# 1. 작업 정의 (Job Functions)
# ==========================================


def job_crawl_data():
    """[오전 7시] 데이터 수집"""
    print("\n🌅 [1단계] 데이터 수집(크롤링) 시작...")
    try:
        call_command("init_stocks")
        print("✅ 데이터 수집 완료!")
    except Exception as e:
        print(f"❌ 데이터 수집 중 오류: {e}")


def job_analyze_data():
    """[오전 8시] 데이터 분석"""
    print("\n⚙️ [2단계] 기술적 지표 분석(RSI, 이평선) 시작...")
    try:
        call_command("calculate_indicators")
        print("✅ 데이터 분석 완료!")
    except Exception as e:
        print(f"❌ 데이터 분석 중 오류: {e}")


def job_send_notification():
    """[오전 8시 30분] 디스코드 알림 및 자동매매"""
    print("\n📢 [3단계] 알림 발송 및 자동매매 시작...")
    try:
        asyncio.run(send_discord_notice())
    except Exception as e:
        print(f"❌ 알림 발송 중 오류: {e}")


# ==========================================
# 2. 비동기 알림 및 매매 로직 (통합됨)
# ==========================================


async def send_discord_notice():
    TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
    # 🚨 [필수] 본인의 디스코드 채널 ID로 변경해주세요!
    CHANNEL_ID = 1472202952839266414

    # ⚙️ [자금 관리 설정]
    TARGET_BUY_AMOUNT = 1000000  # 한 종목당 매수 목표 금액 (100만 원)

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    await client.login(TOKEN)
    channel = await client.fetch_channel(CHANNEL_ID)

    # 1. 트레이딩 봇 초기화 및 잔고 조회
    bot = KisTrading()
    try:
        # API 호출은 동기식이므로 sync_to_async로 감싸야 함
        available_cash = await sync_to_async(bot.get_balance)()
    except Exception:
        available_cash = 0
        print("⚠️ 잔고 조회 실패 (매수 기능 비활성화)")

    # 2. 유망 종목 가져오기 (W패턴 포착 종목)
    stocks = await sync_to_async(list)(
        Stock.objects.filter(is_w_pattern=True).order_by("-w_score")[:30]
    )

    candidates = []

    # 3. 종목 분석 및 매매 루프
    for stock in stocks:
        get_latest = sync_to_async(
            lambda: DailyPrice.objects.filter(stock=stock).order_by("-date").first()
        )
        latest = await get_latest()

        if not latest:
            continue

        ma5 = latest.ma5 or 0
        ma20 = latest.ma20 or 0
        rsi = latest.rsi or 50

        # [기본 필터링] 정배열(5일>20일) + RSI 적정 구간(40~65)
        if ma5 > ma20 and 40 <= rsi <= 65:
            note = ""  # 비고란 (매수 여부 표시)

            # -------------------------------------------------------
            # 🚀 [자동매매 로직]
            # 조건: 기본 필터링을 통과한 것 중, W점수가 90점 이상이고 RSI가 55 이하인 '특급' 종목
            # -------------------------------------------------------
            if stock.w_score >= 90 and rsi <= 55:
                # 1) 매수 수량 계산 (목표금액 / 현재가)
                quantity = 0
                if available_cash >= TARGET_BUY_AMOUNT:
                    quantity = int(TARGET_BUY_AMOUNT / latest.close_price)

                # 2) 매수 실행
                if quantity > 0:
                    print(
                        f"🚀 [자동매수 진입] {stock.name} {quantity}주 (가격: {latest.close_price}원)"
                    )

                    # 실제 주문 전송 (DB 저장 포함되므로 sync_to_async 필수)
                    success = await sync_to_async(bot.buy_stock)(stock.code, quantity)

                    if success:
                        available_cash -= (
                            quantity * latest.close_price
                        )  # 잔고 차감 반영 (단순 계산)
                        note = f"\n✅ **{quantity}주 자동매수 체결!**"
                    else:
                        note = "\n❌ 매수 주문 실패"
                elif available_cash < TARGET_BUY_AMOUNT:
                    note = "\n💸 자금 부족으로 매수 패스"

            # 리스트에 추가 (디스코드 전송용)
            candidates.append(
                {
                    "name": stock.name,
                    "code": stock.code,
                    "score": stock.w_score,
                    "price": latest.close_price,
                    "rsi": rsi,
                    "note": note,
                }
            )

    # 상위 10개 알림 발송
    top_10 = candidates[:10]

    if top_10:
        embed = discord.Embed(
            title="🔥 [테스트] 단타 유망주 & 자동매매 리포트",
            description=f"현재 잔고: {available_cash:,.0f}원 | 분석 및 매매 결과입니다.",
            color=0xFF5722,
        )
        for i, item in enumerate(top_10, 1):
            embed.add_field(
                name=f"{i}위. {item['name']} ({item['score']}점)",
                value=f"💰 {item['price']:,}원 | RSI: {item['rsi']:.1f}{item['note']}",
                inline=False,
            )
        await channel.send(embed=embed)
        print("✅ 디스코드 메시지 전송 성공")
    else:
        await channel.send("🧪 [테스트] 조건에 맞는 종목이 없습니다.")

    await client.close()


# ==========================================
# 3. 스케줄러 커맨드 클래스
# ==========================================


class Command(BaseCommand):
    help = "주식 자동화 루틴 실행 (크롤링 -> 분석 -> 알림 -> 매매)"

    def add_arguments(self, parser):
        parser.add_argument("--test", action="store_true", help="즉시 실행 모드")

    def handle(self, *args, **options):
        # [테스트 모드]
        if options["test"]:
            print("🧪 [테스트 모드] 루틴을 즉시 실행합니다!")
            job_crawl_data()
            job_analyze_data()
            job_send_notification()
            print("✨ 테스트가 모두 완료되었습니다.")
            return

        # [스케줄러 모드]
        scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), "default")

        scheduler.add_job(
            job_crawl_data,
            trigger=CronTrigger(day_of_week="mon-fri", hour="07", minute="00"),
            id="daily_crawling",
            replace_existing=True,
        )
        scheduler.add_job(
            job_analyze_data,
            trigger=CronTrigger(day_of_week="mon-fri", hour="08", minute="00"),
            id="daily_analysis",
            replace_existing=True,
        )
        scheduler.add_job(
            job_send_notification,
            trigger=CronTrigger(day_of_week="mon-fri", hour="08", minute="30"),
            id="morning_brief",
            replace_existing=True,
        )

        print("\n🚀 스케줄러가 시작되었습니다! (매일 아침 7시부터 가동)")
        try:
            scheduler.start()
        except KeyboardInterrupt:
            scheduler.shutdown()
