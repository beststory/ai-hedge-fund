"""
환율 데이터 수집 도구

Yahoo Finance를 통해 환율 데이터를 수집합니다.
- 원/달러 (KRW/USD)
- 달러 인덱스 (DXY)
- 주요 통화쌍
"""

import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ForexDataCollector:
    """환율 데이터 수집 클래스"""

    # 주요 환율 심볼 매핑
    FOREX_SYMBOLS = {
        "USDKRW": "USDKRW=X",  # 달러/원
        "KRWUSD": "KRW=X",  # 원/달러
        "DXY": "DX-Y.NYB",  # 달러 인덱스
        "EURUSD": "EURUSD=X",  # 유로/달러
        "USDJPY": "USDJPY=X",  # 달러/엔
        "GBPUSD": "GBPUSD=X",  # 파운드/달러
        "USDCNY": "USDCNY=X",  # 달러/위안
    }

    def __init__(self):
        """초기화"""
        self.cache = {}
        self.cache_timeout = 300  # 5분 캐시

    def get_current_rate(self, symbol: str) -> Optional[Dict]:
        """
        현재 환율 조회

        Args:
            symbol: 환율 심볼 (예: "USDKRW", "DXY")

        Returns:
            환율 정보 딕셔너리
        """
        try:
            # 심볼 매핑
            yahoo_symbol = self.FOREX_SYMBOLS.get(symbol, symbol)

            # 캐시 확인
            cache_key = f"{symbol}_current"
            if cache_key in self.cache:
                cached_time, cached_data = self.cache[cache_key]
                if (datetime.now() - cached_time).seconds < self.cache_timeout:
                    return cached_data

            # Yahoo Finance에서 조회
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info

            result = {
                "symbol": symbol,
                "rate": info.get("regularMarketPrice", None),
                "previous_close": info.get("regularMarketPreviousClose", None),
                "change": info.get("regularMarketChange", None),
                "change_percent": info.get("regularMarketChangePercent", None),
                "bid": info.get("bid", None),
                "ask": info.get("ask", None),
                "timestamp": datetime.now().isoformat()
            }

            # 캐시 저장
            self.cache[cache_key] = (datetime.now(), result)

            logger.info(f"✅ {symbol} 환율 조회 성공: {result['rate']}")
            return result

        except Exception as e:
            logger.error(f"❌ {symbol} 환율 조회 실패: {e}")
            return None

    def get_historical_rates(
        self,
        symbol: str,
        period: str = "1mo",
        start: Optional[str] = None,
        end: Optional[str] = None
    ) -> Optional[Dict]:
        """
        과거 환율 데이터 조회

        Args:
            symbol: 환율 심볼
            period: 기간 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            start: 시작 날짜 (YYYY-MM-DD)
            end: 종료 날짜 (YYYY-MM-DD)

        Returns:
            환율 히스토리 데이터
        """
        try:
            yahoo_symbol = self.FOREX_SYMBOLS.get(symbol, symbol)
            ticker = yf.Ticker(yahoo_symbol)

            if start and end:
                hist = ticker.history(start=start, end=end)
            else:
                hist = ticker.history(period=period)

            if hist.empty:
                logger.warning(f"⚠️ {symbol} 환율 히스토리 데이터 없음")
                return None

            result = {
                "symbol": symbol,
                "period": period,
                "start_date": hist.index[0].strftime("%Y-%m-%d"),
                "end_date": hist.index[-1].strftime("%Y-%m-%d"),
                "data": {
                    "dates": [d.strftime("%Y-%m-%d") for d in hist.index],
                    "close": hist["Close"].tolist(),
                    "open": hist["Open"].tolist(),
                    "high": hist["High"].tolist(),
                    "low": hist["Low"].tolist(),
                    "volume": hist["Volume"].tolist() if "Volume" in hist.columns else []
                },
                "statistics": {
                    "current": float(hist["Close"].iloc[-1]),
                    "start": float(hist["Close"].iloc[0]),
                    "min": float(hist["Close"].min()),
                    "max": float(hist["Close"].max()),
                    "mean": float(hist["Close"].mean()),
                    "std": float(hist["Close"].std()),
                    "change": float(hist["Close"].iloc[-1] - hist["Close"].iloc[0]),
                    "change_percent": float((hist["Close"].iloc[-1] - hist["Close"].iloc[0]) / hist["Close"].iloc[0] * 100)
                }
            }

            logger.info(f"✅ {symbol} 환율 히스토리 조회 성공: {len(hist)}개 데이터")
            return result

        except Exception as e:
            logger.error(f"❌ {symbol} 환율 히스토리 조회 실패: {e}")
            return None

    def get_all_major_rates(self) -> Dict[str, Dict]:
        """
        주요 환율 일괄 조회

        Returns:
            모든 주요 환율 정보 딕셔너리
        """
        results = {}

        for symbol in self.FOREX_SYMBOLS.keys():
            rate_data = self.get_current_rate(symbol)
            if rate_data:
                results[symbol] = rate_data

        logger.info(f"✅ 주요 환율 {len(results)}개 조회 완료")
        return results

    def get_krw_usd_trend(self, period: str = "3mo") -> Optional[Dict]:
        """
        원/달러 트렌드 분석

        Args:
            period: 분석 기간

        Returns:
            트렌드 분석 결과
        """
        try:
            hist_data = self.get_historical_rates("USDKRW", period=period)
            if not hist_data:
                return None

            stats = hist_data["statistics"]
            current = stats["current"]
            mean = stats["mean"]
            std = stats["std"]

            # 트렌드 판단
            if current > mean + std:
                trend = "강한 상승"
                signal = "달러 강세 (원화 약세)"
            elif current > mean:
                trend = "상승"
                signal = "달러 강세 경향"
            elif current < mean - std:
                trend = "강한 하락"
                signal = "달러 약세 (원화 강세)"
            elif current < mean:
                trend = "하락"
                signal = "달러 약세 경향"
            else:
                trend = "보합"
                signal = "균형 상태"

            result = {
                "symbol": "USDKRW",
                "period": period,
                "current_rate": current,
                "average_rate": mean,
                "volatility": std,
                "trend": trend,
                "signal": signal,
                "change_percent": stats["change_percent"],
                "risk_level": "높음" if std > mean * 0.05 else "보통" if std > mean * 0.02 else "낮음"
            }

            logger.info(f"✅ 원/달러 트렌드 분석 완료: {trend}")
            return result

        except Exception as e:
            logger.error(f"❌ 원/달러 트렌드 분석 실패: {e}")
            return None

    def get_dollar_index_analysis(self, period: str = "3mo") -> Optional[Dict]:
        """
        달러 인덱스 분석

        Args:
            period: 분석 기간

        Returns:
            달러 인덱스 분석 결과
        """
        try:
            hist_data = self.get_historical_rates("DXY", period=period)
            if not hist_data:
                return None

            stats = hist_data["statistics"]
            current = stats["current"]

            # 달러 강도 분석
            if current > 105:
                strength = "매우 강함"
                impact = "신흥국 통화 약세, 금 가격 하락 압력"
            elif current > 100:
                strength = "강함"
                impact = "달러 자산 선호, 수출 부담 증가"
            elif current > 95:
                strength = "보통"
                impact = "균형적 환경"
            elif current > 90:
                strength = "약함"
                impact = "신흥국 통화 강세, 금 가격 상승 가능"
            else:
                strength = "매우 약함"
                impact = "달러 자산 이탈, 원자재 가격 상승"

            result = {
                "symbol": "DXY",
                "period": period,
                "current_level": current,
                "strength": strength,
                "impact": impact,
                "change_percent": stats["change_percent"],
                "volatility": stats["std"],
                "trend": "상승" if stats["change_percent"] > 2 else "하락" if stats["change_percent"] < -2 else "보합"
            }

            logger.info(f"✅ 달러 인덱스 분석 완료: {strength}")
            return result

        except Exception as e:
            logger.error(f"❌ 달러 인덱스 분석 실패: {e}")
            return None


# 전역 인스턴스
_forex_collector = None


def get_forex_collector() -> ForexDataCollector:
    """ForexDataCollector 싱글톤 인스턴스 반환"""
    global _forex_collector
    if _forex_collector is None:
        _forex_collector = ForexDataCollector()
    return _forex_collector


# 편의 함수들
def get_krw_usd_rate() -> Optional[float]:
    """원/달러 환율 조회 (간편 함수)"""
    collector = get_forex_collector()
    data = collector.get_current_rate("USDKRW")
    return data["rate"] if data else None


def get_dollar_index() -> Optional[float]:
    """달러 인덱스 조회 (간편 함수)"""
    collector = get_forex_collector()
    data = collector.get_current_rate("DXY")
    return data["rate"] if data else None


def analyze_forex_market() -> Dict:
    """
    환율 시장 종합 분석

    Returns:
        환율 시장 분석 결과
    """
    collector = get_forex_collector()

    # 원/달러 분석
    krw_trend = collector.get_krw_usd_trend("3mo")

    # 달러 인덱스 분석
    dxy_analysis = collector.get_dollar_index_analysis("3mo")

    # 주요 환율 조회
    major_rates = collector.get_all_major_rates()

    return {
        "krw_usd_trend": krw_trend,
        "dollar_index": dxy_analysis,
        "major_rates": major_rates,
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)

    print("=" * 50)
    print("환율 데이터 수집 테스트")
    print("=" * 50)

    collector = get_forex_collector()

    # 1. 현재 원/달러 환율
    print("\n1. 현재 원/달러 환율:")
    krw_rate = collector.get_current_rate("USDKRW")
    if krw_rate:
        print(f"   환율: {krw_rate['rate']:.2f}")
        print(f"   변동: {krw_rate['change_percent']:.2f}%")

    # 2. 달러 인덱스
    print("\n2. 달러 인덱스:")
    dxy = collector.get_current_rate("DXY")
    if dxy:
        print(f"   지수: {dxy['rate']:.2f}")
        print(f"   변동: {dxy['change_percent']:.2f}%")

    # 3. 원/달러 트렌드
    print("\n3. 원/달러 3개월 트렌드:")
    trend = collector.get_krw_usd_trend("3mo")
    if trend:
        print(f"   트렌드: {trend['trend']}")
        print(f"   시그널: {trend['signal']}")
        print(f"   변동성: {trend['risk_level']}")

    # 4. 달러 인덱스 분석
    print("\n4. 달러 인덱스 분석:")
    dxy_analysis = collector.get_dollar_index_analysis("3mo")
    if dxy_analysis:
        print(f"   강도: {dxy_analysis['strength']}")
        print(f"   영향: {dxy_analysis['impact']}")

    # 5. 환율 시장 종합 분석
    print("\n5. 환율 시장 종합 분석:")
    market_analysis = analyze_forex_market()
    print(f"   주요 환율 {len(market_analysis['major_rates'])}개 조회 완료")
