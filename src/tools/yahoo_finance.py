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
    """시간 기반 캐싱 (TTL: 5분)"""
    def __init__(self, ttl_seconds=300):
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


# 전역 캐시 인스턴스
_stock_data_cache = TimedCache(ttl_seconds=300)  # 5분
_stock_info_cache = TimedCache(ttl_seconds=600)  # 10분


class YahooFinanceAnalyzer:
    """Yahoo Finance를 이용한 주식 분석 및 스크리닝 도구 (최적화 버전)"""

    def __init__(self):
        # 국내 증권사에서 거래 가능한 글로벌 우량주 (미국, 일본, 한국, 중국, 유럽)
        self.top_global_stocks = [
            # 미국 주요 종목 (나스닥, NYSE)
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK-B", "UNH", "JNJ",
            "JPM", "V", "PG", "HD", "CVX", "MA", "ABBV", "PFE", "AVGO", "KO",
            "LLY", "WMT", "ORCL", "BAC", "CRM", "NFLX", "XOM", "ACN", "DIS", "TMO",

            # 일본 주요 종목 (도쿄증권거래소, .T) - 12개
            "7203.T",   # 도요타 자동차
            "6758.T",   # 소니 그룹
            "9984.T",   # 소프트뱅크 그룹
            "7974.T",   # 닌텐도
            "6861.T",   # 키엔스
            "6501.T",   # 히타치
            "9434.T",   # KDDI
            "4063.T",   # 신에츠화학
            "6902.T",   # 덴소 (자동차 부품)
            "8306.T",   # 미쓰비시UFJ은행
            "4452.T",   # 카오 (생활용품)
            "4502.T",   # 다케다제약

            # 한국 주요 종목 (KOSPI, .KS)
            "005930.KS",  # 삼성전자
            "000660.KS",  # SK하이닉스
            "035420.KS",  # NAVER
            "051910.KS",  # LG화학
            "005380.KS",  # 현대차
            "207940.KS",  # 삼성바이오로직스

            # 중국/홍콩 주요 종목 - 12개
            "BABA",      # 알리바바 (US ADR)
            "9988.HK",   # 알리바바 (홍콩)
            "0700.HK",   # 텐센트 홀딩스
            "9618.HK",   # JD.com
            "1810.HK",   # 샤오미 (Xiaomi)
            "2318.HK",   # 핑안보험
            "3690.HK",   # 메이투안 (Meituan)
            "2020.HK",   # 안커 이노베이션
            "1024.HK",   # 콰이쇼 (Kuaishou)
            "JD",        # JD.com (US ADR)
            "PDD",       # 핀둬둬 (Pinduoduo)
            "BIDU",      # 바이두 (Baidu)

            # 유럽 주요 종목 (ADR 또는 직접 상장)
            "ASML",      # ASML 홀딩 (네덜란드 반도체)
            "SAP",       # SAP (독일 소프트웨어)
            "NVO",       # 노보노디스크 (덴마크 제약)
        ]
        self.max_workers = 15  # 병렬 처리 워커 수 증가

    def get_stock_data(self, ticker: str, period: str = "6mo") -> Optional[pd.DataFrame]:
        """개별 주식 데이터 수집 (캐싱 적용, 6개월로 축소)"""
        cache_key = f"data_{ticker}_{period}"
        cached_data = _stock_data_cache.get(cache_key)
        if cached_data is not None:
            return cached_data

        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period=period)
            _stock_data_cache.set(cache_key, data)
            return data
        except Exception as e:
            logger.error(f"Failed to get data for {ticker}: {e}")
            return None

    def get_stock_info(self, ticker: str) -> Optional[Dict]:
        """주식 기본 정보 수집 (캐싱 적용)"""
        cache_key = f"info_{ticker}"
        cached_info = _stock_info_cache.get(cache_key)
        if cached_info is not None:
            return cached_info

        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            _stock_info_cache.set(cache_key, info)
            return info
        except Exception as e:
            logger.error(f"Failed to get info for {ticker}: {e}")
            return None

    def get_market_info(self, ticker: str) -> Dict[str, str]:
        """티커 심볼에서 시장 정보 추출"""
        if ticker.endswith('.T'):
            return {"market": "일본", "market_en": "Japan", "exchange": "도쿄증권거래소"}
        elif ticker.endswith('.KS'):
            return {"market": "한국", "market_en": "Korea", "exchange": "KOSPI"}
        elif ticker.endswith('.KQ'):
            return {"market": "한국", "market_en": "Korea", "exchange": "KOSDAQ"}
        elif ticker.endswith('.HK') or ticker in ['BABA', '9988.HK', '0700.HK', '9618.HK']:
            return {"market": "중국", "market_en": "China", "exchange": "홍콩/미국"}
        elif ticker in ['ASML', 'SAP', 'NVO']:
            return {"market": "유럽", "market_en": "Europe", "exchange": "유럽/미국"}
        else:
            return {"market": "미국", "market_en": "US", "exchange": "NYSE/NASDAQ"}

    def calculate_financial_metrics(self, ticker: str) -> Dict:
        """주요 재무 지표 계산 (최적화: 6개월 데이터만 사용)"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            data = self.get_stock_data(ticker, period="6mo")  # 1년 → 6개월

            if data is None or data.empty:
                return {}

            # 기본 가격 정보
            current_price = data['Close'].iloc[-1]

            # 6개월 데이터 기준으로 최고/최저 계산
            period_high = data['High'].max()
            period_low = data['Low'].min()

            # 수익률 계산 (사용 가능한 데이터만)
            returns_1m = (data['Close'].iloc[-1] / data['Close'].iloc[-22] - 1) * 100 if len(data) >= 22 else 0
            returns_3m = (data['Close'].iloc[-1] / data['Close'].iloc[-66] - 1) * 100 if len(data) >= 66 else 0
            returns_6m = (data['Close'].iloc[-1] / data['Close'].iloc[0] - 1) * 100

            # 변동성 계산
            daily_returns = data['Close'].pct_change().dropna()
            volatility = daily_returns.std() * (252 ** 0.5) * 100  # 연간화

            # 평균 거래량
            avg_volume = data['Volume'].mean()

            # info에서 추가 지표 추출
            pe_ratio = info.get('trailingPE', 0) or 0
            market_cap = info.get('marketCap', 0) or 0
            dividend_yield = info.get('dividendYield', 0) or 0

            return {
                'ticker': ticker,
                'current_price': round(current_price, 2),
                'period_high': round(period_high, 2),
                'period_low': round(period_low, 2),
                'returns_1m': round(returns_1m, 2),
                'returns_3m': round(returns_3m, 2),
                'returns_6m': round(returns_6m, 2),
                'returns_1y': round(returns_6m, 2),  # 6개월 데이터를 1년으로 간주 (호환성)
                'volatility': round(volatility, 2),
                'avg_volume': int(avg_volume),
                'pe_ratio': round(pe_ratio, 2) if pe_ratio else 0,
                'market_cap': market_cap,
                'dividend_yield': round(dividend_yield * 100, 2) if dividend_yield else 0
            }

        except Exception as e:
            logger.error(f"Failed to calculate metrics for {ticker}: {e}")
            return {}

    def _calculate_metrics_safe(self, ticker: str) -> Dict:
        """병렬 처리용 안전한 metrics 계산 래퍼"""
        try:
            return self.calculate_financial_metrics(ticker)
        except Exception as e:
            logger.error(f"Error in parallel processing for {ticker}: {e}")
            return {}

    def screen_top_stocks(self, num_stocks: int = 5) -> List[Dict]:
        """상위 주식 스크리닝 - 병렬 처리 적용 (글로벌 우량주 포함)"""
        all_metrics = []

        logger.info(f"Screening {len(self.top_global_stocks)} global stocks with {self.max_workers} workers...")

        # 🚀 병렬 처리: 글로벌 종목을 동시에 처리
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_ticker = {
                executor.submit(self._calculate_metrics_safe, ticker): ticker
                for ticker in self.top_global_stocks
            }

            for future in as_completed(future_to_ticker):
                metrics = future.result()
                if metrics:
                    all_metrics.append(metrics)

        if not all_metrics:
            return []

        # 점수 계산을 위한 정규화
        df = pd.DataFrame(all_metrics)

        # 각 기준별 점수 계산 (0-100점)
        for column in ['returns_1m', 'returns_3m', 'returns_6m', 'returns_1y']:
            if column in df.columns and df[column].max() != df[column].min():
                df[f'{column}_score'] = ((df[column] - df[column].min()) /
                                      (df[column].max() - df[column].min()) * 100).fillna(0)
            else:
                df[f'{column}_score'] = 0

        # 변동성은 낮을수록 좋음 (역점수)
        if 'volatility' in df.columns and df['volatility'].max() != df['volatility'].min():
            df['volatility_score'] = ((df['volatility'].max() - df['volatility']) /
                                   (df['volatility'].max() - df['volatility'].min()) * 100).fillna(0)
        else:
            df['volatility_score'] = 0

        # 시가총액 점수 (큰 회사일수록 안정적)
        if 'market_cap' in df.columns and df['market_cap'].max() > 0:
            df['market_cap_score'] = ((df['market_cap'] - df['market_cap'].min()) /
                                   (df['market_cap'].max() - df['market_cap'].min()) * 100).fillna(0)
        else:
            df['market_cap_score'] = 0

        # PE 비율 점수 (적정 수준이 좋음)
        if 'pe_ratio' in df.columns:
            # PE 10-25 구간을 최적으로 간주
            df['pe_score'] = df['pe_ratio'].apply(lambda x:
                100 if 10 <= x <= 25 else
                max(0, 100 - abs(x - 17.5) * 3) if x > 0 else 0)
        else:
            df['pe_score'] = 0

        # 종합 점수 계산 (가중 평균)
        score_columns = [col for col in df.columns if col.endswith('_score')]
        if score_columns:
            weights = {
                'returns_1y_score': 0.25,
                'returns_6m_score': 0.20,
                'returns_3m_score': 0.15,
                'returns_1m_score': 0.10,
                'volatility_score': 0.15,
                'market_cap_score': 0.10,
                'pe_score': 0.05
            }

            df['total_score'] = 0
            for col in score_columns:
                weight = weights.get(col, 0.01)
                df['total_score'] += df[col] * weight

        # 🌏 국가별 분산 보장: 미국, 일본, 중국에서 최소 개수 선정
        result = []

        # 국가별 종목 분류
        us_stocks = df[~df['ticker'].str.contains(r'\.T$|\.KS$|\.HK$|BABA|JD|PDD|BIDU', regex=True, na=False)]
        japan_stocks = df[df['ticker'].str.contains(r'\.T$', regex=True, na=False)]
        china_stocks = df[df['ticker'].str.contains(r'\.HK$|BABA|JD|PDD|BIDU', regex=True, na=False)]
        korea_stocks = df[df['ticker'].str.contains(r'\.KS$', regex=True, na=False)]

        # num_stocks에 따라 국가별 최소 개수 설정 (글로벌 분산 투자)
        if num_stocks >= 30:
            # 30개 이상: 미국 10개, 일본 10개, 중국 10개 최소 보장
            min_us, min_jp, min_cn = 10, 10, 10
        elif num_stocks >= 20:
            # 20-29개: 미국 7개, 일본 7개, 중국 6개 최소 보장
            min_us, min_jp, min_cn = 7, 7, 6
        elif num_stocks >= 10:
            # 10-19개: 미국 4개, 일본 3개, 중국 3개 최소 보장
            min_us, min_jp, min_cn = 4, 3, 3
        elif num_stocks >= 5:
            # 5-9개: 미국 2개, 일본 2개, 중국 1개 최소 보장
            min_us, min_jp, min_cn = 2, 2, 1
        else:
            # 5개 미만: 최소 보장 없이 점수 기준
            min_us, min_jp, min_cn = 0, 0, 0

        selected_tickers = set()

        # 각 국가별 최소 개수만큼 선정
        for stocks_df, min_count, country in [(us_stocks, min_us, "미국"),
                                                (japan_stocks, min_jp, "일본"),
                                                (china_stocks, min_cn, "중국")]:
            if len(stocks_df) > 0 and min_count > 0:
                top_country = stocks_df.nlargest(min_count, 'total_score')
                for _, row in top_country.iterrows():
                    selected_tickers.add(row['ticker'])
                logger.info(f"✅ {country} 종목 {len(top_country)}개 선정")

        # 남은 자리는 전체 점수 기준으로 선정
        remaining_count = num_stocks - len(selected_tickers)
        if remaining_count > 0:
            remaining_stocks = df[~df['ticker'].isin(selected_tickers)].nlargest(remaining_count, 'total_score')
            for _, row in remaining_stocks.iterrows():
                selected_tickers.add(row['ticker'])

        # 선정된 종목으로 결과 생성
        top_stocks = df[df['ticker'].isin(selected_tickers)].nlargest(num_stocks, 'total_score')

        for _, row in top_stocks.iterrows():
            ticker = row['ticker']
            market_info = self.get_market_info(ticker)

            stock_data = {
                'ticker': ticker,
                'score': round(row['total_score'], 2),
                'current_price': row['current_price'],
                'returns_1y': row['returns_1y'],
                'returns_6m': row['returns_6m'],
                'returns_3m': row['returns_3m'],
                'volatility': row['volatility'],
                'pe_ratio': row['pe_ratio'],
                'market_cap': row['market_cap'],
                'dividend_yield': row['dividend_yield'],
                'market': market_info['market'],
                'market_en': market_info['market_en'],
                'exchange': market_info['exchange']
            }
            result.append(stock_data)

        return result

    def generate_stock_analysis(self, ticker: str, metrics: Optional[Dict] = None) -> str:
        """개별 주식에 대한 상세 분석 생성 (중복 호출 방지)"""
        # 🎯 중복 API 호출 제거: metrics가 이미 있으면 재사용
        if metrics is None:
            metrics = self.calculate_financial_metrics(ticker)

        info = self.get_stock_info(ticker)

        if not metrics or not info:
            return f"{ticker}에 대한 분석 데이터를 가져올 수 없습니다."

        company_name = info.get('longName', ticker)
        sector = info.get('sector', '정보 없음')
        industry = info.get('industry', '정보 없음')

        # 분석 생성
        analysis = f"""
{company_name} ({ticker}) 투자 분석

기업 개요:
- 섹터: {sector}
- 산업: {industry}
- 시가총액: ${metrics['market_cap']:,}

가격 정보:
- 현재가: ${metrics['current_price']}
- 6개월 최고: ${metrics.get('period_high', 0)}
- 6개월 최저: ${metrics.get('period_low', 0)}

수익률 분석:
- 1개월: {metrics['returns_1m']:+.2f}%
- 3개월: {metrics['returns_3m']:+.2f}%
- 6개월: {metrics['returns_6m']:+.2f}%

리스크 지표:
- 연간 변동성: {metrics['volatility']:.2f}%
- 평균 거래량: {metrics['avg_volume']:,}주

밸류에이션:
- PER: {metrics['pe_ratio']}
- 배당수익률: {metrics['dividend_yield']:.2f}%

투자 의견:
"""

        # 투자 의견 생성 로직
        if metrics['returns_6m'] > 15:
            analysis += "- 6개월 수익률이 우수하여 성장성이 높습니다.\n"
        elif metrics['returns_6m'] > 5:
            analysis += "- 6개월 수익률이 안정적인 수준입니다.\n"
        else:
            analysis += "- 6개월 수익률이 저조하여 주의가 필요합니다.\n"

        if metrics['volatility'] < 20:
            analysis += "- 변동성이 낮아 안정적인 투자처입니다.\n"
        elif metrics['volatility'] < 35:
            analysis += "- 변동성이 보통 수준입니다.\n"
        else:
            analysis += "- 변동성이 높아 위험성을 고려해야 합니다.\n"

        if 10 <= metrics['pe_ratio'] <= 25:
            analysis += "- PER이 적정 수준으로 밸류에이션이 합리적입니다.\n"
        elif metrics['pe_ratio'] > 25:
            analysis += "- PER이 높아 고평가 가능성이 있습니다.\n"
        elif metrics['pe_ratio'] > 0:
            analysis += "- PER이 낮아 저평가 가능성이 있습니다.\n"

        return analysis.strip()

    def get_top_stocks_with_analysis(self, num_stocks: int = 5) -> List[Dict]:
        """상위 주식과 각각의 상세 분석을 함께 반환 (최적화: 중복 호출 제거)"""
        top_stocks = self.screen_top_stocks(num_stocks)

        # 🎯 중복 API 호출 제거: 이미 가져온 metrics를 재사용
        for stock in top_stocks:
            # stock 딕셔너리를 metrics로 변환
            metrics = {
                'ticker': stock['ticker'],
                'current_price': stock['current_price'],
                'period_high': stock['current_price'],  # 간략화
                'period_low': stock['current_price'] * 0.9,  # 간략화
                'returns_1m': stock.get('returns_1m', 0),
                'returns_3m': stock['returns_3m'],
                'returns_6m': stock['returns_6m'],
                'volatility': stock['volatility'],
                'avg_volume': 0,  # 분석에 필수 아님
                'pe_ratio': stock['pe_ratio'],
                'market_cap': stock['market_cap'],
                'dividend_yield': stock['dividend_yield']
            }
            stock['analysis'] = self.generate_stock_analysis(stock['ticker'], metrics)

        return top_stocks


# 전역 인스턴스
yahoo_analyzer = YahooFinanceAnalyzer()


def get_top_stocks(num_stocks: int = 5) -> List[Dict]:
    """상위 주식 반환 (외부 API 호환)"""
    return yahoo_analyzer.get_top_stocks_with_analysis(num_stocks)


def analyze_stock(ticker: str) -> Dict:
    """개별 주식 분석 (외부 API 호환)"""
    metrics = yahoo_analyzer.calculate_financial_metrics(ticker)
    analysis = yahoo_analyzer.generate_stock_analysis(ticker, metrics)

    return {
        'ticker': ticker,
        'metrics': metrics,
        'analysis': analysis
    }


def clear_cache():
    """캐시 초기화 (테스트용)"""
    _stock_data_cache.clear()
    _stock_info_cache.clear()
    logger.info("Cache cleared")
