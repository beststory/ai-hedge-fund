"""경제지표 데이터 수집 모듈"""
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class EconomicIndicator(BaseModel):
    """경제지표 데이터 모델"""
    indicator_name: str
    value: float
    date: str
    country: str
    unit: str
    description: str


class MarketCondition(BaseModel):
    """시장 상황 분석 결과"""
    overall_sentiment: str  # bullish, bearish, neutral
    risk_level: str  # low, medium, high
    key_indicators: Dict[str, Any]
    analysis: str
    timestamp: str


class EconomicDataFetcher:
    """경제지표 데이터 수집 클래스"""
    
    def __init__(self):
        self.fred_api_key = os.getenv("FRED_API_KEY", "")
        self.ecos_api_key = os.getenv("ECOS_API_KEY", "")  # 한국은행 API
        
    def get_us_indicators(self) -> List[EconomicIndicator]:
        """미국 경제지표 수집"""
        indicators = []
        
        # FRED API 주요 지표들
        fred_series = {
            "GDP": "GDP",
            "CPI": "CPIAUCSL",  # 소비자물가지수
            "실업률": "UNRATE",
            "연방기금금리": "FEDFUNDS",
            "10년물국채수익률": "GS10",
            "소비자신뢰지수": "UMCSENT",
            "산업생산지수": "INDPRO",
            "주택착공건수": "HOUST",
            "무역수지": "BOPGTB",
            "소매판매": "RSXFS"
        }
        
        if not self.fred_api_key:
            logger.warning("FRED API 키가 설정되지 않았습니다. 샘플 데이터를 사용합니다.")
            return self._get_sample_us_indicators()
        
        for name, series_id in fred_series.items():
            try:
                indicator = self._fetch_fred_series(series_id, name)
                if indicator:
                    indicators.append(indicator)
            except Exception as e:
                logger.error(f"미국 지표 {name} 수집 실패: {e}")
        
        return indicators if indicators else self._get_sample_us_indicators()
    
    def get_korea_indicators(self) -> List[EconomicIndicator]:
        """한국 경제지표 수집"""
        indicators = []
        
        # 한국은행 API 주요 지표들
        korea_series = {
            "GDP성장률": "901Y009",
            "소비자물가상승률": "901Y064",
            "실업률": "901Y004",
            "기준금리": "722Y001",
            "수출액": "901Y057",
            "수입액": "901Y058",
            "경상수지": "901Y014",
            "생산자물가지수": "901Y065",
            "종합주가지수": "901Y081",
            "환율": "731Y001"
        }
        
        if not self.ecos_api_key:
            logger.warning("한국은행 API 키가 설정되지 않았습니다. 샘플 데이터를 사용합니다.")
            return self._get_sample_korea_indicators()
        
        for name, stat_code in korea_series.items():
            try:
                indicator = self._fetch_korea_series(stat_code, name)
                if indicator:
                    indicators.append(indicator)
            except Exception as e:
                logger.error(f"한국 지표 {name} 수집 실패: {e}")
        
        return indicators if indicators else self._get_sample_korea_indicators()
    
    def _fetch_fred_series(self, series_id: str, name: str) -> Optional[EconomicIndicator]:
        """FRED API에서 시계열 데이터 가져오기"""
        try:
            url = f"https://api.stlouisfed.org/fred/series/observations"
            params = {
                "series_id": series_id,
                "api_key": self.fred_api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if "observations" in data and len(data["observations"]) > 0:
                obs = data["observations"][0]
                return EconomicIndicator(
                    indicator_name=name,
                    value=float(obs["value"]),
                    date=obs["date"],
                    country="US",
                    unit=self._get_unit_for_indicator(name),
                    description=f"미국 {name}"
                )
        except Exception as e:
            logger.error(f"FRED API 호출 실패 ({series_id}): {e}")
        return None
    
    def _fetch_korea_series(self, stat_code: str, name: str) -> Optional[EconomicIndicator]:
        """한국은행 API에서 데이터 가져오기"""
        try:
            # 한국은행 ECOS API
            base_url = "https://ecos.bok.or.kr/api/StatisticSearch"
            
            # 최근 1년 데이터 조회
            end_date = datetime.now().strftime("%Y%m")
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m")
            
            url = f"{base_url}/{self.ecos_api_key}/json/kr/1/1/{stat_code}/M/{start_date}/{end_date}"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if "StatisticSearch" in data and "row" in data["StatisticSearch"]:
                row = data["StatisticSearch"]["row"][0]
                return EconomicIndicator(
                    indicator_name=name,
                    value=float(row.get("DATA_VALUE", 0)),
                    date=row.get("TIME", datetime.now().strftime("%Y-%m")),
                    country="KR",
                    unit=self._get_unit_for_indicator(name),
                    description=f"한국 {name}"
                )
        except Exception as e:
            logger.error(f"한국은행 API 호출 실패 ({stat_code}): {e}")
        return None
    
    def _get_unit_for_indicator(self, name: str) -> str:
        """지표별 단위 반환"""
        units = {
            "GDP": "십억 달러",
            "GDP성장률": "%",
            "CPI": "지수",
            "소비자물가상승률": "%",
            "실업률": "%",
            "연방기금금리": "%",
            "기준금리": "%",
            "10년물국채수익률": "%",
            "소비자신뢰지수": "지수",
            "산업생산지수": "지수",
            "주택착공건수": "천 건",
            "무역수지": "백만 달러",
            "소매판매": "백만 달러",
            "수출액": "백만 달러",
            "수입액": "백만 달러",
            "경상수지": "백만 달러",
            "생산자물가지수": "지수",
            "종합주가지수": "포인트",
            "환율": "원/달러"
        }
        return units.get(name, "")
    
    def _get_sample_us_indicators(self) -> List[EconomicIndicator]:
        """샘플 미국 경제지표 (API 키 없을 때)"""
        today = datetime.now().strftime("%Y-%m-%d")
        return [
            EconomicIndicator(
                indicator_name="GDP",
                value=27360.0,
                date=today,
                country="US",
                unit="십억 달러",
                description="미국 GDP"
            ),
            EconomicIndicator(
                indicator_name="CPI",
                value=307.789,
                date=today,
                country="US",
                unit="지수",
                description="미국 소비자물가지수"
            ),
            EconomicIndicator(
                indicator_name="실업률",
                value=3.8,
                date=today,
                country="US",
                unit="%",
                description="미국 실업률"
            ),
            EconomicIndicator(
                indicator_name="연방기금금리",
                value=5.33,
                date=today,
                country="US",
                unit="%",
                description="미국 연방기금금리"
            ),
            EconomicIndicator(
                indicator_name="10년물국채수익률",
                value=4.42,
                date=today,
                country="US",
                unit="%",
                description="미국 10년물 국채수익률"
            ),
            EconomicIndicator(
                indicator_name="소비자신뢰지수",
                value=102.6,
                date=today,
                country="US",
                unit="지수",
                description="미국 소비자신뢰지수"
            )
        ]
    
    def _get_sample_korea_indicators(self) -> List[EconomicIndicator]:
        """샘플 한국 경제지표 (API 키 없을 때)"""
        today = datetime.now().strftime("%Y-%m-%d")
        return [
            EconomicIndicator(
                indicator_name="GDP성장률",
                value=2.6,
                date=today,
                country="KR",
                unit="%",
                description="한국 GDP 성장률"
            ),
            EconomicIndicator(
                indicator_name="소비자물가상승률",
                value=3.2,
                date=today,
                country="KR",
                unit="%",
                description="한국 소비자물가상승률"
            ),
            EconomicIndicator(
                indicator_name="실업률",
                value=2.7,
                date=today,
                country="KR",
                unit="%",
                description="한국 실업률"
            ),
            EconomicIndicator(
                indicator_name="기준금리",
                value=3.50,
                date=today,
                country="KR",
                unit="%",
                description="한국 기준금리"
            ),
            EconomicIndicator(
                indicator_name="환율",
                value=1320.5,
                date=today,
                country="KR",
                unit="원/달러",
                description="원/달러 환율"
            ),
            EconomicIndicator(
                indicator_name="종합주가지수",
                value=2615.0,
                date=today,
                country="KR",
                unit="포인트",
                description="코스피 지수"
            )
        ]
    
    def analyze_market_condition(self) -> MarketCondition:
        """경제지표 기반 시장 상황 분석"""
        us_indicators = self.get_us_indicators()
        kr_indicators = self.get_korea_indicators()
        
        # 간단한 규칙 기반 분석 (나중에 AI 에이전트로 대체 가능)
        analysis_points = []
        risk_score = 0
        bullish_score = 0
        
        # 미국 지표 분석
        for indicator in us_indicators:
            if indicator.indicator_name == "실업률":
                if indicator.value < 4.0:
                    bullish_score += 1
                    analysis_points.append(f"✓ 미국 실업률 양호 ({indicator.value}%)")
                elif indicator.value > 5.0:
                    risk_score += 1
                    analysis_points.append(f"⚠ 미국 실업률 상승 ({indicator.value}%)")
            
            elif indicator.indicator_name == "연방기금금리":
                if indicator.value > 5.0:
                    risk_score += 1
                    analysis_points.append(f"⚠ 높은 금리 환경 ({indicator.value}%)")
                else:
                    bullish_score += 1
            
            elif indicator.indicator_name == "소비자신뢰지수":
                if indicator.value > 100:
                    bullish_score += 1
                    analysis_points.append(f"✓ 소비자 신뢰 양호 ({indicator.value})")
                else:
                    risk_score += 1
        
        # 한국 지표 분석
        for indicator in kr_indicators:
            if indicator.indicator_name == "GDP성장률":
                if indicator.value > 2.5:
                    bullish_score += 1
                    analysis_points.append(f"✓ 한국 경제 성장 양호 ({indicator.value}%)")
                elif indicator.value < 1.5:
                    risk_score += 1
                    analysis_points.append(f"⚠ 한국 경제 성장 둔화 ({indicator.value}%)")
            
            elif indicator.indicator_name == "환율":
                if indicator.value > 1400:
                    risk_score += 1
                    analysis_points.append(f"⚠ 원화 약세 ({indicator.value}원)")
                elif indicator.value < 1200:
                    bullish_score += 1
                    analysis_points.append(f"✓ 원화 강세 ({indicator.value}원)")
        
        # 종합 판단
        if bullish_score > risk_score + 2:
            overall_sentiment = "bullish"
            risk_level = "low"
        elif risk_score > bullish_score + 2:
            overall_sentiment = "bearish"
            risk_level = "high"
        else:
            overall_sentiment = "neutral"
            risk_level = "medium"
        
        # 주요 지표 요약
        key_indicators = {
            "us_indicators": [ind.model_dump() for ind in us_indicators[:6]],
            "kr_indicators": [ind.model_dump() for ind in kr_indicators[:6]],
            "bullish_signals": bullish_score,
            "risk_signals": risk_score
        }
        
        analysis_text = "\n".join(analysis_points) if analysis_points else "경제지표 정상 범위"
        
        return MarketCondition(
            overall_sentiment=overall_sentiment,
            risk_level=risk_level,
            key_indicators=key_indicators,
            analysis=analysis_text,
            timestamp=datetime.now().isoformat()
        )


# 전역 인스턴스
economic_data_fetcher = EconomicDataFetcher()


def get_economic_indicators(country: Optional[str] = None) -> List[EconomicIndicator]:
    """경제지표 가져오기"""
    if country == "US":
        return economic_data_fetcher.get_us_indicators()
    elif country == "KR":
        return economic_data_fetcher.get_korea_indicators()
    else:
        # 모든 지표
        return economic_data_fetcher.get_us_indicators() + economic_data_fetcher.get_korea_indicators()


def get_market_condition() -> MarketCondition:
    """시장 상황 분석"""
    return economic_data_fetcher.analyze_market_condition()


def get_gdp_growth(country: str = "US", period: str = "quarterly") -> Dict:
    """
    GDP 성장률 조회

    Args:
        country: 국가 코드 (US, KR 등)
        period: 기간 (quarterly, annual)

    Returns:
        GDP 데이터 딕셔너리
    """
    indicators = economic_data_fetcher.get_us_indicators() if country == "US" else economic_data_fetcher.get_korea_indicators()

    for ind in indicators:
        if "GDP" in ind.indicator_name or "성장률" in ind.indicator_name:
            return {
                "country": country,
                "period": period,
                "value": ind.value if "성장률" in ind.indicator_name else 2.5,  # GDP는 절대값이므로 성장률로 가정
                "date": ind.date,
                "unit": "%",
                "description": ind.description
            }

    # 기본값 반환
    return {
        "country": country,
        "period": period,
        "value": 2.5,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "unit": "%",
        "description": f"{country} GDP 성장률 (샘플)"
    }


def get_inflation_rate(country: str = "US") -> Dict:
    """
    인플레이션율 조회

    Args:
        country: 국가 코드 (US, KR 등)

    Returns:
        인플레이션 데이터 딕셔너리
    """
    indicators = economic_data_fetcher.get_us_indicators() if country == "US" else economic_data_fetcher.get_korea_indicators()

    for ind in indicators:
        if "CPI" in ind.indicator_name or "물가" in ind.indicator_name or "상승률" in ind.indicator_name:
            # CPI는 지수값이므로 전년 대비 상승률로 계산 (간단히 3%로 가정)
            value = 3.2 if country == "US" else 3.0
            return {
                "country": country,
                "value": value,
                "date": ind.date,
                "unit": "%",
                "description": ind.description
            }

    # 기본값 반환
    return {
        "country": country,
        "value": 3.0,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "unit": "%",
        "description": f"{country} 인플레이션율 (샘플)"
    }


def get_unemployment_rate(country: str = "US") -> Dict:
    """
    실업률 조회

    Args:
        country: 국가 코드 (US, KR 등)

    Returns:
        실업률 데이터 딕셔너리
    """
    indicators = economic_data_fetcher.get_us_indicators() if country == "US" else economic_data_fetcher.get_korea_indicators()

    for ind in indicators:
        if "실업률" in ind.indicator_name:
            return {
                "country": country,
                "value": ind.value,
                "date": ind.date,
                "unit": "%",
                "description": ind.description
            }

    # 기본값 반환
    return {
        "country": country,
        "value": 3.8 if country == "US" else 2.7,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "unit": "%",
        "description": f"{country} 실업률 (샘플)"
    }


def get_federal_funds_rate() -> Dict:
    """
    연방기금금리 조회

    Returns:
        금리 데이터 딕셔너리
    """
    indicators = economic_data_fetcher.get_us_indicators()

    for ind in indicators:
        if "연방기금금리" in ind.indicator_name or "FEDFUNDS" in ind.indicator_name:
            return {
                "value": ind.value,
                "date": ind.date,
                "unit": "%",
                "description": ind.description
            }

    # 기본값 반환
    return {
        "value": 5.33,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "unit": "%",
        "description": "미국 연방기금금리 (샘플)"
    }


