"""한국 주식 시장 데이터 처리 모듈"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import requests
from bs4 import BeautifulSoup
import json

class KoreanStockAnalyzer:
    """한국 주식 분석 클래스"""
    
    # 주요 KOSPI 종목
    KOSPI_TICKERS = {
        '005930.KS': '삼성전자',
        '000660.KS': 'SK하이닉스', 
        '207940.KS': '삼성바이오로직스',
        '005380.KS': '현대차',
        '000270.KS': '기아',
        '051910.KS': 'LG화학',
        '006400.KS': '삼성SDI',
        '035720.KS': '카카오',
        '035420.KS': 'NAVER',
        '068270.KS': '셀트리온',
        '105560.KS': 'KB금융',
        '055550.KS': '신한지주',
        '086790.KS': '하나금융지주',
        '003550.KS': 'LG',
        '034730.KS': 'SK',
        '015760.KS': '한국전력',
        '017670.KS': 'SK텔레콤',
        '030200.KS': 'KT',
        '032830.KS': '삼성생명',
        '033780.KS': 'KT&G'
    }
    
    # 주요 KOSDAQ 종목
    KOSDAQ_TICKERS = {
        '247540.KQ': '에코프로비엠',
        '086520.KQ': '에코프로',
        '328130.KQ': '루닛',
        '196170.KQ': '알테오젠',
        '145020.KQ': '휴젤',
        '112040.KQ': '위메이드',
        '293490.KQ': '카카오게임즈',
        '357780.KQ': 'BNK투자증권',
        '091990.KQ': '셀트리온헬스케어',
        '036570.KQ': '엔씨소프트'
    }
    
    def __init__(self):
        """초기화"""
        self.all_tickers = {**self.KOSPI_TICKERS, **self.KOSDAQ_TICKERS}
        
    def get_stock_data(self, ticker: str, period: str = "1mo") -> Dict[str, Any]:
        """
        한국 주식 데이터 가져오기
        
        Args:
            ticker: 종목 코드 (예: '005930.KS')
            period: 기간 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y)
        
        Returns:
            주식 데이터 딕셔너리
        """
        try:
            stock = yf.Ticker(ticker)
            
            # 기본 정보
            info = stock.info
            
            # 과거 데이터
            hist = stock.history(period=period)
            
            # 현재가 및 변동
            current_price = hist['Close'].iloc[-1] if len(hist) > 0 else 0
            prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            change = current_price - prev_close
            change_pct = (change / prev_close) * 100 if prev_close > 0 else 0
            
            # 기술적 지표 계산
            technical = self._calculate_technical_indicators(hist)
            
            return {
                'ticker': ticker,
                'name': self.all_tickers.get(ticker, info.get('longName', ticker)),
                'current_price': current_price,
                'change': change,
                'change_percent': change_pct,
                'volume': int(hist['Volume'].iloc[-1]) if len(hist) > 0 else 0,
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'dividend_yield': info.get('dividendYield', 0),
                'beta': info.get('beta', 0),
                'high_52w': info.get('fiftyTwoWeekHigh', 0),
                'low_52w': info.get('fiftyTwoWeekLow', 0),
                'technical_indicators': technical,
                'historical_data': hist.to_dict()
            }
            
        except Exception as e:
            print(f"주식 데이터 가져오기 실패 {ticker}: {e}")
            return {
                'ticker': ticker,
                'name': self.all_tickers.get(ticker, ticker),
                'error': str(e)
            }
    
    def _calculate_technical_indicators(self, hist: pd.DataFrame) -> Dict[str, float]:
        """
        기술적 지표 계산
        
        Args:
            hist: 과거 가격 데이터
        
        Returns:
            기술적 지표 딕셔너리
        """
        if len(hist) < 20:
            return {}
        
        close = hist['Close']
        
        # 이동평균
        ma20 = close.rolling(window=20).mean().iloc[-1]
        ma60 = close.rolling(window=60).mean().iloc[-1] if len(close) >= 60 else ma20
        ma120 = close.rolling(window=120).mean().iloc[-1] if len(close) >= 120 else ma60
        
        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # 볼린저 밴드
        std20 = close.rolling(window=20).std().iloc[-1]
        upper_band = ma20 + (std20 * 2)
        lower_band = ma20 - (std20 * 2)
        
        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        macd_histogram = (macd - signal).iloc[-1]
        
        return {
            'ma20': float(ma20),
            'ma60': float(ma60),
            'ma120': float(ma120),
            'rsi': float(rsi),
            'upper_band': float(upper_band),
            'lower_band': float(lower_band),
            'macd': float(macd.iloc[-1]),
            'macd_signal': float(signal.iloc[-1]),
            'macd_histogram': float(macd_histogram)
        }
    
    def get_top_korean_stocks(self, market: str = "all", limit: int = 10) -> List[Dict[str, Any]]:
        """
        상위 한국 주식 가져오기
        
        Args:
            market: 시장 구분 (kospi, kosdaq, all)
            limit: 가져올 종목 수
        
        Returns:
            상위 종목 리스트
        """
        if market == "kospi":
            tickers = list(self.KOSPI_TICKERS.keys())[:limit]
        elif market == "kosdaq":
            tickers = list(self.KOSDAQ_TICKERS.keys())[:limit]
        else:
            # KOSPI와 KOSDAQ 섞어서
            kospi_tickers = list(self.KOSPI_TICKERS.keys())[:limit//2]
            kosdaq_tickers = list(self.KOSDAQ_TICKERS.keys())[:limit//2]
            tickers = kospi_tickers + kosdaq_tickers
        
        stocks = []
        for ticker in tickers:
            data = self.get_stock_data(ticker, period="1mo")
            if 'error' not in data:
                stocks.append(data)
        
        # 시가총액 기준 정렬
        stocks.sort(key=lambda x: x.get('market_cap', 0), reverse=True)
        
        return stocks[:limit]
    
    def analyze_korean_market_trend(self) -> Dict[str, Any]:
        """
        한국 시장 전체 트렌드 분석
        
        Returns:
            시장 트렌드 분석 결과
        """
        # KOSPI 지수
        kospi = yf.Ticker('^KS11')
        kospi_hist = kospi.history(period="1mo")
        
        # KOSDAQ 지수
        kosdaq = yf.Ticker('^KQ11')
        kosdaq_hist = kosdaq.history(period="1mo")
        
        # 시장 트렌드 계산
        kospi_trend = self._calculate_market_trend(kospi_hist)
        kosdaq_trend = self._calculate_market_trend(kosdaq_hist)
        
        # 섹터별 분석
        sectors = self._analyze_sectors()
        
        return {
            'kospi': {
                'current': float(kospi_hist['Close'].iloc[-1]) if len(kospi_hist) > 0 else 0,
                'change_1d': kospi_trend.get('change_1d', 0),
                'change_1w': kospi_trend.get('change_1w', 0),
                'change_1m': kospi_trend.get('change_1m', 0),
                'trend': kospi_trend.get('trend', 'neutral')
            },
            'kosdaq': {
                'current': float(kosdaq_hist['Close'].iloc[-1]) if len(kosdaq_hist) > 0 else 0,
                'change_1d': kosdaq_trend.get('change_1d', 0),
                'change_1w': kosdaq_trend.get('change_1w', 0),
                'change_1m': kosdaq_trend.get('change_1m', 0),
                'trend': kosdaq_trend.get('trend', 'neutral')
            },
            'sectors': sectors,
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_market_trend(self, hist: pd.DataFrame) -> Dict[str, Any]:
        """
        시장 트렌드 계산
        
        Args:
            hist: 지수 과거 데이터
        
        Returns:
            트렌드 분석 결과
        """
        if len(hist) < 2:
            return {'trend': 'neutral'}
        
        current = hist['Close'].iloc[-1]
        
        # 1일 변화
        change_1d = ((current - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2] * 100) if len(hist) > 1 else 0
        
        # 1주 변화
        week_ago_idx = max(-len(hist), -5)
        change_1w = ((current - hist['Close'].iloc[week_ago_idx]) / hist['Close'].iloc[week_ago_idx] * 100) if len(hist) > 5 else change_1d
        
        # 1개월 변화
        month_ago_idx = max(-len(hist), -20)
        change_1m = ((current - hist['Close'].iloc[month_ago_idx]) / hist['Close'].iloc[month_ago_idx] * 100) if len(hist) > 20 else change_1w
        
        # 트렌드 판단
        if change_1m > 5:
            trend = 'strong_bullish'
        elif change_1m > 2:
            trend = 'bullish'
        elif change_1m < -5:
            trend = 'strong_bearish'
        elif change_1m < -2:
            trend = 'bearish'
        else:
            trend = 'neutral'
        
        return {
            'change_1d': float(change_1d),
            'change_1w': float(change_1w),
            'change_1m': float(change_1m),
            'trend': trend
        }
    
    def _analyze_sectors(self) -> Dict[str, Any]:
        """
        섹터별 분석
        
        Returns:
            섹터별 성과
        """
        sectors = {
            'technology': ['005930.KS', '000660.KS', '035420.KS', '035720.KS'],
            'automobile': ['005380.KS', '000270.KS'],
            'finance': ['105560.KS', '055550.KS', '086790.KS'],
            'bio': ['207940.KS', '068270.KS', '196170.KQ'],
            'battery': ['051910.KS', '006400.KS', '247540.KQ']
        }
        
        sector_performance = {}
        
        for sector, tickers in sectors.items():
            total_change = 0
            count = 0
            
            for ticker in tickers:
                try:
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period="1mo")
                    if len(hist) > 1:
                        change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
                        total_change += change
                        count += 1
                except:
                    continue
            
            if count > 0:
                avg_change = total_change / count
                sector_performance[sector] = {
                    'performance': float(avg_change),
                    'status': 'bullish' if avg_change > 0 else 'bearish'
                }
        
        return sector_performance

class KoreanNewsAnalyzer:
    """한국 뉴스 분석 클래스"""
    
    def __init__(self):
        """초기화"""
        self.sentiment_keywords = {
            'positive': ['상승', '급등', '호재', '개선', '증가', '성장', '신고가', '호조', '회복', '긍정'],
            'negative': ['하락', '급락', '악재', '감소', '부진', '하향', '우려', '위축', '부정', '조정']
        }
    
    def get_stock_news(self, ticker: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        종목 관련 뉴스 가져오기
        
        Args:
            ticker: 종목 코드
            limit: 가져올 뉴스 수
        
        Returns:
            뉴스 리스트
        """
        # 실제 구현시 네이버 금융 등의 API 사용
        # 여기서는 샘플 데이터 반환
        
        sample_news = [
            {
                'title': f'{ticker} 실적 개선 전망... 목표가 상향',
                'source': '한국경제',
                'time': datetime.now() - timedelta(minutes=30),
                'sentiment': 'positive',
                'summary': '애널리스트들이 실적 개선을 근거로 목표가를 상향 조정했다.'
            },
            {
                'title': f'{ticker} 신제품 출시 임박... 시장 기대감 상승',
                'source': '매일경제',
                'time': datetime.now() - timedelta(hours=1),
                'sentiment': 'positive',
                'summary': '새로운 제품 라인업이 곧 출시될 예정이며 시장의 기대가 높다.'
            },
            {
                'title': f'글로벌 경기 둔화 우려... {ticker} 영향은?',
                'source': '연합뉴스',
                'time': datetime.now() - timedelta(hours=2),
                'sentiment': 'neutral',
                'summary': '글로벌 경기 둔화가 예상되나 국내 기업들의 영향은 제한적일 전망이다.'
            }
        ]
        
        return sample_news[:limit]
    
    def analyze_news_sentiment(self, news_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        뉴스 감정 분석
        
        Args:
            news_list: 뉴스 리스트
        
        Returns:
            감정 분석 결과
        """
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        for news in news_list:
            sentiment = news.get('sentiment', 'neutral')
            if sentiment == 'positive':
                positive_count += 1
            elif sentiment == 'negative':
                negative_count += 1
            else:
                neutral_count += 1
        
        total = len(news_list)
        
        # 전체 감정 점수 계산 (0-100)
        if total > 0:
            sentiment_score = ((positive_count - negative_count) / total + 1) * 50
        else:
            sentiment_score = 50
        
        # 전체 감정 판단
        if sentiment_score >= 70:
            overall_sentiment = 'very_positive'
        elif sentiment_score >= 60:
            overall_sentiment = 'positive'
        elif sentiment_score >= 40:
            overall_sentiment = 'neutral'
        elif sentiment_score >= 30:
            overall_sentiment = 'negative'
        else:
            overall_sentiment = 'very_negative'
        
        return {
            'sentiment_score': sentiment_score,
            'overall_sentiment': overall_sentiment,
            'positive_ratio': positive_count / total if total > 0 else 0,
            'negative_ratio': negative_count / total if total > 0 else 0,
            'neutral_ratio': neutral_count / total if total > 0 else 0,
            'total_news': total
        }
    
    def get_market_news(self, market: str = "all") -> List[Dict[str, Any]]:
        """
        시장 전체 뉴스 가져오기
        
        Args:
            market: 시장 구분 (kospi, kosdaq, all)
        
        Returns:
            시장 뉴스 리스트
        """
        # 샘플 데이터
        market_news = [
            {
                'title': 'KOSPI 2,500선 회복... 외국인 순매수 지속',
                'source': '연합인포맥스',
                'time': datetime.now() - timedelta(minutes=15),
                'sentiment': 'positive',
                'category': 'market'
            },
            {
                'title': '반도체 업황 회복 기대감... 관련주 강세',
                'source': '이데일리',
                'time': datetime.now() - timedelta(minutes=45),
                'sentiment': 'positive',
                'category': 'sector'
            },
            {
                'title': '미 연준 금리 인상 가능성... 국내 증시 영향은?',
                'source': '한국경제',
                'time': datetime.now() - timedelta(hours=1),
                'sentiment': 'neutral',
                'category': 'global'
            },
            {
                'title': '2차전지 관련주 조정... 차익 실현 물량 출회',
                'source': '머니투데이',
                'time': datetime.now() - timedelta(hours=2),
                'sentiment': 'negative',
                'category': 'sector'
            },
            {
                'title': '기관 순매도 전환... 단기 조정 가능성',
                'source': '서울경제',
                'time': datetime.now() - timedelta(hours=3),
                'sentiment': 'negative',
                'category': 'market'
            }
        ]
        
        if market == "kospi":
            return [n for n in market_news if 'KOSPI' in n['title'] or 'kospi' in n['title'].lower()]
        elif market == "kosdaq":
            return [n for n in market_news if 'KOSDAQ' in n['title'] or 'kosdaq' in n['title'].lower()]
        else:
            return market_news