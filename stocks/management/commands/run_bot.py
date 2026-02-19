import os

import discord
import matplotlib
from asgiref.sync import sync_to_async
from discord.ext import commands
from django.core.management.base import BaseCommand
from django.db.models import Q

from stocks.ai_service import analyze_stock_with_gemini
from stocks.models import DailyPrice, Stock

matplotlib.use("Agg")
import io

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

# 폰트 설정
font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
if os.path.exists(font_path):
    fm.fontManager.addfont(font_path)
    font_name = fm.FontProperties(fname=font_path).get_name()
    plt.rc("font", family=font_name)
else:
    plt.rc("font", family="sans-serif")

plt.rcParams["axes.unicode_minus"] = False


# [차트 생성 함수] - 데이터가 부족할 경우를 대비한 안전장치 강화
def create_stock_chart(stock):
    prices = DailyPrice.objects.filter(stock=stock).order_by("-date")[:30]
    prices = list(reversed(prices))
    if not prices or len(prices) < 2:
        return None

    dates = [p.date.strftime("%m-%d") for p in prices]
    closes = [p.close_price for p in prices]

    plt.figure(figsize=(10, 5), dpi=100)
    plt.plot(
        dates,
        closes,
        marker="o",
        linestyle="-",
        color="#6200ea",
        linewidth=2,
        markersize=5,
    )
    plt.title(
        f"{stock.name} ({stock.code}) - 최근 30일 주가", fontsize=15, fontweight="bold"
    )
    plt.xlabel("날짜", fontsize=12)
    plt.ylabel("종가 (원)", fontsize=12)
    plt.grid(True, which="both", linestyle="--", linewidth=0.5)
    plt.xticks(range(0, len(dates), 5), rotation=45)
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    plt.close()
    return buffer


class Command(BaseCommand):
    help = "디스코드 주식 봇을 실행합니다."

    def handle(self, *args, **options):
        TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
        if not TOKEN:
            self.stdout.write(
                self.style.ERROR("❌ .env 파일에 DISCORD_BOT_TOKEN이 없습니다!")
            )
            return

        intents = discord.Intents.default()
        intents.message_content = True
        bot = commands.Bot(command_prefix="!", intents=intents)

        @bot.event
        async def on_ready():
            print(f"🤖 {bot.user} 봇이 안전 모드로 가동 중입니다!")

        # [명령어 1] !주식 - 안전한 포맷팅 적용
        @bot.command(name="주식")
        async def stock_info(ctx, keyword: str):
            get_stock = sync_to_async(
                lambda: Stock.objects.filter(
                    Q(name__icontains=keyword) | Q(code=keyword)
                ).first()
            )
            stock = await get_stock()

            if not stock:
                await ctx.send(f"😭 '{keyword}' 종목을 찾을 수 없습니다.")
                return

            get_price = sync_to_async(
                lambda: DailyPrice.objects.filter(stock=stock).order_by("-date").first()
            )
            latest = await get_price()

            if not latest:
                await ctx.send(f"❌ '{stock.name}'의 시세 데이터가 없습니다.")
                return

            # [✨ 핵심 수정] None 값을 체크하여 안전하게 문자열로 변환합니다.
            rsi_val = f"{latest.rsi:.1f}" if latest.rsi is not None else "데이터 없음"

            # 이평선 상태 판단 시 None 값은 0으로 처리하여 연산 오류 방지
            m5, m20, m60 = latest.ma5 or 0, latest.ma20 or 0, latest.ma60 or 0
            ma_trend = "정배열(상승)" if m5 > m20 > m60 else "역배열/혼조"

            embed = discord.Embed(
                title=f"📈 {stock.name} ({stock.code})", color=0x00FF00
            )
            embed.add_field(
                name="현재가", value=f"{latest.close_price:,}원", inline=True
            )
            embed.add_field(name="W-점수", value=f"{stock.w_score}점", inline=True)
            embed.add_field(name="📊 RSI 지수", value=rsi_val, inline=True)
            embed.add_field(name="📉 이평선 추세", value=ma_trend, inline=True)
            embed.set_footer(text=f"기준일: {latest.date} | 시장: {stock.market}")

            await ctx.send(embed=embed)

        # [명령어 2] !추천
        @bot.command(name="추천")
        async def recommend(ctx):
            await ctx.send("🔍 W-패턴 유망주 TOP 10을 추출 중입니다...")
            get_top = sync_to_async(
                lambda: list(
                    Stock.objects.filter(is_w_pattern=True).order_by("-w_score")[:10]
                )
            )
            top_stocks = await get_top()

            if not top_stocks:
                await ctx.send("분석된 종목이 없습니다.")
                return

            embed = discord.Embed(title="🏆 W-패턴 강력 추천 TOP 10", color=0xFFD700)
            for i, s in enumerate(top_stocks, 1):
                embed.add_field(
                    name=f"{i}위. {s.name}",
                    value=f"코드: {s.code} ({s.w_score}점)",
                    inline=False,
                )
            await ctx.send(embed=embed)

        # [명령어 3] !분석 - 안전한 지표 요약 적용
        @bot.command(name="분석")
        async def analyze(ctx, keyword: str):
            get_stock = sync_to_async(
                lambda: Stock.objects.filter(
                    Q(name__icontains=keyword) | Q(code=keyword)
                ).first()
            )
            stock = await get_stock()

            if not stock:
                await ctx.send(f"😭 '{keyword}' 종목을 찾을 수 없습니다.")
                return

            waiting_msg = await ctx.send(
                f"🤖 **[{stock.name}]** AI 전문 분석 리포트 생성 중..."
            )

            try:
                run_ai = sync_to_async(analyze_stock_with_gemini)
                result_text = await run_ai(stock)

                generate_chart = sync_to_async(create_stock_chart)
                chart_buffer = await generate_chart(stock)
                chart_file = (
                    discord.File(chart_buffer, filename="chart.png")
                    if chart_buffer
                    else None
                )

                get_latest = sync_to_async(
                    lambda: DailyPrice.objects.filter(stock=stock)
                    .order_by("-date")
                    .first()
                )
                latest = await get_latest()

                embed = discord.Embed(
                    title=f"✨ {stock.name} AI 전문 투자 리포트",
                    description=result_text[:4000],
                    color=0x6200EA,
                )

                if latest:
                    # [✨ 핵심 수정] RSI가 None일 경우를 대비한 안전한 텍스트 처리
                    rsi_num = latest.rsi if latest.rsi is not None else 50
                    rsi_status = (
                        "과매도(바닥)"
                        if rsi_num < 30
                        else "과매수(주의)" if rsi_num > 70 else "보통"
                    )
                    rsi_display = (
                        f"{latest.rsi:.1f}" if latest.rsi is not None else "N/A"
                    )

                    embed.add_field(
                        name="RSI 상태",
                        value=f"{rsi_display} ({rsi_status})",
                        inline=True,
                    )
                    embed.add_field(
                        name="장기추세(MA60)",
                        value=(
                            "상승"
                            if latest.close_price > (latest.ma60 or 0)
                            else "하락"
                        ),
                        inline=True,
                    )

                if chart_file:
                    embed.set_image(url="attachment://chart.png")
                    await waiting_msg.edit(
                        content="✅ 분석이 완료되었습니다!",
                        embed=embed,
                        attachments=[chart_file],
                    )
                else:
                    await waiting_msg.edit(
                        content="✅ 분석 완료! (차트 데이터 부족)", embed=embed
                    )

            except Exception as e:
                await waiting_msg.edit(content=f"❌ 오류 발생: {str(e)}")

        bot.run(TOKEN)
