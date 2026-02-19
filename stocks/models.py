from django.db import models


class Stock(models.Model):
    # [기본 정보]
    # ETF 등 긴 종목명을 대비해 50 -> 100으로 확장
    name = models.CharField(max_length=100, verbose_name="종목명")

    # 티커 외에 ISIN 코드 등이 들어올 수 있으므로 10 -> 20으로 확장
    code = models.CharField(max_length=20, unique=True, verbose_name="종목코드")

    # [✨ 핵심 수정] "KOSDAQ GLOBAL"(13자) 등을 저장하기 위해 10 -> 50으로 확장
    market = models.CharField(
        max_length=50, null=True, blank=True, verbose_name="시장구분"
    )

    # [AI 분석 데이터]
    current_price = models.IntegerField(null=True, blank=True, verbose_name="현재가")
    price_change = models.FloatField(null=True, blank=True, verbose_name="등락률")
    volume_change = models.FloatField(
        null=True, blank=True, verbose_name="거래량변동률"
    )

    # [AI 판단 결과]
    # "STRONG BUY" 등 긴 텍스트 대비 10 -> 20으로 확장 추천
    ai_decision = models.CharField(max_length=20, default="HOLD", verbose_name="AI추천")
    ai_score = models.IntegerField(default=0, verbose_name="AI점수")

    # [W 패턴 분석 필드]
    is_w_pattern = models.BooleanField(default=False, verbose_name="W패턴여부")
    w_score = models.IntegerField(default=0, verbose_name="W패턴점수")

    last_analyzed = models.DateTimeField(null=True, blank=True, verbose_name="분석시간")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class DailyPrice(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="prices")
    date = models.DateField(verbose_name="날짜")

    open_price = models.IntegerField(verbose_name="시가")
    high_price = models.IntegerField(verbose_name="고가")
    low_price = models.IntegerField(verbose_name="저가")
    close_price = models.IntegerField(verbose_name="종가")

    # 거래량은 21억을 넘을 수 있으므로 BigIntegerField 유지 (아주 좋습니다)
    volume = models.BigIntegerField(verbose_name="거래량")

    # 보조 지표
    ma5 = models.FloatField(null=True, blank=True)
    ma20 = models.FloatField(null=True, blank=True)
    ma60 = models.FloatField(null=True, blank=True)
    rsi = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ("stock", "date")

    # 모의 투자 자동 매매


class TradeLog(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    trade_type = models.CharField(max_length=10)  # BUY / SELL
    price = models.IntegerField()  # 체결가
    quantity = models.IntegerField()  # 수량
    timestamp = models.DateTimeField(auto_now_add=True)
    result_msg = models.CharField(
        max_length=255, null=True, blank=True
    )  # API 응답 메시지

    def __str__(self):
        return (
            f"[{self.trade_type}] {self.stock.name} - {self.quantity}주 @ {self.price}"
        )
