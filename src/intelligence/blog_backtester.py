"""블로그 인사이트 백테스팅 엔진

매일 블로그 글을 시점별로 분석하여 실제 시장 변화와 비교
인사이트-결과 상관관계를 계산하고 신뢰도를 평가
"""
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
import pandas as pd
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BlogInsight:
    """블로그 인사이트 데이터 클래스"""
    blog_id: int
    title: str
    content: str
    date: datetime
    url: str
    keywords: List[str]
    sentiment: float  # -1.0 (부정) ~ 1.0 (긍정)


@dataclass
class MarketOutcome:
    """시장 결과 데이터 클래스"""
    ticker: str
    start_date: datetime
    end_date: datetime
    start_price: float
    end_price: float
    return_pct: float
    volatility: float


@dataclass
class BacktestResult:
    """백테스팅 결과 데이터 클래스"""
    insight: BlogInsight
    prediction_topic: str
    prediction_direction: str  # "상승", "하락", "중립"
    actual_outcome: MarketOutcome
    correlation_score: float  # -1.0 ~ 1.0
    confidence_level: str  # "높음", "중간", "낮음"
    success: bool


class BlogBacktester:
    """블로그 백테스팅 엔진"""

    def __init__(self, blog_data_path: str = "data/blog_raw_all.json"):
        self.blog_data_path = Path(blog_data_path)
        self.blogs = self._load_blogs()
        logger.info(f"✅ {len(self.blogs)}개 블로그 글 로드 완료")

    def _load_blogs(self) -> List[Dict]:
        """블로그 데이터 로드"""
        if not self.blog_data_path.exists():
            logger.error(f"❌ 블로그 데이터 파일 없음: {self.blog_data_path}")
            return []

        with open(self.blog_data_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """날짜 문자열 파싱 (다양한 형식 지원)"""
        if not date_str:
            return None

        # "2025. 10. 2. 0:10" 형식
        try:
            date_str = date_str.strip()
            # ". " -> "-" 변환
            date_str = date_str.replace('. ', '-').replace('.', '').strip()
            parts = date_str.split()

            if len(parts) >= 3:
                year = int(parts[0])
                month = int(parts[1])
                day = int(parts[2])
                return datetime(year, month, day)
        except Exception as e:
            logger.warning(f"날짜 파싱 실패: {date_str}, 에러: {e}")
            return None

        return None

    def segment_blogs_by_time(self, months_back: int = 12) -> Dict[str, List[BlogInsight]]:
        """시점별로 블로그 분할

        Args:
            months_back: 몇 개월 전까지 데이터를 분할할지

        Returns:
            {"2024-01": [BlogInsight, ...], "2024-02": [...], ...}
        """
        segments = {}
        now = datetime.now()

        for blog in self.blogs:
            date = self._parse_date(blog.get('date', ''))
            if not date:
                continue

            # 너무 오래된 데이터는 제외
            if (now - date).days > months_back * 30:
                continue

            # 월별로 그룹화
            month_key = date.strftime("%Y-%m")

            if month_key not in segments:
                segments[month_key] = []

            # BlogInsight 객체 생성
            insight = BlogInsight(
                blog_id=blog.get('id', 0),
                title=blog.get('title', ''),
                content=blog.get('content', ''),
                date=date,
                url=blog.get('url', ''),
                keywords=self._extract_keywords(blog.get('content', '')),
                sentiment=self._calculate_sentiment(blog.get('content', ''))
            )

            segments[month_key].append(insight)

        logger.info(f"✅ {len(segments)}개 월별 세그먼트 생성 완료")
        return segments

    def _extract_keywords(self, text: str) -> List[str]:
        """텍스트에서 투자 관련 키워드 추출"""
        # 주요 키워드 리스트
        keywords = [
            # 종목/기업
            "삼성전자", "SK하이닉스", "TSMC", "엔비디아", "애플", "테슬라",
            "아마존", "구글", "마이크로소프트", "메타",

            # 섹터/산업
            "반도체", "AI", "인공지능", "전기차", "배터리", "바이오", "제약",
            "은행", "금융", "부동산", "건설", "자동차", "항공", "여행",

            # 경제/정책
            "금리", "인플레이션", "GDP", "실업률", "양적완화", "긴축",
            "무역전쟁", "관세", "환율", "달러", "원화",

            # 투자 전략
            "매수", "매도", "보유", "저평가", "고평가", "성장주", "가치주",
            "배당", "분할", "합병", "IPO", "상장",

            # 시장 상황
            "강세", "약세", "조정", "반등", "하락", "상승", "횡보",
            "변동성", "유동성", "거래량"
        ]

        found_keywords = []
        text_lower = text.lower()

        for keyword in keywords:
            if keyword.lower() in text_lower or keyword in text:
                found_keywords.append(keyword)

        return list(set(found_keywords))  # 중복 제거

    def _calculate_sentiment(self, text: str) -> float:
        """텍스트 감성 분석 (-1.0 ~ 1.0)"""
        # 긍정/부정 키워드 기반 간단한 감성 분석
        positive_words = [
            "상승", "호황", "성장", "증가", "개선", "회복", "강세", "긍정",
            "좋", "훌륭", "최고", "매수", "추천", "기대", "전망", "낙관"
        ]

        negative_words = [
            "하락", "불황", "감소", "악화", "부진", "약세", "부정",
            "나쁨", "최악", "매도", "우려", "위험", "비관", "손실"
        ]

        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)

        total = positive_count + negative_count
        if total == 0:
            return 0.0

        sentiment = (positive_count - negative_count) / total
        return max(-1.0, min(1.0, sentiment))

    def extract_predictions_from_insights(self, insights: List[BlogInsight]) -> List[Dict]:
        """블로그 인사이트에서 예측 추출

        예: "삼성전자 반도체 호황" -> {"ticker": "005930.KS", "direction": "상승"}
        """
        predictions = []

        # 키워드 -> 종목 심볼 매핑
        keyword_to_ticker = {
            "삼성전자": "005930.KS",
            "SK하이닉스": "000660.KS",
            "TSMC": "TSM",
            "엔비디아": "NVDA",
            "애플": "AAPL",
            "테슬라": "TSLA",
            "아마존": "AMZN",
            "구글": "GOOGL",
            "마이크로소프트": "MSFT",
            "메타": "META",
            # 섹터 ETF로 변환
            "반도체": "SMH",  # VanEck Semiconductor ETF
            "AI": "BOTZ",  # AI & Robotics ETF
            "전기차": "LIT",  # Lithium & Battery ETF
            "바이오": "XBI",  # Biotech ETF
        }

        for insight in insights:
            for keyword in insight.keywords:
                if keyword in keyword_to_ticker:
                    ticker = keyword_to_ticker[keyword]

                    # 감성 분석 결과로 방향 예측
                    if insight.sentiment > 0.2:
                        direction = "상승"
                    elif insight.sentiment < -0.2:
                        direction = "하락"
                    else:
                        direction = "중립"

                    predictions.append({
                        "insight": insight,
                        "ticker": ticker,
                        "direction": direction,
                        "confidence": abs(insight.sentiment)
                    })

        return predictions

    async def backtest_insight(
        self,
        insight: BlogInsight,
        ticker: str,
        direction: str,
        test_period_months: int = 3
    ) -> Optional[BacktestResult]:
        """개별 인사이트 백테스팅

        Args:
            insight: 블로그 인사이트
            ticker: 종목 심볼
            direction: 예측 방향 ("상승", "하락", "중립")
            test_period_months: 테스트 기간 (개월)

        Returns:
            BacktestResult 또는 None
        """
        try:
            import yfinance as yf

            # 실제 시장 데이터 수집
            start_date = insight.date
            end_date = start_date + timedelta(days=test_period_months * 30)

            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date)

            if hist.empty or len(hist) < 5:
                logger.warning(f"⚠️ {ticker} 데이터 부족: {start_date} ~ {end_date}")
                return None

            # 시작/종료 가격
            start_price = hist['Close'].iloc[0]
            end_price = hist['Close'].iloc[-1]
            return_pct = ((end_price - start_price) / start_price) * 100

            # 변동성 계산
            daily_returns = hist['Close'].pct_change().dropna()
            volatility = daily_returns.std() * np.sqrt(252) * 100  # 연간화

            # 실제 결과
            outcome = MarketOutcome(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                start_price=float(start_price),
                end_price=float(end_price),
                return_pct=float(return_pct),
                volatility=float(volatility)
            )

            # 예측 vs 실제 비교
            actual_direction = "상승" if return_pct > 2 else "하락" if return_pct < -2 else "중립"

            # 상관계수 계산
            if direction == actual_direction:
                correlation_score = 0.8 + (abs(return_pct) / 100) * 0.2  # 0.8 ~ 1.0
            elif direction == "중립" or actual_direction == "중립":
                correlation_score = 0.5  # 중립
            else:
                correlation_score = -0.5 - (abs(return_pct) / 100) * 0.5  # -0.5 ~ -1.0

            correlation_score = max(-1.0, min(1.0, correlation_score))

            # 신뢰도 레벨
            if abs(correlation_score) > 0.7:
                confidence_level = "높음"
            elif abs(correlation_score) > 0.4:
                confidence_level = "중간"
            else:
                confidence_level = "낮음"

            # 성공 여부
            success = (direction == actual_direction)

            result = BacktestResult(
                insight=insight,
                prediction_topic=ticker,
                prediction_direction=direction,
                actual_outcome=outcome,
                correlation_score=correlation_score,
                confidence_level=confidence_level,
                success=success
            )

            logger.info(f"✅ 백테스팅 완료: {ticker} ({direction}) -> 실제 {actual_direction} (수익률: {return_pct:.2f}%)")
            return result

        except Exception as e:
            logger.error(f"❌ 백테스팅 실패: {ticker}, 에러: {e}")
            return None

    async def run_full_backtest(self, months_back: int = 12, test_period_months: int = 3) -> List[BacktestResult]:
        """전체 백테스팅 실행

        Args:
            months_back: 몇 개월 전까지 백테스팅할지
            test_period_months: 각 예측의 테스트 기간 (개월)

        Returns:
            List[BacktestResult]
        """
        logger.info(f"🚀 전체 백테스팅 시작: 과거 {months_back}개월, 테스트 기간 {test_period_months}개월")

        # 1. 시점별 블로그 분할
        segments = self.segment_blogs_by_time(months_back)

        all_results = []

        # 2. 각 시점별로 백테스팅
        for month_key in sorted(segments.keys()):
            insights = segments[month_key]
            logger.info(f"\n📅 {month_key} 백테스팅 ({len(insights)}개 인사이트)")

            # 3. 인사이트에서 예측 추출
            predictions = self.extract_predictions_from_insights(insights)
            logger.info(f"   추출된 예측: {len(predictions)}개")

            # 4. 각 예측 백테스팅
            for i, pred in enumerate(predictions[:50]):  # 시간 절약을 위해 상위 50개만
                result = await self.backtest_insight(
                    insight=pred["insight"],
                    ticker=pred["ticker"],
                    direction=pred["direction"],
                    test_period_months=test_period_months
                )

                if result:
                    all_results.append(result)

                # 진행률 표시
                if (i + 1) % 10 == 0:
                    logger.info(f"   진행률: {i+1}/{len(predictions[:50])}")

        logger.info(f"\n🎉 전체 백테스팅 완료: {len(all_results)}개 결과")
        return all_results

    def analyze_backtest_results(self, results: List[BacktestResult]) -> Dict:
        """백테스팅 결과 분석 및 통계"""
        if not results:
            return {"error": "백테스팅 결과 없음"}

        total = len(results)
        successful = sum(1 for r in results if r.success)
        success_rate = (successful / total) * 100

        avg_correlation = np.mean([r.correlation_score for r in results])

        # 신뢰도별 성공률
        high_confidence = [r for r in results if r.confidence_level == "높음"]
        high_confidence_success_rate = (sum(1 for r in high_confidence if r.success) / len(high_confidence) * 100) if high_confidence else 0

        # 키워드별 성공률
        keyword_stats = {}
        for result in results:
            for keyword in result.insight.keywords:
                if keyword not in keyword_stats:
                    keyword_stats[keyword] = {"total": 0, "success": 0}
                keyword_stats[keyword]["total"] += 1
                if result.success:
                    keyword_stats[keyword]["success"] += 1

        # 성공률 계산
        for keyword in keyword_stats:
            stats = keyword_stats[keyword]
            stats["success_rate"] = (stats["success"] / stats["total"]) * 100 if stats["total"] > 0 else 0

        # 상위 키워드 (성공률 높은 순)
        top_keywords = sorted(
            keyword_stats.items(),
            key=lambda x: (x[1]["success_rate"], x[1]["total"]),
            reverse=True
        )[:10]

        return {
            "total_backtests": total,
            "successful": successful,
            "success_rate": round(success_rate, 2),
            "avg_correlation": round(avg_correlation, 4),
            "high_confidence_success_rate": round(high_confidence_success_rate, 2),
            "confidence_breakdown": {
                "높음": len([r for r in results if r.confidence_level == "높음"]),
                "중간": len([r for r in results if r.confidence_level == "중간"]),
                "낮음": len([r for r in results if r.confidence_level == "낮음"])
            },
            "top_keywords": [
                {"keyword": k, **v} for k, v in top_keywords
            ]
        }


# 테스트 실행
async def main():
    """백테스터 테스트"""
    backtester = BlogBacktester()

    # 전체 백테스팅 실행 (과거 6개월, 테스트 기간 3개월)
    results = await backtester.run_full_backtest(months_back=6, test_period_months=3)

    # 결과 분석
    analysis = backtester.analyze_backtest_results(results)

    print("\n" + "="*60)
    print("📊 블로그 백테스팅 결과 분석")
    print("="*60)
    print(json.dumps(analysis, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
