"""RAG 기반 지능형 포트폴리오 조언 시스템"""
import logging
from typing import List, Dict
from datetime import datetime, timedelta
from src.tools.supabase_rag import SupabaseRAG
from src.utils.llm import call_llm
from src.llm.models import ModelProvider
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StockRecommendation(BaseModel):
    """종목별 투자 추천"""
    ticker: str = Field(description="종목 심볼")
    weight: float = Field(description="포트폴리오 비중 (0.0 ~ 1.0)")
    confidence: str = Field(description="확신도 (높음, 보통, 낮음)")
    reasoning: str = Field(description="추천 근거 요약 (1-2문장)")


class PortfolioRecommendations(BaseModel):
    """전체 포트폴리오 추천"""
    recommendations: List[StockRecommendation] = Field(description="종목별 추천 리스트")
    market_outlook: str = Field(description="현재 시장 전망 (긍정적, 중립, 부정적)")
    strategy_summary: str = Field(description="투자 전략 요약 (2-3문장)")


class RAGPortfolioAdvisor:
    """RAG 기반 포트폴리오 조언자"""

    def __init__(self):
        self.rag = SupabaseRAG()

    def get_stock_insights_with_time_weight(self, ticker: str, top_k: int = 10) -> List[Dict]:
        """종목 관련 인사이트를 시간 가중치와 함께 검색"""
        # 종목명으로 RAG 검색
        search_queries = [
            ticker,
            f"{ticker} 투자",
            f"{ticker} 분석",
            f"{ticker} 전망"
        ]

        all_insights = []
        for query in search_queries:
            try:
                insights = self.rag.search_similar(query, top_k=top_k)
                all_insights.extend(insights)
            except Exception as e:
                logger.error(f"RAG 검색 실패 ({query}): {e}")

        # 중복 제거 (id 기준)
        unique_insights = {}
        for insight in all_insights:
            insight_id = insight.get('id')
            if insight_id and insight_id not in unique_insights:
                unique_insights[insight_id] = insight

        insights_list = list(unique_insights.values())

        # 시간 가중치 계산
        now = datetime.now()
        for insight in insights_list:
            try:
                # 날짜 파싱 (예: "2025. 10. 2. 0:10")
                date_str = insight.get('date', '')
                if date_str:
                    # 날짜 형식 정규화
                    date_str = date_str.replace('. ', '-').replace('.', '').strip()
                    date_parts = date_str.split()
                    if len(date_parts) >= 3:
                        year = int(date_parts[0])
                        month = int(date_parts[1])
                        day = int(date_parts[2])
                        insight_date = datetime(year, month, day)

                        # 경과 일수 계산
                        days_ago = (now - insight_date).days

                        # 시간 가중치 (최근일수록 높은 가중치)
                        # 1개월 이내: 1.0, 3개월 이내: 0.7, 6개월 이내: 0.4, 그 이상: 0.2
                        if days_ago <= 30:
                            time_weight = 1.0
                        elif days_ago <= 90:
                            time_weight = 0.7
                        elif days_ago <= 180:
                            time_weight = 0.4
                        else:
                            time_weight = 0.2

                        insight['time_weight'] = time_weight
                        insight['days_ago'] = days_ago
                    else:
                        insight['time_weight'] = 0.5
                        insight['days_ago'] = 999
                else:
                    insight['time_weight'] = 0.5
                    insight['days_ago'] = 999
            except Exception as e:
                logger.warning(f"시간 가중치 계산 실패: {e}")
                insight['time_weight'] = 0.5
                insight['days_ago'] = 999

        # 유사도와 시간 가중치를 결합한 최종 점수로 정렬
        for insight in insights_list:
            similarity = insight.get('similarity', 0.5)
            time_weight = insight.get('time_weight', 0.5)
            # 최종 점수 = 유사도 70% + 시간 가중치 30%
            insight['final_score'] = similarity * 0.7 + time_weight * 0.3

        # 최종 점수로 정렬
        insights_list.sort(key=lambda x: x.get('final_score', 0), reverse=True)

        return insights_list[:top_k]

    def analyze_portfolio_with_rag(self, stocks: List[Dict], ai_engine: str = "ollama") -> Dict:
        """RAG 인사이트를 기반으로 포트폴리오 비중 분석"""
        logger.info(f"\n{'='*80}")
        logger.info(f"RAG 기반 포트폴리오 분석 시작 (AI 엔진: {ai_engine})")
        logger.info(f"  - 종목 수: {len(stocks)}개")
        logger.info(f"{'='*80}\n")

        # 각 종목별 인사이트 수집
        stock_insights = {}
        for stock in stocks:
            ticker = stock['ticker']
            logger.info(f"[{ticker}] 인사이트 검색 중...")

            insights = self.get_stock_insights_with_time_weight(ticker, top_k=5)
            stock_insights[ticker] = {
                'stock': stock,
                'insights': insights,
                'insight_count': len(insights),
                'avg_sentiment_score': self._calculate_sentiment_score(insights),
                'recent_mention_count': sum(1 for i in insights if i.get('days_ago', 999) <= 30)
            }

            logger.info(f"  ✅ {len(insights)}개 인사이트 발견")
            logger.info(f"     최근 1개월 언급: {stock_insights[ticker]['recent_mention_count']}개")
            logger.info(f"     감성 점수: {stock_insights[ticker]['avg_sentiment_score']:.2f}")

        # LLM으로 종목별 비중 결정
        portfolio_weights = self._get_llm_portfolio_weights(stock_insights, ai_engine=ai_engine)

        return portfolio_weights

    def _calculate_sentiment_score(self, insights: List[Dict]) -> float:
        """인사이트 감성 점수 계산 (-1.0 ~ 1.0)"""
        if not insights:
            return 0.0

        sentiment_map = {
            "매우 긍정적": 1.0,
            "긍정적": 0.6,
            "조심스럽게 긍정적": 0.3,
            "중립": 0.0,
            "주의": -0.3,
            "부정적": -0.6
        }

        total_score = 0.0
        total_weight = 0.0

        for insight in insights:
            sentiment = insight.get('sentiment', '중립')
            time_weight = insight.get('time_weight', 0.5)
            score = sentiment_map.get(sentiment, 0.0)

            total_score += score * time_weight
            total_weight += time_weight

        return total_score / total_weight if total_weight > 0 else 0.0

    def _get_llm_portfolio_weights(self, stock_insights: Dict, ai_engine: str = "ollama") -> Dict:
        """LLM으로 포트폴리오 비중 결정"""
        # 프롬프트 생성
        stock_summaries = []
        for ticker, data in stock_insights.items():
            stock = data['stock']
            insights = data['insights']

            # 최근 인사이트 3개만 요약
            recent_insights = insights[:3]
            insight_texts = []
            for i, insight in enumerate(recent_insights, 1):
                days_ago = insight.get('days_ago', 999)
                sentiment = insight.get('sentiment', '중립')
                title = insight.get('title', '')
                insight_texts.append(f"{i}. [{days_ago}일 전] {title} (감성: {sentiment})")

            stock_summary = f"""
종목: {ticker}
현재가: ${stock.get('current_price', 0):.2f}
1년 수익률: {stock.get('returns_1y', 0):.1f}%
변동성: {stock.get('volatility', 0):.1f}%
PER: {stock.get('pe_ratio', 'N/A')}

블로그 인사이트 ({data['insight_count']}개 발견, 최근 1개월 {data['recent_mention_count']}개 언급):
{chr(10).join(insight_texts) if insight_texts else '관련 인사이트 없음'}

감성 점수: {data['avg_sentiment_score']:.2f} (-1.0 ~ 1.0)
"""
            stock_summaries.append(stock_summary)

        prompt = f"""당신은 전문 포트폴리오 매니저입니다. 아래 종목들에 대한 투자 블로그 분석을 바탕으로 포트폴리오 비중을 결정해주세요.

## 분석 대상 종목들:
{'=' * 80}
{chr(10).join(stock_summaries)}
{'=' * 80}

## 비중 결정 기준:
1. **최신성**: 최근 1개월 이내 언급이 많을수록 높은 비중
2. **감성**: 긍정적 감성이 높을수록 높은 비중
3. **기술적 지표**: 수익률이 높고 변동성이 적절한 종목 우대
4. **분산투자**: 한 종목에 과도하게 집중하지 않음 (최대 30%)

## 요구사항:
- 모든 종목의 비중 합계는 반드시 1.0이어야 합니다
- 각 종목의 최소 비중: 0.05 (5%)
- 각 종목의 최대 비중: 0.30 (30%)
- 블로그에서 최근 언급이 많고 긍정적인 종목에 더 높은 비중 부여
- 언급이 없거나 부정적인 종목은 낮은 비중 부여

JSON 형식으로 응답하세요:
{{
    "recommendations": [
        {{"ticker": "AAPL", "weight": 0.25, "confidence": "높음", "reasoning": "최근 1개월 5건 긍정적 언급, 안정적 수익"}},
        ...
    ],
    "market_outlook": "긍정적",
    "strategy_summary": "최근 블로그 분석 결과..."
}}
"""

        try:
            logger.info(f"\n🤖 LLM으로 포트폴리오 비중 계산 중... (엔진: {ai_engine})")
            logger.info(f"프롬프트 길이: {len(prompt)} 문자")

            # AI 엔진에 따라 모델 선택
            if ai_engine == "openai":
                model_provider = ModelProvider.OPENAI
                model_name = "gpt-4o-mini"
            else:
                model_provider = ModelProvider.OLLAMA
                model_name = "mistral-small3.1"

            response = call_llm(
                prompt=prompt,
                model_name=model_name,
                model_provider=model_provider,
                pydantic_model=PortfolioRecommendations
            )

            logger.info(f"✅ LLM 응답 받음: {len(response.recommendations)}개 추천")

            # 비중 정규화 (합계가 1.0이 되도록)
            total_weight = sum(r.weight for r in response.recommendations)
            logger.info(f"총 비중: {total_weight:.4f}")

            if total_weight > 0:
                for rec in response.recommendations:
                    rec.weight = rec.weight / total_weight

            logger.info("✅ 포트폴리오 비중 계산 완료\n")

            return {
                'recommendations': [
                    {
                        'ticker': r.ticker,
                        'weight': round(r.weight, 4),
                        'confidence': r.confidence,
                        'reasoning': r.reasoning
                    }
                    for r in response.recommendations
                ],
                'market_outlook': response.market_outlook,
                'strategy_summary': response.strategy_summary
            }

        except Exception as e:
            logger.error(f"❌ LLM 포트폴리오 비중 계산 실패: {e}")
            # 실패 시 동등 분할
            equal_weight = 1.0 / len(stock_insights)
            return {
                'recommendations': [
                    {
                        'ticker': ticker,
                        'weight': equal_weight,
                        'confidence': '보통',
                        'reasoning': 'AI 분석 실패, 동등 분할 적용'
                    }
                    for ticker in stock_insights.keys()
                ],
                'market_outlook': '중립',
                'strategy_summary': 'AI 분석 실패로 동등 분할 전략을 사용했습니다.'
            }


def get_rag_based_portfolio(stocks: List[Dict], total_investment: float, ai_engine: str = "ollama") -> Dict:
    """RAG 기반 포트폴리오 제안"""
    advisor = RAGPortfolioAdvisor()
    weights_data = advisor.analyze_portfolio_with_rag(stocks, ai_engine=ai_engine)

    # 비중에 따라 포트폴리오 구성
    portfolio = []
    allocated_amount = 0

    recommendations = weights_data['recommendations']

    # ticker로 매칭
    ticker_to_stock = {stock['ticker']: stock for stock in stocks}
    ticker_to_recommendation = {rec['ticker']: rec for rec in recommendations}

    for i, stock in enumerate(stocks):
        ticker = stock['ticker']
        recommendation = ticker_to_recommendation.get(ticker)

        if not recommendation:
            # 추천에 없는 종목은 최소 비중
            weight = 0.05
            confidence = '낮음'
            reasoning = '블로그에서 관련 정보 없음'
        else:
            weight = recommendation['weight']
            confidence = recommendation['confidence']
            reasoning = recommendation['reasoning']

        # 금액 계산
        amount = int(total_investment * weight)

        # 마지막 종목은 나머지 금액 전부 할당
        if i == len(stocks) - 1:
            amount = total_investment - allocated_amount

        allocated_amount += amount

        # 주식 수 계산
        current_price = stock.get('current_price', 0)
        shares = int(amount / current_price) if current_price > 0 else 0
        actual_amount = shares * current_price

        portfolio.append({
            "ticker": ticker,
            "allocation_ratio": round(weight * 100, 2),
            "recommended_amount": amount,
            "actual_amount": round(actual_amount, 2),
            "shares": shares,
            "current_price": current_price,
            "score": stock.get('score', 70),
            "returns_1y": stock.get('returns_1y', 0),
            "volatility": stock.get('volatility', 20),
            "pe_ratio": stock.get('pe_ratio', 'N/A'),
            "confidence": confidence,
            "rag_reasoning": reasoning
        })

    return {
        'portfolio': portfolio,
        'market_outlook': weights_data['market_outlook'],
        'strategy_summary': weights_data['strategy_summary']
    }
