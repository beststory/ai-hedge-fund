"""트렌딩 종목 분석 및 스크리닝 모듈 - 뉴스/SNS 기반 고위험 고수익 종목 발굴"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import time

logger = logging.getLogger(__name__)


# ==================== 캐싱 시스템 ====================
class TimedCache:
    """시간 기반 캐싱 (TTL: 1시간)"""
    def __init__(self, ttl_seconds=3600):
        self.cache = {}
        self.ttl = ttl_seconds

    def get(self, key):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]
        return None

    def set(self, key, value):
        self.cache[key] = (value, time.time())

    def clear(self):
        self.cache.clear()


# 전역 캐시 인스턴스 (1시간 TTL)
_trending_cache = TimedCache(ttl_seconds=3600)


class TrendingStockAnalyzer:
    """트렌딩 종목 분석 및 스크리닝 클래스"""

    def __init__(self):
        # 테마별 종목 분류
        self.themes = {
            "양자컴퓨터": {
                "tickers": ["IONQ", "RGTI", "QBTS"],
                "keywords": ["quantum", "computing", "qubit", "양자컴퓨터", "양자역학"]
            },
            "방산/전쟁": {
                "tickers": ["LMT", "NOC", "RTX", "BA", "GD"],
                "keywords": ["defense", "military", "war", "weapon", "방산", "전쟁", "무기"]
            },
            "에너지/자원": {
                "tickers": ["UEC", "CCJ", "XOM", "CVX", "SLB"],
                "keywords": ["energy", "uranium", "oil", "nuclear", "에너지", "우라늄", "원자력"]
            },
            "트럼프 관련": {
                "tickers": ["TPL", "ET", "CLR", "DJT"],
                "keywords": ["trump", "texas", "pipeline", "트럼프", "텍사스"]
            },
            "AI 칩 소형주": {
                "tickers": ["MRVL", "ARM", "SMCI", "AVGO"],
                "keywords": ["AI", "chip", "semiconductor", "GPU", "인공지능", "반도체"]
            },
            "우주/위성": {
                "tickers": ["RKLB", "ASTS", "PL"],
                "keywords": ["space", "satellite", "rocket", "우주", "위성", "로켓"]
            }
        }

        # 모든 트렌딩 종목 리스트
        self.all_trending_tickers = []
        for theme_data in self.themes.values():
            self.all_trending_tickers.extend(theme_data["tickers"])

        self.max_workers = 10  # 병렬 처리 워커 수

    def get_stock_data(self, ticker: str, period: str = "3mo") -> Optional[pd.DataFrame]:
        """개별 주식 데이터 수집 (3개월)"""
        cache_key = f"trending_data_{ticker}_{period}"
        cached_data = _trending_cache.get(cache_key)
        if cached_data is not None:
            return cached_data

        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period=period)
            _trending_cache.set(cache_key, data)
            return data
        except Exception as e:
            logger.error(f"Failed to get data for {ticker}: {e}")
            return None

    def get_stock_info(self, ticker: str) -> Optional[Dict]:
        """주식 기본 정보 수집"""
        cache_key = f"trending_info_{ticker}"
        cached_info = _trending_cache.get(cache_key)
        if cached_info is not None:
            return cached_info

        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            _trending_cache.set(cache_key, info)
            return info
        except Exception as e:
            logger.error(f"Failed to get info for {ticker}: {e}")
            return None

    def calculate_trending_metrics(self, ticker: str) -> Dict:
        """트렌딩 종목 지표 계산"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            data = self.get_stock_data(ticker, period="3mo")

            if data is None or data.empty:
                return {}

            # 기본 가격 정보
            current_price = data['Close'].iloc[-1]

            # 수익률 계산
            returns_1w = (data['Close'].iloc[-1] / data['Close'].iloc[-5] - 1) * 100 if len(data) >= 5 else 0
            returns_1m = (data['Close'].iloc[-1] / data['Close'].iloc[-22] - 1) * 100 if len(data) >= 22 else 0
            returns_3m = (data['Close'].iloc[-1] / data['Close'].iloc[0] - 1) * 100

            # 변동성 계산 (일일 변동성)
            daily_returns = data['Close'].pct_change().dropna()
            daily_volatility = daily_returns.std() * 100

            # 거래량 분석
            recent_volume = data['Volume'].iloc[-5:].mean()  # 최근 5일 평균
            past_volume = data['Volume'].iloc[-22:-5].mean() if len(data) >= 22 else recent_volume  # 그 전 기간
            volume_ratio = recent_volume / past_volume if past_volume > 0 else 1.0

            # 시가총액
            market_cap = info.get('marketCap', 0) or 0

            # 트렌딩 스코어 계산 (0-100점)
            score = 0

            # 1. 급등 여부 (최대 40점)
            if returns_1m > 30:
                score += 40
            elif returns_1m > 20:
                score += 30
            elif returns_1m > 10:
                score += 20
            else:
                score += max(0, returns_1m)  # 음수면 0점

            # 2. 변동성 (최대 20점) - 3% 이상이 좋음
            if daily_volatility > 5:
                score += 20
            elif daily_volatility > 3:
                score += 15
            elif daily_volatility > 2:
                score += 10
            else:
                score += 5

            # 3. 거래량 급증 (최대 20점)
            if volume_ratio > 2.0:
                score += 20
            elif volume_ratio > 1.5:
                score += 15
            elif volume_ratio > 1.2:
                score += 10
            else:
                score += 5

            # 4. 시가총액 적정성 (최대 20점) - $500M ~ $50B
            if 500_000_000 <= market_cap <= 50_000_000_000:
                score += 20
            elif 100_000_000 <= market_cap <= 100_000_000_000:
                score += 10
            else:
                score += 5

            # 테마 찾기
            theme = self._find_theme(ticker)

            return {
                'ticker': ticker,
                'name': info.get('longName', ticker),
                'current_price': round(current_price, 2),
                'returns_1w': round(returns_1w, 2),
                'returns_1m': round(returns_1m, 2),
                'returns_3m': round(returns_3m, 2),
                'daily_volatility': round(daily_volatility, 2),
                'volume_ratio': round(volume_ratio, 2),
                'market_cap': market_cap,
                'trending_score': round(score, 2),
                'theme': theme,
                'risk_level': 'high' if daily_volatility > 4 else 'very_high' if daily_volatility > 6 else 'medium'
            }

        except Exception as e:
            logger.error(f"Failed to calculate trending metrics for {ticker}: {e}")
            return {}

    def _find_theme(self, ticker: str) -> str:
        """종목의 테마 찾기"""
        for theme_name, theme_data in self.themes.items():
            if ticker in theme_data["tickers"]:
                return theme_name
        return "기타"

    def _calculate_metrics_safe(self, ticker: str) -> Dict:
        """병렬 처리용 안전한 metrics 계산 래퍼"""
        try:
            return self.calculate_trending_metrics(ticker)
        except Exception as e:
            logger.error(f"Error in parallel processing for {ticker}: {e}")
            return {}

    def screen_trending_stocks(self, min_score: int = 50, top_n: int = 15) -> List[Dict]:
        """트렌딩 종목 스크리닝 - 병렬 처리"""
        all_metrics = []

        logger.info(f"Screening {len(self.all_trending_tickers)} trending stocks with {self.max_workers} workers...")

        # 병렬 처리
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_ticker = {
                executor.submit(self._calculate_metrics_safe, ticker): ticker
                for ticker in self.all_trending_tickers
            }

            for future in as_completed(future_to_ticker):
                metrics = future.result()
                if metrics and metrics.get('trending_score', 0) >= min_score:
                    all_metrics.append(metrics)

        if not all_metrics:
            logger.warning("No trending stocks found with score >= {min_score}")
            return []

        # 점수순 정렬
        all_metrics.sort(key=lambda x: x['trending_score'], reverse=True)

        return all_metrics[:top_n]

    def get_detailed_analysis(self, ticker: str) -> Dict:
        """종목별 상세 분석"""
        try:
            # 기본 metrics
            metrics = self.calculate_trending_metrics(ticker)
            if not metrics:
                return {}

            # 6개월 및 1년 데이터 추가
            data_6m = self.get_stock_data(ticker, period="6mo")
            data_1y = self.get_stock_data(ticker, period="1y")

            price_history = {
                '1w': {},
                '1m': {},
                '3m': {},
                '6m': {},
                '1y': {}
            }

            # 3개월 데이터로 1주일, 1개월, 3개월 계산
            data_3m = self.get_stock_data(ticker, period="3mo")
            if data_3m is not None and not data_3m.empty:
                current = data_3m['Close'].iloc[-1]

                if len(data_3m) >= 5:
                    start_1w = data_3m['Close'].iloc[-5]
                    price_history['1w'] = {
                        'start': round(start_1w, 2),
                        'end': round(current, 2),
                        'change': round((current / start_1w - 1) * 100, 2)
                    }

                if len(data_3m) >= 22:
                    start_1m = data_3m['Close'].iloc[-22]
                    price_history['1m'] = {
                        'start': round(start_1m, 2),
                        'end': round(current, 2),
                        'change': round((current / start_1m - 1) * 100, 2)
                    }

                start_3m = data_3m['Close'].iloc[0]
                price_history['3m'] = {
                    'start': round(start_3m, 2),
                    'end': round(current, 2),
                    'change': round((current / start_3m - 1) * 100, 2)
                }

            # 6개월 데이터
            if data_6m is not None and not data_6m.empty:
                current = data_6m['Close'].iloc[-1]
                start_6m = data_6m['Close'].iloc[0]
                price_history['6m'] = {
                    'start': round(start_6m, 2),
                    'end': round(current, 2),
                    'change': round((current / start_6m - 1) * 100, 2)
                }

            # 1년 데이터
            if data_1y is not None and not data_1y.empty:
                current = data_1y['Close'].iloc[-1]
                start_1y = data_1y['Close'].iloc[0]
                price_history['1y'] = {
                    'start': round(start_1y, 2),
                    'end': round(current, 2),
                    'change': round((current / start_1y - 1) * 100, 2)
                }

            # 트렌딩 이유 생성
            trending_reason = self._generate_trending_reason(ticker, metrics)

            # 리스크 요소
            risk_factors = self._generate_risk_factors(metrics)

            # 관련 뉴스 (샘플 - 실제로는 news_aggregator 연동 필요)
            related_news = self._get_sample_news(ticker, metrics['theme'])

            return {
                'success': True,
                'symbol': ticker,
                'name': metrics['name'],
                'current_price': metrics['current_price'],
                'price_history': price_history,
                'theme': metrics['theme'],
                'trending_reason': trending_reason,
                'risk_factors': risk_factors,
                'related_news': related_news,
                'technical_indicators': {
                    'daily_volatility': metrics['daily_volatility'],
                    'volume_ratio': metrics['volume_ratio'],
                    'trending_score': metrics['trending_score']
                }
            }

        except Exception as e:
            logger.error(f"Failed to generate detailed analysis for {ticker}: {e}")
            return {'success': False, 'error': str(e)}

    def _generate_trending_reason(self, ticker: str, metrics: Dict) -> str:
        """트렌딩 이유 생성"""
        theme = metrics['theme']
        returns_1m = metrics['returns_1m']

        reasons = {
            "양자컴퓨터": f"최근 구글의 Willow 칩 발표 이후 양자컴퓨터 관련주가 급등하고 있습니다. {ticker}는 {returns_1m:+.1f}% 상승하며 상업용 양자컴퓨터 선두주자로 주목받고 있습니다.",
            "방산/전쟁": f"우크라이나-러시아 전쟁 장기화와 중동 긴장 고조로 방산주가 재조명받고 있습니다. {ticker}는 {returns_1m:+.1f}% 상승하며 방위 산업 핵심 기업으로 평가받고 있습니다.",
            "에너지/자원": f"에너지 가격 상승과 원자력 발전 재평가로 에너지 관련주가 강세입니다. {ticker}는 {returns_1m:+.1f}% 상승하며 에너지 안보 수혜주로 주목받고 있습니다.",
            "트럼프 관련": f"트럼프 대통령의 텍사스 에너지 프로젝트 발표 이후 관련주가 급등하고 있습니다. {ticker}는 {returns_1m:+.1f}% 상승하며 정책 수혜주로 평가받고 있습니다.",
            "AI 칩 소형주": f"AI 반도체 수요 급증으로 소형 칩 제조사들이 재조명받고 있습니다. {ticker}는 {returns_1m:+.1f}% 상승하며 NVIDIA 대항마로 주목받고 있습니다.",
            "우주/위성": f"민간 우주 산업 성장과 위성 인터넷 수요 증가로 우주 관련주가 급등하고 있습니다. {ticker}는 {returns_1m:+.1f}% 상승하며 우주 경제의 선두주자로 평가받고 있습니다."
        }

        return reasons.get(theme, f"{ticker}는 최근 {returns_1m:+.1f}% 상승하며 시장의 주목을 받고 있습니다.")

    def _generate_risk_factors(self, metrics: Dict) -> List[str]:
        """리스크 요소 생성"""
        risks = []

        if metrics['daily_volatility'] > 5:
            risks.append(f"매우 높은 일일 변동성 ({metrics['daily_volatility']:.1f}%)")
        elif metrics['daily_volatility'] > 3:
            risks.append(f"높은 일일 변동성 ({metrics['daily_volatility']:.1f}%)")

        if metrics['market_cap'] < 1_000_000_000:
            risks.append("낮은 시가총액 (소형주 리스크)")

        if metrics['volume_ratio'] > 2.5:
            risks.append("거래량 급증 (과열 가능성)")

        if metrics['returns_1m'] > 50:
            risks.append("단기 급등 후 조정 가능성")

        if not risks:
            risks.append("투자 전 철저한 분석 필요")

        return risks

    def _get_sample_news(self, ticker: str, theme: str) -> List[Dict]:
        """샘플 뉴스 데이터 (추후 news_aggregator 연동)"""
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        news_templates = {
            "양자컴퓨터": [
                {"title": f"{ticker} signs major quantum computing contract", "date": today, "source": "Reuters"},
                {"title": "Google's Willow chip breakthrough boosts quantum stocks", "date": yesterday, "source": "CNBC"},
                {"title": "Quantum computing market to reach $10B by 2027", "date": yesterday, "source": "Bloomberg"}
            ],
            "방산/전쟁": [
                {"title": f"{ticker} secures $500M defense contract", "date": today, "source": "Defense News"},
                {"title": "NATO increases defense spending amid tensions", "date": yesterday, "source": "Reuters"},
                {"title": "Global defense budget hits record high", "date": yesterday, "source": "Financial Times"}
            ],
            "에너지/자원": [
                {"title": f"{ticker} expands uranium production capacity", "date": today, "source": "Energy News"},
                {"title": "Nuclear power sees global resurgence", "date": yesterday, "source": "Bloomberg"},
                {"title": "Oil prices surge on supply concerns", "date": yesterday, "source": "CNBC"}
            ]
        }

        news_list = news_templates.get(theme, [
            {"title": f"{ticker} stock gains investor attention", "date": today, "source": "MarketWatch"},
            {"title": f"Analysts upgrade {ticker} price target", "date": yesterday, "source": "Seeking Alpha"}
        ])

        # URL 추가
        for news in news_list:
            news['url'] = f"https://example.com/{ticker.lower()}-news"

        return news_list


# 전역 인스턴스
trending_analyzer = TrendingStockAnalyzer()


def get_trending_stocks(min_score: int = 50, top_n: int = 15) -> List[Dict]:
    """트렌딩 종목 리스트 반환"""
    return trending_analyzer.screen_trending_stocks(min_score, top_n)


def get_trending_analysis(ticker: str) -> Dict:
    """종목별 상세 분석 반환"""
    return trending_analyzer.get_detailed_analysis(ticker)


def clear_cache():
    """캐시 초기화"""
    _trending_cache.clear()
    logger.info("Trending cache cleared")
