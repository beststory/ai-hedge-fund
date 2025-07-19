from src.graph.state import AgentState, show_agent_reasoning
from src.tools.api import get_vix, get_treasury_yield, get_unemployment_rate
from langchain_core.messages import HumanMessage
import json
import pandas as pd
from typing_extensions import Literal
from pydantic import BaseModel


class MarketRegime(BaseModel):
    regime: Literal["Bullish", "Bearish", "Neutral", "High-Volatility"]
    reasoning: str


def market_regime_agent(state: AgentState):
    """
    Analyzes the overall market regime based on macroeconomic indicators.
    """
    data = state["data"]
    start_date = data["start_date"]
    end_date = data["end_date"]

    # Fetch macroeconomic data
    vix_data = get_vix(start_date, end_date)
    treasury_yield_data = get_treasury_yield(start_date, end_date)
    unemployment_data = get_unemployment_rate(start_date, end_date)

    # --- Analysis Logic ---
    vix_latest = vix_data['Close'].iloc[-1] if not vix_data.empty else None
    yield_latest = treasury_yield_data['Close'].iloc[-1] if not treasury_yield_data.empty else None
    unemployment_latest = unemployment_data['UNRATE'].iloc[-1] if not unemployment_data.empty else None

    regime = "Neutral"
    reasoning_parts = []

    # VIX Analysis
    if vix_latest:
        if vix_latest > 30:
            regime = "High-Volatility"
            reasoning_parts.append(f"VIX is very high ({vix_latest:.2f}), indicating significant market fear and uncertainty.")
        elif vix_latest > 20:
            if regime != "High-Volatility":
                regime = "Bearish"
            reasoning_parts.append(f"VIX is elevated ({vix_latest:.2f}), suggesting increased investor concern.")
        else:
            if regime == "Neutral":
                regime = "Bullish"
            reasoning_parts.append(f"VIX is low ({vix_latest:.2f}), indicating market complacency and bullish sentiment.")

    # Treasury Yield Analysis
    if yield_latest:
        # A simple check on the 10-year yield. A very high yield can signal inflation fears or a strong economy,
        # a very low one might signal a flight to safety (bearish).
        if yield_latest > 4.5:
             if regime == "Bullish":
                regime = "Neutral" # High yields can be a headwind for stocks
             reasoning_parts.append(f"10-year treasury yield is high ({yield_latest:.2f}%), which could restrain equity valuations.")
        elif yield_latest < 2.0:
            if regime == "Bullish":
                regime = "Neutral"
            reasoning_parts.append(f"10-year treasury yield is low ({yield_latest:.2f}%), often a sign of economic slowdown fears (flight to safety).")

    # Unemployment Rate Analysis
    if unemployment_latest:
        # Rising unemployment is a classic recession indicator.
        if unemployment_latest > 5.0:
            regime = "Bearish"
            reasoning_parts.append(f"Unemployment rate is high ({unemployment_latest:.2f}%), signaling economic weakness.")
        # We could also look at the trend (e.g., unemployment rising for 3 consecutive months).
        # For simplicity, we'll just use the latest level.

    # Final Decision
    if not reasoning_parts:
        reasoning = "Could not determine market regime due to lack of macroeconomic data."
    else:
        reasoning = " ".join(reasoning_parts)

    market_analysis = {
        "regime": regime,
        "reasoning": reasoning,
        "metrics": {
            "vix": vix_latest,
            "10y_treasury_yield": yield_latest,
            "unemployment_rate": unemployment_latest,
        }
    }

    # Add reasoning to the UI if requested
    if state["metadata"]["show_reasoning"]:
        show_agent_reasoning({"market_regime": market_analysis}, "Market Regime Agent")

    # Update the state
    state["data"]["market_regime"] = market_analysis

    return {"data": state["data"]}
