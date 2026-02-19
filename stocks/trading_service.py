import json
import os

import requests

from .models import Stock, TradeLog


class KisTrading:
    def __init__(self):
        # [✨ 핵심 수정 1] .strip()을 추가하여 .env 복사/붙여넣기 시 딸려온 공백 제거
        self.mode = os.environ.get("KIS_MODE", "VIRTUAL").strip()
        self.app_key = os.environ.get("KIS_APP_KEY", "").strip()
        self.app_secret = os.environ.get("KIS_APP_SECRET", "").strip()
        self.acc_no = os.environ.get("KIS_ACCOUNT_NO", "").strip()
        # 계좌 상품코드는 보통 '01'이므로 기본값 설정
        self.acc_code = os.environ.get("KIS_ACCOUNT_PRDT_CODE", "01").strip()

        # 모의투자 vs 실전투자 URL 구분
        if self.mode == "VIRTUAL":
            self.base_url = "https://openapivts.koreainvestment.com:29443"
            print(f"🤖 [KisTrading] 모의투자(VIRTUAL) 모드로 초기화됨")
        else:
            self.base_url = "https://openapi.koreainvestment.com:9443"
            print(f"💰 [KisTrading] 실전투자(REAL) 모드로 초기화됨")

        self.access_token = None

    def _get_access_token(self):
        """토큰 발급"""
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }

        try:
            res = requests.post(url, headers=headers, data=json.dumps(body))
            data = res.json()

            # [✨ 핵심 수정 2] 실패 원인을 상세하게 출력 (디버깅용)
            if "access_token" not in data:
                print(f"\n🔥🔥 [API 오류] 토큰 발급 실패! 응답 내용 확인 필요:")
                print(f"👉 응답 코드: {res.status_code}")
                print(f"👉 응답 본문: {data}")
                print(f"👉 사용된 앱키(앞5자리): {self.app_key[:5]}...")
                return False

            self.access_token = data["access_token"]
            return True

        except Exception as e:
            print(f"❌ 토큰 요청 중 예외 발생: {e}")
            return False

    def _get_common_headers(self, tr_id):
        # 토큰이 없으면 발급 시도
        if not self.access_token:
            if not self._get_access_token():
                raise Exception("API 토큰 발급에 실패하여 헤더를 생성할 수 없습니다.")

        return {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
        }

    def buy_stock(self, stock_code, quantity, price=0):
        """시장가 매수 주문"""
        # 모의투자: VTTC0802U / 실전: TTTC0802U
        tr_id = "VTTC0802U" if self.mode == "VIRTUAL" else "TTTC0802U"
        return self._place_order(stock_code, quantity, price, tr_id, "BUY")

    def sell_stock(self, stock_code, quantity, price=0):
        """시장가 매도 주문"""
        # 모의투자: VTTC0801U / 실전: TTTC0801U
        tr_id = "VTTC0801U" if self.mode == "VIRTUAL" else "TTTC0801U"
        return self._place_order(stock_code, quantity, price, tr_id, "SELL")

    def _place_order(self, stock_code, quantity, price, tr_id, trade_type):
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"

        try:
            headers = self._get_common_headers(tr_id)

            # 시장가(01) 주문
            data = {
                "CANO": self.acc_no,
                "ACNT_PRDT_CD": self.acc_code,
                "PDNO": stock_code,
                "ORD_DVSN": "01",  # 01: 시장가
                "ORD_QTY": str(quantity),
                "ORD_UNPR": "0" if price == 0 else str(price),
            }

            print(f"📡 [{trade_type}] 주문 전송 중... ({stock_code}, {quantity}주)")
            res = requests.post(url, headers=headers, data=json.dumps(data))
            result = res.json()

            # 주문 결과 로깅
            if result.get("rt_cd") == "0":
                print(
                    f"✅ [{trade_type}] 주문 성공! (주문번호: {result.get('output', {}).get('ODNO', 'Unknown')})"
                )
                success = True
            else:
                print(f"❌ [{trade_type}] 주문 거부됨: {result.get('msg1')}")
                print(f"   상세 코드: {result.get('msg_cd')}")
                success = False

            # DB에 기록
            try:
                stock = Stock.objects.get(code=stock_code)
                TradeLog.objects.create(
                    stock=stock,
                    trade_type=trade_type,
                    price=price,
                    quantity=quantity,
                    result_msg=result.get("msg1", str(result)),
                )
            except Exception as e:
                print(f"⚠️ DB 로그 저장 실패 (주문은 실행됨): {e}")

            return success

        except Exception as e:
            print(f"❌ 주문 실행 중 치명적 오류: {e}")
            return False

    def get_balance(self):
        """주문 가능 현금(예수금) 조회"""
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-psbl-order"

        # 모의투자: VTTC8908U / 실전: TTTC8908U (매수가능금액 조회용)
        tr_id = "VTTC8908U" if self.mode == "VIRTUAL" else "TTTC8908U"
        headers = self._get_common_headers(tr_id)

        params = {
            "CANO": self.acc_no,
            "ACNT_PRDT_CD": self.acc_code,
            "PDNO": "",  # 종목번호 공란
            "ORD_UNPR": "0",
            "ORD_DVSN": "01",
            "CMA_EVLU_AMT_ICLD_YN": "Y",
            "OVRS_ICLD_YN": "Y",
        }

        try:
            res = requests.get(url, headers=headers, params=params)
            data = res.json()

            if data["rt_cd"] == "0":
                # 'ord_psbl_cash': 주문 가능 현금
                cash = int(data["output"]["ord_psbl_cash"])
                print(f"💰 현재 주문 가능 현금: {cash:,}원")
                return cash
            else:
                print(f"❌ 잔고 조회 실패: {data['msg1']}")
                return 0
        except Exception as e:
            print(f"❌ 잔고 조회 중 에러: {e}")
            return 0
