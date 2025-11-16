"""거시경제 분석 에이전트"""
import json
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.graph.state import AgentState, show_agent_reasoning
from src.utils.progress import progress
from src.utils.llm import call_llm
from src.tools.economic_indicators import get_economic_indicators, get_market_condition
from src.tools.news_aggregator import get_recent_news, analyze_news_sentiment


class MacroEconomicAnalysis(BaseModel):
    """거시경제 분석 결과"""
    market_outlook: str = Field(description="Overall market outlook: bullish, bearish, or neutral")
    confidence: float = Field(description="Confidence level between 0 and 100")
    key_factors: list[str] = Field(description="Key economic factors affecting the market")
    risks: list[str] = Field(description="Major risks to watch")
    opportunities: list[str] = Field(description="Investment opportunities based on macro conditions")
    recommendation: str = Field(description="Investment recommendation based on macro analysis")


class MacroEconomicSignals(BaseModel):
    """거시경제 기반 투자 신호"""
    signals: dict[str, dict] = Field(description="Dictionary of ticker to macro signals")


def macro_economic_agent(state: AgentState):
    """거시경제 지표 및 뉴스 기반 시장 분석 에이전트"""
    
    progress.update_status("macro_economic_agent", None, "Collecting economic indicators")
    
    # 경제지표 수집
    us_indicators = get_economic_indicators("US")
    kr_indicators = get_economic_indicators("KR")
    market_condition = get_market_condition()
    
    progress.update_status("macro_economic_agent", None, "Collecting recent news")
    
    # 뉴스 수집 및 분석
    recent_news = get_recent_news(days=7, limit=30)
    news_sentiment = analyze_news_sentiment(recent_news)
    
    progress.update_status("macro_economic_agent", None, "Analyzing macro conditions")
    
    # AI 분석 실행
    analysis = analyze_macro_conditions(
        us_indicators=us_indicators,
        kr_indicators=kr_indicators,
        market_condition=market_condition,
        news_sentiment=news_sentiment,
        recent_news=recent_news[:10],  # 최근 10개 뉴스만 전달
        model_name=state["metadata"]["model_name"],
        model_provider=state["metadata"]["model_provider"]
    )
    
    progress.update_status("macro_economic_agent", None, "Generating investment signals")
    
    # 티커별 신호 생성
    tickers = state["data"]["tickers"]
    signals = generate_macro_signals(
        tickers=tickers,
        analysis=analysis,
        model_name=state["metadata"]["model_name"],
        model_provider=state["metadata"]["model_provider"]
    )
    
    # 결과 저장
    result = {
        "analysis": analysis.model_dump(),
        "signals": signals.signals,
        "market_condition": market_condition.model_dump(),
        "news_sentiment": news_sentiment,
        "indicators": {
            "us": [ind.model_dump() for ind in us_indicators[:5]],
            "kr": [ind.model_dump() for ind in kr_indicators[:5]]
        }
    }
    
    message = HumanMessage(
        content=json.dumps(result),
        name="macro_economic_agent"
    )
    
    if state["metadata"]["show_reasoning"]:
        show_agent_reasoning(result, "Macro Economic Agent")
    
    # 시그널 저장
    for ticker, signal_data in signals.signals.items():
        if ticker not in state["data"]["analyst_signals"]:
            state["data"]["analyst_signals"][ticker] = {}
        state["data"]["analyst_signals"]["macro_economic_agent"] = signals.signals
    
    return {
        "messages": state["messages"] + [message],
        "data": state["data"]
    }


def analyze_macro_conditions(
    us_indicators: list,
    kr_indicators: list,
    market_condition: dict,
    news_sentiment: dict,
    recent_news: list,
    model_name: str,
    model_provider: str
) -> MacroEconomicAnalysis:
    """거시경제 상황 분석"""
    
    template = ChatPromptTemplate.from_messages([
        (
            "system",
            """You are a macro economic analyst specializing in global markets.
            
            Analyze the current economic conditions based on:
            1. US economic indicators
            2. Korean economic indicators
            3. Overall market conditions
            4. Recent news sentiment
            
            Provide a comprehensive analysis considering:
            - Interest rate environment
            - Inflation trends
            - Employment situation
            - GDP growth
            - Currency movements
            - Market sentiment from news
            
            Output your analysis in JSON format with clear recommendations.
            """
        ),
        (
            "human",
            """Analyze the current macro economic environment:
            
            US Economic Indicators:
            {us_indicators}
            
            Korean Economic Indicators:
            {kr_indicators}
            
            Market Condition Summary:
            {market_condition}
            
            News Sentiment Analysis:
            {news_sentiment}
            
            Recent Key News Headlines:
            {recent_news}
            
            Provide a comprehensive macro economic analysis with:
            - market_outlook: "bullish", "bearish", or "neutral"
            - confidence: 0-100
            - key_factors: list of major factors
            - risks: list of risks
            - opportunities: list of opportunities
            - recommendation: detailed investment recommendation
            """
        )
    ])
    
    # 데이터 준비
    us_ind_summary = "\n".join([f"- {ind.indicator_name}: {ind.value} {ind.unit}" for ind in us_indicators[:6]])
    kr_ind_summary = "\n".join([f"- {ind.indicator_name}: {ind.value} {ind.unit}" for ind in kr_indicators[:6]])
    news_headlines = "\n".join([f"- {news.title} ({news.source})" for news in recent_news])
    
    prompt = template.invoke({
        "us_indicators": us_ind_summary,
        "kr_indicators": kr_ind_summary,
        "market_condition": json.dumps(market_condition.model_dump(), indent=2),
        "news_sentiment": json.dumps(news_sentiment, indent=2),
        "recent_news": news_headlines
    })
    
    def create_default_analysis():
        return MacroEconomicAnalysis(
            market_outlook="neutral",
            confidence=50.0,
            key_factors=["Economic data collection in progress"],
            risks=["Market volatility"],
            opportunities=["Diversified portfolio approach"],
            recommendation="Maintain balanced portfolio with focus on quality assets"
        )
    
    return call_llm(
        prompt=prompt,
        model_name=model_name,
        model_provider=model_provider,
        pydantic_model=MacroEconomicAnalysis,
        agent_name="macro_economic_agent",
        default_factory=create_default_analysis
    )


def generate_macro_signals(
    tickers: list[str],
    analysis: MacroEconomicAnalysis,
    model_name: str,
    model_provider: str
) -> MacroEconomicSignals:
    """거시경제 분석을 기반으로 티커별 신호 생성"""
    
    template = ChatPromptTemplate.from_messages([
        (
            "system",
            """Based on the macro economic analysis, generate trading signals for each ticker.
            
            Consider how macro conditions affect different stocks:
            - Tech stocks: affected by interest rates, growth outlook
            - Financial stocks: benefit from higher rates
            - Consumer stocks: affected by employment, consumer confidence
            - Export-oriented stocks: affected by currency, global demand
            
            Provide signal and confidence for each ticker.
            """
        ),
        (
            "human",
            """Generate trading signals based on this macro analysis:
            
            Market Outlook: {market_outlook}
            Confidence: {confidence}
            Key Factors: {key_factors}
            Risks: {risks}
            Opportunities: {opportunities}
            
            Tickers to analyze: {tickers}
            
            Output in JSON format:
            {{
              "signals": {{
                "TICKER1": {{
                  "signal": "bullish/bearish/neutral",
                  "confidence": 0-100,
                  "reasoning": "explanation"
                }},
                ...
              }}
            }}
            """
        )
    ])
    
    prompt = template.invoke({
        "market_outlook": analysis.market_outlook,
        "confidence": analysis.confidence,
        "key_factors": ", ".join(analysis.key_factors),
        "risks": ", ".join(analysis.risks),
        "opportunities": ", ".join(analysis.opportunities),
        "tickers": ", ".join(tickers)
    })
    
    def create_default_signals():
        return MacroEconomicSignals(
            signals={
                ticker: {
                    "signal": "neutral",
                    "confidence": 50.0,
                    "reasoning": "Awaiting detailed macro analysis"
                }
                for ticker in tickers
            }
        )
    
    return call_llm(
        prompt=prompt,
        model_name=model_name,
        model_provider=model_provider,
        pydantic_model=MacroEconomicSignals,
        agent_name="macro_economic_agent",
        default_factory=create_default_signals
    )


