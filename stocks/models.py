from django.db import models


class Stock(models.Model):
    name = models.CharField(max_length=50, verbose_name="종목명")
    code = models.CharField(max_length=10, unique=True, verbose_name="종목코드")

    def __str__(self):
        return f"{self.name} ({self.code})"


class DailyPrice(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="prices")
    date = models.DateField(verbose_name="날짜")
    open_price = models.IntegerField(verbose_name="시가")
    high_price = models.IntegerField(verbose_name="고가")
    low_price = models.IntegerField(verbose_name="저가")
    close_price = models.IntegerField(verbose_name="종가")
    volume = models.BigIntegerField(verbose_name="거래량")

    class Meta:
        unique_together = ("stock", "date")  # 같은 날짜 중복 저장 방지
