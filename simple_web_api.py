"""간단한 웹 API 서버 - 테스트용"""

import os
import logging
from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import json
import asyncio
from datetime import datetime

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase 클라이언트
from supabase import create_client, Client

# Yahoo Finance 통합
from src.tools.yahoo_finance import yahoo_analyzer

# RAG 시스템 통합 - Supabase 기반
from src.tools.supabase_rag import SupabaseRAG
from src.tools.rag_portfolio_advisor import get_rag_based_portfolio

# 캐시 매니저 통합 - 1시간 TTL 캐싱
from src.tools.cache_manager import cache_manager

# Supabase RAG 인스턴스 초기화
supabase_rag = SupabaseRAG()

# 기존 API 호환을 위한 wrapper 함수
def get_relevant_insights(query: str, top_k: int = 3):
    """Supabase RAG에서 관련 인사이트 검색 (벡터 + 텍스트 하이브리드)"""
    results = supabase_rag.search_similar(query, top_k=top_k, use_text_search=True)
    return results if results else []

def format_insights_for_llm(insights):
    """인사이트를 LLM 친화적 텍스트로 포맷"""
    if not insights:
        return ""

    formatted = "\n\n📊 **투자 인사이트 (블로그 분석)**:\n"
    for i, insight in enumerate(insights, 1):
        formatted += f"\n{i}. **{insight['title']}** (유사도: {insight['similarity']:.0%})\n"
        formatted += f"   - 섹터: {insight['sector']}\n"
        formatted += f"   - 감성: {insight['sentiment']}\n"
        formatted += f"   - 키워드: {', '.join(insight['keywords'][:5])}\n"
        formatted += f"   - 요약: {insight['content'][:150]}...\n"

    return formatted

# 환경변수 로드
from dotenv import load_dotenv
load_dotenv()

# Supabase 클라이언트 초기화
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:8000")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", os.getenv("ANON_KEY", ""))
SUPABASE_SERVICE_KEY = os.getenv("SERVICE_ROLE_KEY", "")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY) if SUPABASE_SERVICE_KEY else None

app = FastAPI(title="AI 헤지펀드 시스템")

# 정적 파일 서빙
app.mount("/static", StaticFiles(directory="web"), name="static")

# 거래 히스토리 저장소 (메모리 저장 - 실제 환경에서는 DB 사용)
trade_history = []

# 간단한 인증 시스템 (레거시 - Supabase Auth로 대체 예정)
USERNAME = os.getenv("WEB_USERNAME", "admin")
PASSWORD = os.getenv("WEB_PASSWORD", "hedge2024!")

# JWT 인증 미들웨어
async def verify_token(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """JWT 토큰 검증 및 사용자 정보 추출"""
    if not authorization:
        raise HTTPException(status_code=401, detail="인증 토큰이 필요합니다")

    try:
        # "Bearer <token>" 형식에서 토큰 추출
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="잘못된 인증 방식입니다")

        # Supabase를 통한 토큰 검증
        user = supabase.auth.get_user(token)

        if not user or not user.user:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")

        return {
            "user_id": user.user.id,
            "email": user.user.email,
            "user": user.user
        }

    except ValueError:
        raise HTTPException(status_code=401, detail="잘못된 토큰 형식입니다")
    except Exception as e:
        print(f"토큰 검증 실패: {e}")
        raise HTTPException(status_code=401, detail=f"토큰 검증 실패: {str(e)}")

class LoginRequest(BaseModel):
    username: str
    password: str

class AuthRequest(BaseModel):
    email: str
    password: str

class TradeRequest(BaseModel):
    symbol: str
    action: str
    quantity: int

@app.get("/", response_class=HTMLResponse)
async def root():
    """메인 페이지 (클라이언트 사이드에서 인증 체크)"""
    with open("web/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """로그인 페이지"""
    with open("web/login.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/auth/signup")
async def auth_signup(request: AuthRequest):
    """Supabase Auth 회원가입 - SERVICE_ROLE_KEY 사용하여 이메일 확인 우회"""
    try:
        if not supabase_admin:
            raise HTTPException(status_code=500, detail="관리자 권한이 설정되지 않았습니다")

        # Admin 클라이언트로 사용자 생성 (이메일 확인 우회)
        response = supabase_admin.auth.admin.create_user({
            "email": request.email,
            "password": request.password,
            "email_confirm": True  # 이메일 확인 자동 처리
        })

        if response.user:
            # 생성된 사용자로 로그인하여 세션 토큰 발급
            login_response = supabase.auth.sign_in_with_password({
                "email": request.email,
                "password": request.password
            })

            return {
                "success": True,
                "user": {
                    "id": response.user.id,
                    "email": response.user.email
                },
                "session": {
                    "access_token": login_response.session.access_token if login_response.session else None,
                    "refresh_token": login_response.session.refresh_token if login_response.session else None
                } if login_response.session else None,
                "message": "회원가입 성공"
            }
        else:
            raise HTTPException(status_code=400, detail="회원가입 실패")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"회원가입 실패: {str(e)}")

@app.post("/api/auth/login")
async def auth_login(request: AuthRequest):
    """Supabase Auth 로그인"""
    try:
        response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })

        if response.user and response.session:
            return {
                "success": True,
                "user": {
                    "id": response.user.id,
                    "email": response.user.email
                },
                "session": {
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token
                },
                "message": "로그인 성공"
            }
        else:
            raise HTTPException(status_code=401, detail="로그인 실패")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"로그인 실패: {str(e)}")

@app.post("/api/login")
async def login(request: LoginRequest):
    """로그인 (레거시)"""
    if request.username == USERNAME and request.password == PASSWORD:
        return {"success": True, "access_token": "demo-token", "token_type": "bearer"}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/api/status")
async def get_status():
    """시스템 상태"""
    return {
        "status": "running",
        "mode": "paper_trading",
        "account": {
            "balance": 100000.0,
            "buying_power": 95000.0,
            "positions": []
        }
    }

@app.get("/api/portfolio")
async def get_portfolio(current_user: Dict[str, Any] = Depends(verify_token)):
    """포트폴리오 정보 (인증 필요)"""
    # 사용자별 포트폴리오 조회 (향후 구현)
    user_id = current_user["user_id"]

    return {
        "user_id": user_id,
        "total_value": 100000.0,
        "cash": 95000.0,
        "positions": [
            {
                "symbol": "AAPL",
                "quantity": 10,
                "avg_price": 150.0,
                "current_price": 155.0,
                "market_value": 1550.0,
                "unrealized_pnl": 50.0
            }
        ]
    }

@app.post("/api/analyze")
async def analyze_stock(request: Dict[str, Any] = None):
    """주식 분석 - 개별 주식 또는 자동 스크리닝 (1시간 캐싱)"""
    if request is None:
        request = {}

    symbol = request.get("symbol", "")

    if symbol:
        # 캐시 조회 (symbol별로 1시간 캐싱)
        cached = cache_manager.get_cached("analyze", params={"symbol": symbol}, ttl_seconds=3600)
        if cached:
            logger.info(f"✅ 캐시에서 {symbol} 분석 반환")
            return cached

        # 개별 주식 분석 - yahoo_finance.py의 고급 기능 사용
        try:
            import yfinance as yf
            from src.tools.yahoo_finance import yahoo_analyzer

            logger.info(f"🔄 {symbol} 분석 새로 계산 중...")

            # 한국 종목 코드 변환 (6자리 숫자면 .KS 추가)
            yahoo_symbol = symbol
            if symbol.isdigit() and len(symbol) == 6:
                yahoo_symbol = f"{symbol}.KS"

            # 고급 metrics 계산 (캐싱 및 병렬 처리 적용)
            metrics = yahoo_analyzer.calculate_financial_metrics(yahoo_symbol)

            if not metrics:
                raise Exception("데이터를 가져올 수 없습니다")

            # 회사 정보 가져오기
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info
            company_name = info.get('longName', symbol)

            # RAG 인사이트 가져오기
            insights = get_relevant_insights(symbol, top_k=2)

            # 추천 로직
            returns_1y = metrics.get('returns_1y', 0)
            recommendation = "매수" if returns_1y > 10 else "관망" if returns_1y > 0 else "주의"

            # 기본 분석 생성 (야후 파이낸셜 데이터만 - 블로그 인사이트 제외)
            analysis = yahoo_analyzer.generate_stock_analysis(yahoo_symbol, metrics)

            result = {
                "success": True,  # success 플래그 추가
                "symbol": symbol,
                "company_name": company_name,
                "recommendation": recommendation,
                "confidence": 0.85,
                "analysis": analysis.strip(),
                "blog_insights": insights if insights else [],  # 블로그 인사이트 별도 필드
                "metrics": metrics  # 모든 metrics 포함 (returns_1m, returns_3m, volatility 등)
            }

            # 캐시 저장 (1시간)
            cache_manager.set_cached("analyze", result, params={"symbol": symbol}, ttl_seconds=3600)
            logger.info(f"💾 {symbol} 분석 캐시 저장 완료")

            return result
        except Exception as e:
            return {
                "symbol": symbol,
                "company_name": symbol,
                "error": f"분석 실패: {str(e)}",
                "analysis": f"{symbol} 분석 중 오류가 발생했습니다: {str(e)}",
                "metrics": {}
            }
    else:
        # 자동 주식 스크리닝 (캐싱된 top-stocks 활용)
        try:
            from src.tools.yahoo_finance import get_top_stocks
            top_stocks = get_top_stocks(5)
            return {
                "auto_screening": True,
                "top_stocks": top_stocks,
                "message": "AI가 선별한 상위 5개 추천 주식입니다."
            }
        except Exception as e:
            return {
                "auto_screening": False,
                "error": str(e),
                "message": f"자동 스크리닝 실패: {str(e)}"
            }

@app.get("/api/top-stocks")
async def get_top_stocks_api():
    """상위 추천 주식 조회 (1시간 캐싱)"""
    # 캐시 조회 (1시간 TTL)
    cached = cache_manager.get_cached("top-stocks", ttl_seconds=3600)
    if cached:
        logger.info("✅ 캐시에서 AI 추천 종목 반환")
        return cached

    try:
        from src.tools.yahoo_finance import get_top_stocks
        logger.info("🔄 AI 추천 종목 새로 계산 중...")
        top_stocks = get_top_stocks(5)

        result = {
            "success": True,
            "stocks": top_stocks,
            "generated_at": datetime.now().isoformat(),
            "message": "Yahoo Finance 데이터를 기반으로 한 AI 추천 주식입니다."
        }

        # 캐시 저장 (1시간)
        cache_manager.set_cached("top-stocks", result, ttl_seconds=3600)
        logger.info("💾 AI 추천 종목 캐시 저장 완료")

        return result
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"추천 주식 조회 실패: {str(e)}"
        }

@app.post("/api/trade")
async def execute_trade(request: TradeRequest, current_user: Dict[str, Any] = Depends(verify_token)):
    """거래 실행 (인증 필요)"""
    user_id = current_user["user_id"]

    return {
        "success": True,
        "user_id": user_id,
        "order_id": "demo-order-123",
        "message": f"{request.action} {request.quantity} shares of {request.symbol} - Paper Trading Mode",
        "status": "filled"
    }

@app.get("/api/trade-history")
async def get_trade_history():
    """거래 내역 (기존)"""
    return {
        "trades": [
            {
                "id": "trade-001",
                "symbol": "AAPL",
                "action": "BUY",
                "quantity": 10,
                "price": 150.0,
                "timestamp": "2024-01-01T10:00:00Z",
                "status": "filled"
            }
        ]
    }

@app.get("/api/alerts")
async def get_alerts():
    """알림 목록"""
    return {
        "alerts": [
            {
                "type": "info",
                "message": "AI 헤지펀드 시스템이 성공적으로 시작되었습니다.",
                "timestamp": "2024-01-01T09:00:00Z"
            },
            {
                "type": "warning",
                "message": "현재 페이퍼 트레이딩 모드로 실행 중입니다.",
                "timestamp": "2024-01-01T09:01:00Z"
            }
        ]
    }

@app.post("/api/portfolio-suggestion")
async def get_portfolio_suggestion(request: Dict[str, Any] = None):
    """AI 기반 포트폴리오 분산투자 제안 (1시간 캐싱)"""
    if request is None:
        request = {}

    # 투자 금액 (기본값: 1억원)
    total_investment = request.get("total_investment", 100000000)

    # 종목 리스트 (프론트엔드에서 전달되면 사용, 아니면 AI 추천 종목 사용)
    stocks_from_request = request.get("stocks", None)

    # 캐시 조회 (total_investment + stocks로 1시간 캐싱)
    stocks_key = ",".join(stocks_from_request) if stocks_from_request else "auto"
    cache_params = {"total_investment": total_investment, "stocks": stocks_key}
    cached = cache_manager.get_cached("portfolio-suggestion", params=cache_params, ttl_seconds=3600)
    if cached:
        logger.info(f"✅ 캐시에서 포트폴리오 제안 반환 (투자금액: {total_investment:,}원)")
        return cached

    try:
        from src.tools.yahoo_finance import get_top_stocks
        import yfinance as yf
        from src.tools.yahoo_finance import yahoo_analyzer

        # 종목 리스트 결정
        if stocks_from_request and len(stocks_from_request) > 0:
            # 프론트엔드에서 전달된 종목 리스트 사용 (상위 5개만)
            # 첫 5개만 선택
            selected_symbols = stocks_from_request[:5]

            top_stocks = []
            for stock_symbol in selected_symbols:
                try:
                    # 한국 종목 코드 변환
                    yahoo_symbol = stock_symbol
                    if stock_symbol.isdigit() and len(stock_symbol) == 6:
                        yahoo_symbol = f"{stock_symbol}.KS"

                    # metrics 계산
                    metrics = yahoo_analyzer.calculate_financial_metrics(yahoo_symbol)
                    if metrics:
                        ticker = yf.Ticker(yahoo_symbol)
                        info = ticker.info

                        top_stocks.append({
                            'ticker': stock_symbol,
                            'current_price': metrics.get('current_price', 0),
                            'score': metrics.get('score', 70),  # 기본 점수
                            'returns_1y': metrics.get('returns_1y', 0),
                            'volatility': metrics.get('volatility', 20),
                            'pe_ratio': metrics.get('pe_ratio', 'N/A')
                        })
                except Exception as e:
                    print(f"종목 {stock_symbol} 처리 실패: {e}")
                    continue
        else:
            # 기존 방식: AI 추천 상위 5개 종목 사용 (10개에서 5개로 축소)
            top_stocks = get_top_stocks(5)

        if not top_stocks:
            return {
                "success": False,
                "message": "추천 종목을 가져올 수 없습니다."
            }

        # ✨ RAG 기반 포트폴리오 비중 결정 (블로그 인사이트 활용)
        logger.info("\n🤖 RAG 기반 포트폴리오 제안 시작...")
        rag_result = get_rag_based_portfolio(top_stocks, total_investment)

        portfolio = rag_result['portfolio']
        market_outlook = rag_result['market_outlook']
        strategy_summary = rag_result['strategy_summary']

        # 리스크 분석
        avg_volatility = sum(p['volatility'] for p in portfolio) / len(portfolio) if portfolio else 0
        avg_returns = sum(p['returns_1y'] for p in portfolio) / len(portfolio) if portfolio else 0

        risk_level = "낮음" if avg_volatility < 20 else "보통" if avg_volatility < 35 else "높음"

        logger.info(f"✅ RAG 포트폴리오 제안 완료: {len(portfolio)}개 종목\n")

        # 포트폴리오에 회사 이름 추가
        for stock in portfolio:
            ticker = stock['ticker']
            try:
                yahoo_symbol = ticker
                if ticker.isdigit() and len(ticker) == 6:
                    yahoo_symbol = f"{ticker}.KS"

                ticker_obj = yf.Ticker(yahoo_symbol)
                info = ticker_obj.info
                stock['company_name'] = info.get('longName', ticker)
            except Exception as e:
                stock['company_name'] = ticker
                logger.warning(f"회사 이름 가져오기 실패 {ticker}: {e}")

        # 포트폴리오 종목들에 대한 블로그 인사이트 수집
        portfolio_insights = []
        related_stocks_set = set()

        for stock in portfolio:
            ticker = stock['ticker']
            # 각 종목에 대한 인사이트 검색 (top_k=2)
            insights = get_relevant_insights(ticker, top_k=2)

            for insight in insights:
                portfolio_insights.append({
                    "stock": ticker,
                    "title": insight.get("title", ""),
                    "content": insight.get("content", "")[:200] + "...",  # 요약만
                    "similarity": insight.get("similarity", 0),
                    "keywords": insight.get("keywords", [])[:5],
                    "sector": insight.get("sector", ""),
                    "sentiment": insight.get("sentiment", ""),
                    "url": insight.get("url", "")
                })

                # 인사이트의 키워드를 기반으로 유사 종목 찾기
                for keyword in insight.get("keywords", [])[:3]:
                    related_stocks_set.add(keyword)

        # 유사 종목 추천 (실제 거래 가능한 종목 심볼 반환)
        related_stocks = []

        # 포트폴리오 종목의 시장 감지 (코스피 vs 미국)
        portfolio_tickers = [s['ticker'] for s in portfolio]
        is_kospi_portfolio = any(ticker.isdigit() and len(ticker) == 6 for ticker in portfolio_tickers)

        if is_kospi_portfolio:
            # 코스피 포트폴리오: 한국 주식 추천
            logger.info("🇰🇷 코스피 포트폴리오 감지 → 한국 주식 추천")
            from src.tools.korean_stocks import KoreanStockAnalyzer
            korean_analyzer = KoreanStockAnalyzer()

            # 코스피 상위 종목 20개 가져오기
            korean_top_stocks = korean_analyzer.get_top_korean_stocks(market="kospi", limit=20)

            # 포트폴리오에 없는 종목들만 후보로
            candidate_stocks = []
            for k_stock in korean_top_stocks:
                # ticker 형식 변환: '005930.KS' → '005930'
                k_ticker = k_stock['ticker'].replace('.KS', '').replace('.KQ', '')
                if k_ticker not in portfolio_tickers:
                    candidate_stocks.append({
                        'ticker': k_ticker,
                        'company_name': k_stock['name'],
                        'current_price': k_stock.get('current_price', 0),
                        'score': 75,  # 기본 점수
                        'returns_1y': 0,
                        'volatility': 20,
                        'pe_ratio': k_stock.get('pe_ratio', 'N/A')
                    })
        else:
            # 미국 포트폴리오: 미국 주식 추천
            logger.info("🇺🇸 미국 포트폴리오 감지 → 미국 주식 추천")
            # AI 추천 종목 전체 리스트 가져오기 (top 20개)
            all_top_stocks = get_top_stocks(20)

            # 회사 이름 추가
            for stock in all_top_stocks:
                ticker = stock['ticker']
                try:
                    ticker_obj = yf.Ticker(ticker)
                    info = ticker_obj.info
                    stock['company_name'] = info.get('longName', ticker)
                except Exception as e:
                    stock['company_name'] = ticker

            # 포트폴리오에 없는 종목들만 후보로
            candidate_stocks = [s for s in all_top_stocks if s['ticker'] not in portfolio_tickers]

        if related_stocks_set and candidate_stocks:
            # 키워드를 조합하여 유사 인사이트 검색
            combined_keywords = " ".join(list(related_stocks_set)[:5])
            similar_insights = get_relevant_insights(combined_keywords, top_k=5)

            # 각 후보 종목에 대해 인사이트 검색하여 관련도 계산
            stock_scores = {}

            for stock in candidate_stocks[:10]:  # 상위 10개 종목만 검사
                ticker = stock['ticker']

                # 해당 종목의 인사이트 검색
                stock_insights = get_relevant_insights(ticker, top_k=2)

                # 유사 인사이트와의 관련도 계산
                max_similarity = 0
                best_reason = ""

                for stock_insight in stock_insights:
                    # 포트폴리오 키워드와 겹치는 키워드 찾기
                    stock_keywords = set(stock_insight.get("keywords", []))
                    common_keywords = related_stocks_set & stock_keywords

                    if common_keywords or stock_insight.get("similarity", 0) > 0.5:
                        similarity = stock_insight.get("similarity", 0)
                        if similarity > max_similarity:
                            max_similarity = similarity
                            best_reason = f"{stock_insight.get('title', '')[:50]}... ({stock_insight.get('sector', '')})"

                if max_similarity > 0:
                    # candidate_stocks에서 회사 이름 찾기
                    company_name = ticker
                    for candidate in candidate_stocks:
                        if candidate['ticker'] == ticker:
                            company_name = candidate.get('company_name', ticker)
                            break

                    stock_scores[ticker] = {
                        "symbol": ticker,
                        "company_name": company_name,
                        "reason": best_reason,
                        "similarity": max_similarity
                    }

            # 유사도 순으로 정렬하여 상위 5개 선택
            sorted_stocks = sorted(stock_scores.values(), key=lambda x: x['similarity'], reverse=True)
            related_stocks = sorted_stocks[:5]

        unique_related = related_stocks

        result = {
            "success": True,
            "total_investment": total_investment,
            "portfolio": portfolio,
            "summary": {
                "total_stocks": len(portfolio),
                "total_allocated": sum(p['actual_amount'] for p in portfolio),
                "cash_remaining": total_investment - sum(p['actual_amount'] for p in portfolio),
                "avg_expected_return": round(avg_returns, 2),
                "avg_volatility": round(avg_volatility, 2),
                "risk_level": risk_level
            },
            "market_outlook": market_outlook,  # RAG 기반 시장 전망
            "portfolio_insights": portfolio_insights,  # 포트폴리오 종목별 블로그 인사이트
            "related_stocks": unique_related,  # 유사 종목 추천
            "recommendation": f"""
🧠 **AI 블로그 분석 기반 포트폴리오**

📊 시장 전망: {market_outlook}
💡 투자 전략: {strategy_summary}

📈 예상 수익률: {avg_returns:.2f}%
📉 변동성: {avg_volatility:.2f}% ({risk_level} 리스크)
💰 총 투자 금액: {total_investment:,}원

각 종목의 비중은 최근 블로그 분석 결과를 바탕으로 AI가 지능적으로 결정했습니다.
최신 시장 동향과 감성 분석이 반영된 데이터 기반 포트폴리오입니다.
            """.strip()
        }

        # 캐시 저장 (1시간)
        cache_manager.set_cached("portfolio-suggestion", result, params=cache_params, ttl_seconds=3600)
        logger.info(f"💾 포트폴리오 제안 캐시 저장 완료 (투자금액: {total_investment:,}원, 인사이트: {len(portfolio_insights)}개)")

        return result

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"포트폴리오 제안 생성 실패: {str(e)}"
        }

@app.post("/api/portfolio-backtest")
async def backtest_portfolio(request: Dict[str, Any] = None):
    """포트폴리오 백테스팅 - 과거 성과 시뮬레이션"""
    if request is None:
        request = {}

    portfolio = request.get("portfolio", [])
    months_back = request.get("months_back", 3)

    if not portfolio:
        return {
            "success": False,
            "message": "포트폴리오 데이터가 필요합니다."
        }

    try:
        import yfinance as yf
        from datetime import datetime, timedelta
        import pandas as pd

        # 날짜 계산
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months_back * 30)

        # 각 종목의 일일 수익률 계산
        daily_returns = {}
        portfolio_values = []
        dates = []

        for stock in portfolio:
            ticker = stock['ticker']
            shares = stock['shares']

            try:
                # 한국 종목 코드 변환
                yahoo_ticker = ticker
                if ticker.isdigit() and len(ticker) == 6:
                    yahoo_ticker = f"{ticker}.KS"
                    print(f"한국 종목 변환: {ticker} → {yahoo_ticker}")

                data = yf.Ticker(yahoo_ticker).history(start=start_date, end=end_date)
                if not data.empty:
                    daily_returns[ticker] = {
                        'prices': data['Close'],
                        'shares': shares
                    }
                    print(f"✅ {ticker} 데이터 {len(data)}개 수집 완료")
                else:
                    print(f"⚠️ {ticker} 데이터 없음")
            except Exception as e:
                print(f"❌ 데이터 수집 실패 {ticker}: {e}")

        if not daily_returns:
            return {
                "success": False,
                "message": "과거 데이터를 가져올 수 없습니다."
            }

        # 공통 날짜 찾기
        common_dates = None
        for ticker_data in daily_returns.values():
            if common_dates is None:
                common_dates = ticker_data['prices'].index
            else:
                common_dates = common_dates.intersection(ticker_data['prices'].index)

        # 포트폴리오 일일 가치 계산
        for date in common_dates:
            total_value = sum(
                daily_returns[ticker]['prices'].loc[date] * daily_returns[ticker]['shares']
                for ticker in daily_returns.keys()
            )
            portfolio_values.append(total_value)
            dates.append(date.strftime('%Y-%m-%d'))

        if not portfolio_values:
            return {
                "success": False,
                "message": "포트폴리오 가치를 계산할 수 없습니다."
            }

        # 초기 투자금액
        initial_value = portfolio_values[0]
        final_value = portfolio_values[-1]
        total_return = ((final_value - initial_value) / initial_value) * 100

        # 일일 수익률 계산
        daily_pct_changes = []
        for i in range(1, len(portfolio_values)):
            pct_change = ((portfolio_values[i] - portfolio_values[i-1]) / portfolio_values[i-1]) * 100
            daily_pct_changes.append(pct_change)

        # 변동성 계산 (연환산)
        volatility = pd.Series(daily_pct_changes).std() * (252 ** 0.5)

        # 최대 낙폭 계산
        peak = portfolio_values[0]
        max_drawdown = 0
        for value in portfolio_values:
            if value > peak:
                peak = value
            drawdown = ((peak - value) / peak) * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # 샤프 비율 계산 (무위험 수익률 0% 가정)
        avg_daily_return = pd.Series(daily_pct_changes).mean()
        daily_volatility = pd.Series(daily_pct_changes).std()
        sharpe_ratio = (avg_daily_return / daily_volatility) * (252 ** 0.5) if daily_volatility > 0 else 0

        return {
            "success": True,
            "backtest_period": {
                "start_date": dates[0],
                "end_date": dates[-1],
                "months": months_back
            },
            "performance": {
                "initial_value": round(initial_value, 2),
                "final_value": round(final_value, 2),
                "total_return": round(total_return, 2),
                "volatility": round(volatility, 2),
                "max_drawdown": round(max_drawdown, 2),
                "sharpe_ratio": round(sharpe_ratio, 2)
            },
            "chart_data": {
                "dates": dates,
                "values": [round(v, 2) for v in portfolio_values],
                "returns": [round(((v - initial_value) / initial_value) * 100, 2) for v in portfolio_values]
            },
            "stocks_performance": [
                {
                    "ticker": stock['ticker'],
                    "shares": stock['shares'],
                    "initial_price": round(daily_returns[stock['ticker']]['prices'].iloc[0], 2),
                    "final_price": round(daily_returns[stock['ticker']]['prices'].iloc[-1], 2),
                    "return": round(
                        ((daily_returns[stock['ticker']]['prices'].iloc[-1] -
                          daily_returns[stock['ticker']]['prices'].iloc[0]) /
                         daily_returns[stock['ticker']]['prices'].iloc[0]) * 100, 2
                    )
                }
                for stock in portfolio if stock['ticker'] in daily_returns
            ]
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"백테스팅 실패: {str(e)}"
        }

@app.post("/api/save-history")
async def save_history(request: Dict[str, Any], current_user: Dict[str, Any] = Depends(verify_token)):
    """거래 히스토리 저장 (인증 필요)"""
    try:
        user_id = current_user["user_id"]
        history_item = {
            "id": len(trade_history) + 1,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "type": request.get("type"),  # "screening", "portfolio", "analysis", "trade"
            "data": request.get("data"),
            "result": request.get("result")
        }
        trade_history.append(history_item)
        return {"success": True, "id": history_item["id"]}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/history")
async def get_history(current_user: Dict[str, Any] = Depends(verify_token)):
    """거래 히스토리 조회 (인증 필요)"""
    try:
        user_id = current_user["user_id"]
        # 사용자별 히스토리 필터링
        user_history = [h for h in trade_history if h.get("user_id") == user_id]
        # 최신순으로 정렬
        sorted_history = sorted(user_history, key=lambda x: x["timestamp"], reverse=True)
        return {
            "success": True,
            "history": sorted_history,
            "total": len(sorted_history)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "history": []
        }

@app.delete("/api/history/{history_id}")
async def delete_history(history_id: int, current_user: Dict[str, Any] = Depends(verify_token)):
    """특정 히스토리 삭제 (인증 필요)"""
    global trade_history
    try:
        user_id = current_user["user_id"]
        # 본인의 히스토리만 삭제 가능
        trade_history = [h for h in trade_history if not (h["id"] == history_id and h.get("user_id") == user_id)]
        return {"success": True, "message": "삭제되었습니다"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== 경제지표 및 뉴스 API ====================
from typing import Optional

try:
    from src.tools.economic_indicators import get_economic_indicators, get_market_condition
    from src.tools.news_aggregator import get_recent_news, analyze_news_sentiment
    MACRO_FEATURES_AVAILABLE = True
except ImportError:
    MACRO_FEATURES_AVAILABLE = False
    print("⚠️ 경제지표 및 뉴스 모듈을 불러올 수 없습니다. /api/economic-indicators 등의 엔드포인트가 작동하지 않습니다.")


@app.get("/api/economic-indicators")
async def get_economic_indicators_api(country: Optional[str] = None):
    """경제지표 조회
    
    Args:
        country: "US" 또는 "KR" (없으면 전체)
    """
    if not MACRO_FEATURES_AVAILABLE:
        raise HTTPException(status_code=503, detail="경제지표 기능을 사용할 수 없습니다")
    
    try:
        indicators = get_economic_indicators(country)
        return {
            "success": True,
            "count": len(indicators),
            "indicators": [ind.model_dump() for ind in indicators]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"경제지표 조회 실패: {str(e)}")


@app.get("/api/market-condition")
async def get_market_condition_api():
    """시장 상황 분석"""
    if not MACRO_FEATURES_AVAILABLE:
        raise HTTPException(status_code=503, detail="시장 상황 분석 기능을 사용할 수 없습니다")
    
    try:
        condition = get_market_condition()
        return {
            "success": True,
            "condition": condition.model_dump()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시장 상황 분석 실패: {str(e)}")


@app.get("/api/news")
async def get_news_api(
    categories: Optional[str] = None,
    days: int = 7,
    limit: int = 50,
    symbol: Optional[str] = None
):
    """최근 뉴스 조회 (30분 캐싱)

    Args:
        categories: 쉼표로 구분된 카테고리 (예: "미국경제,한국경제")
        days: 최근 며칠간의 뉴스
        limit: 최대 뉴스 개수
        symbol: 종목 심볼 (특정 종목 관련 뉴스 검색)
    """
    # 캐시 조회 (symbol/categories + days + limit로 30분 캐싱)
    cache_params = {"symbol": symbol or "", "categories": categories or "", "days": days, "limit": limit}
    cached = cache_manager.get_cached("news", params=cache_params, ttl_seconds=1800)
    if cached:
        logger.info(f"✅ 캐시에서 뉴스 반환 (symbol={symbol}, categories={categories})")
        return cached

    if not MACRO_FEATURES_AVAILABLE:
        # 종목별 뉴스는 Google News RSS 사용하므로 MACRO_FEATURES 없어도 가능
        if symbol:
            try:
                import feedparser
                import yfinance as yf

                # 회사명 가져오기
                yahoo_symbol = symbol
                if symbol.isdigit() and len(symbol) == 6:
                    yahoo_symbol = f"{symbol}.KS"

                ticker = yf.Ticker(yahoo_symbol)
                info = ticker.info
                company_name = info.get('longName', symbol)

                # Google News RSS로 종목 관련 뉴스 검색
                search_query = f"{symbol}+OR+{company_name.replace(' ', '+')}"
                rss_url = f"https://news.google.com/rss/search?q={search_query}&hl=en-US&gl=US&ceid=US:en"

                feed = feedparser.parse(rss_url)
                news_list = []

                for entry in feed.entries[:limit]:
                    published = entry.get("published_parsed")
                    if published:
                        pub_date = datetime(*published[:6])
                        pub_date_str = pub_date.strftime('%Y-%m-%d %H:%M')
                    else:
                        pub_date_str = datetime.now().strftime('%Y-%m-%d %H:%M')

                    news_list.append({
                        "title": entry.get("title", ""),
                        "description": entry.get("summary", "")[:200],
                        "url": entry.get("link", ""),
                        "source": entry.get("source", {}).get("title", "Google News") if hasattr(entry.get("source", {}), "__getitem__") else "Google News",
                        "published_at": pub_date_str,
                        "category": "stock"
                    })

                result = {
                    "success": True,
                    "count": len(news_list),
                    "news": news_list,
                    "symbol": symbol,
                    "company_name": company_name
                }

                # 캐시 저장 (30분)
                cache_manager.set_cached("news", result, params=cache_params, ttl_seconds=1800)
                logger.info(f"💾 {symbol} 뉴스 캐시 저장 완료")

                return result
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "news": [],
                    "message": f"종목 뉴스 조회 실패: {str(e)}"
                }
        else:
            raise HTTPException(status_code=503, detail="뉴스 기능을 사용할 수 없습니다")

    try:
        # 종목별 뉴스 검색
        if symbol:
            import feedparser
            import yfinance as yf

            # 회사명 가져오기
            yahoo_symbol = symbol
            if symbol.isdigit() and len(symbol) == 6:
                yahoo_symbol = f"{symbol}.KS"

            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info
            company_name = info.get('longName', symbol)

            # Google News RSS로 종목 관련 뉴스 검색
            search_query = f"{symbol}+OR+{company_name.replace(' ', '+')}"
            rss_url = f"https://news.google.com/rss/search?q={search_query}&hl=en-US&gl=US&ceid=US:en"

            feed = feedparser.parse(rss_url)
            news_list = []

            for entry in feed.entries[:limit]:
                published = entry.get("published_parsed")
                if published:
                    pub_date = datetime(*published[:6])
                    pub_date_str = pub_date.strftime('%Y-%m-%d %H:%M')
                else:
                    pub_date_str = datetime.now().strftime('%Y-%m-%d %H:%M')

                news_list.append({
                    "title": entry.get("title", ""),
                    "description": entry.get("summary", "")[:200],
                    "url": entry.get("link", ""),
                    "source": entry.get("source", {}).get("title", "Google News") if hasattr(entry.get("source", {}), "__getitem__") else "Google News",
                    "published_at": pub_date_str,
                    "category": "stock"
                })

            result = {
                "success": True,
                "count": len(news_list),
                "news": news_list,
                "symbol": symbol,
                "company_name": company_name
            }

            # 캐시 저장 (30분)
            cache_manager.set_cached("news", result, params=cache_params, ttl_seconds=1800)
            logger.info(f"💾 {symbol} 뉴스 캐시 저장 완료")

            return result

        # 일반 뉴스 (기존 로직)
        category_list = None
        if categories:
            category_list = [c.strip() for c in categories.split(",")]

        news_list = get_recent_news(category_list, days, limit)
        sentiment = analyze_news_sentiment(news_list)

        result = {
            "success": True,
            "count": len(news_list),
            "news": [news.model_dump() for news in news_list],
            "sentiment": sentiment
        }

        # 캐시 저장 (30분)
        cache_manager.set_cached("news", result, params=cache_params, ttl_seconds=1800)
        logger.info(f"💾 일반 뉴스 캐시 저장 완료 (categories={categories})")

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"뉴스 조회 실패: {str(e)}")


@app.get("/api/macro-dashboard")
async def get_macro_dashboard():
    """거시경제 대시보드 데이터 통합 조회"""
    if not MACRO_FEATURES_AVAILABLE:
        raise HTTPException(status_code=503, detail="거시경제 대시보드 기능을 사용할 수 없습니다")
    
    try:
        # 병렬로 데이터 수집
        us_indicators = get_economic_indicators("US")
        kr_indicators = get_economic_indicators("KR")
        market_condition = get_market_condition()
        recent_news = get_recent_news(days=3, limit=20)
        news_sentiment = analyze_news_sentiment(recent_news)
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "market_condition": market_condition.model_dump(),
            "indicators": {
                "us": [ind.model_dump() for ind in us_indicators],
                "kr": [ind.model_dump() for ind in kr_indicators]
            },
            "news": {
                "articles": [news.model_dump() for news in recent_news[:10]],
                "sentiment": news_sentiment
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"대시보드 데이터 조회 실패: {str(e)}")


# ==================== 트렌딩 종목 API ====================
try:
    from src.tools.trending_analyzer import get_trending_stocks, get_trending_analysis
    TRENDING_FEATURES_AVAILABLE = True
except ImportError:
    TRENDING_FEATURES_AVAILABLE = False
    print("⚠️ 트렌딩 종목 모듈을 불러올 수 없습니다. /api/trending-stocks 엔드포인트가 작동하지 않습니다.")


@app.get("/api/historical-prices")
async def get_historical_prices(symbol: str, period: str = "3m"):
    """종목의 과거 가격 데이터 조회 (1시간 캐싱)

    Args:
        symbol: 종목 심볼
        period: 기간 (1m, 3m, 6m, 1y)

    Returns:
        날짜별 가격 데이터
    """
    # 캐시 조회 (symbol + period로 1시간 캐싱)
    cached = cache_manager.get_cached("historical-prices", params={"symbol": symbol, "period": period}, ttl_seconds=3600)
    if cached:
        logger.info(f"✅ 캐시에서 {symbol} ({period}) 가격 데이터 반환")
        return cached

    try:
        import yfinance as yf
        from datetime import datetime, timedelta

        logger.info(f"🔄 {symbol} ({period}) 가격 데이터 새로 계산 중...")

        # 한국 종목 코드 변환
        yahoo_symbol = symbol
        if symbol.isdigit() and len(symbol) == 6:
            yahoo_symbol = f"{symbol}.KS"

        # 기간별 일수 매핑
        period_days = {
            '1m': 30,
            '3m': 90,
            '6m': 180,
            '1y': 365
        }

        days = period_days.get(period, 90)

        # 과거 데이터 가져오기
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days + 10)  # 여유 있게

        ticker = yf.Ticker(yahoo_symbol)
        hist = ticker.history(start=start_date, end=end_date)

        if hist.empty:
            return {
                "success": False,
                "message": f"{symbol} 과거 데이터를 가져올 수 없습니다."
            }

        # 데이터 포맷팅
        dates = []
        prices = []

        for date, row in hist.iterrows():
            dates.append(date.strftime('%Y-%m-%d'))
            prices.append(round(row['Close'], 2))

        result = {
            "success": True,
            "symbol": symbol,
            "period": period,
            "count": len(dates),
            "dates": dates,
            "prices": prices,
            "current_price": prices[-1] if prices else 0,
            "start_price": prices[0] if prices else 0,
            "change_percent": round(((prices[-1] - prices[0]) / prices[0] * 100), 2) if prices else 0
        }

        # 캐시 저장 (1시간)
        cache_manager.set_cached("historical-prices", result, params={"symbol": symbol, "period": period}, ttl_seconds=3600)
        logger.info(f"💾 {symbol} ({period}) 가격 데이터 캐시 저장 완료")

        return result

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"가격 데이터 조회 실패: {str(e)}"
        }


@app.get("/api/trending-stocks")
async def get_trending_stocks_api(min_score: int = 50, top_n: int = 15):
    """트렌딩 종목 리스트 조회

    Args:
        min_score: 최소 트렌딩 점수 (기본값: 50)
        top_n: 상위 N개 종목 (기본값: 15)

    Returns:
        트렌딩 종목 리스트 (테마별 분류)
    """
    if not TRENDING_FEATURES_AVAILABLE:
        raise HTTPException(status_code=503, detail="트렌딩 종목 기능을 사용할 수 없습니다")

    try:
        trending_stocks = get_trending_stocks(min_score=min_score, top_n=top_n)

        # 테마별 분류
        themes = {}
        for stock in trending_stocks:
            theme = stock['theme']
            if theme not in themes:
                themes[theme] = []
            themes[theme].append(stock)

        return {
            "success": True,
            "count": len(trending_stocks),
            "stocks": trending_stocks,
            "themes": {theme: len(stocks) for theme, stocks in themes.items()},
            "generated_at": datetime.now().isoformat(),
            "message": "뉴스 및 시장 동향 기반 고위험 고수익 트렌딩 종목입니다."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"트렌딩 종목 조회 실패: {str(e)}")


@app.post("/api/trending-analysis")
async def get_trending_analysis_api(request: Dict[str, Any]):
    """트렌딩 종목 상세 분석

    Args:
        symbol: 종목 심볼 (예: "IONQ", "RGTI")

    Returns:
        종목별 상세 분석 (가격 변화, 트렌딩 이유, 관련 뉴스, 리스크 요소)
    """
    if not TRENDING_FEATURES_AVAILABLE:
        raise HTTPException(status_code=503, detail="트렌딩 종목 기능을 사용할 수 없습니다")

    symbol = request.get("symbol", "")

    if not symbol:
        raise HTTPException(status_code=400, detail="symbol 파라미터가 필요합니다")

    try:
        analysis = get_trending_analysis(symbol)

        if not analysis.get('success'):
            raise HTTPException(status_code=404, detail=f"{symbol} 분석 데이터를 가져올 수 없습니다")

        return analysis
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"트렌딩 종목 분석 실패: {str(e)}")


# ==================== 사용자별 포트폴리오 관리 API ====================

class PortfolioCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    initial_capital: float

class PortfolioPositionRequest(BaseModel):
    portfolio_id: str
    symbol: str
    shares: float
    avg_price: float

@app.get("/api/user/portfolios")
async def get_user_portfolios(current_user: Dict[str, Any] = Depends(verify_token)):
    """사용자 포트폴리오 목록 조회"""
    try:
        user_id = current_user["user_id"]

        # Supabase에서 사용자 포트폴리오 조회
        result = supabase.table("user_portfolios").select("*").eq("user_id", user_id).execute()

        return {
            "success": True,
            "portfolios": result.data,
            "count": len(result.data)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "portfolios": []
        }

@app.post("/api/user/portfolio")
async def create_user_portfolio(request: PortfolioCreateRequest, current_user: Dict[str, Any] = Depends(verify_token)):
    """사용자 포트폴리오 생성"""
    try:
        user_id = current_user["user_id"]

        # Supabase에 포트폴리오 삽입
        result = supabase.table("user_portfolios").insert({
            "user_id": user_id,
            "name": request.name,
            "description": request.description,
            "initial_capital": request.initial_capital
        }).execute()

        return {
            "success": True,
            "portfolio": result.data[0] if result.data else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/user/portfolio/{portfolio_id}")
async def get_user_portfolio(portfolio_id: str, current_user: Dict[str, Any] = Depends(verify_token)):
    """특정 포트폴리오 상세 조회"""
    try:
        user_id = current_user["user_id"]

        # 포트폴리오 기본 정보
        portfolio_result = supabase.table("user_portfolios").select("*").eq("id", portfolio_id).eq("user_id", user_id).single().execute()

        # 포트폴리오 포지션
        positions_result = supabase.table("portfolio_positions").select("*").eq("portfolio_id", portfolio_id).execute()

        return {
            "success": True,
            "portfolio": portfolio_result.data,
            "positions": positions_result.data
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/user/portfolio/{portfolio_id}/position")
async def add_portfolio_position(portfolio_id: str, request: PortfolioPositionRequest, current_user: Dict[str, Any] = Depends(verify_token)):
    """포트폴리오에 포지션 추가"""
    try:
        user_id = current_user["user_id"]

        # 포트폴리오 소유권 확인
        portfolio_result = supabase.table("user_portfolios").select("id").eq("id", portfolio_id).eq("user_id", user_id).single().execute()

        if not portfolio_result.data:
            raise HTTPException(status_code=403, detail="권한이 없습니다")

        # 포지션 추가
        result = supabase.table("portfolio_positions").insert({
            "portfolio_id": portfolio_id,
            "symbol": request.symbol,
            "shares": request.shares,
            "avg_price": request.avg_price
        }).execute()

        return {
            "success": True,
            "position": result.data[0] if result.data else None
        }
    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/user/selections")
async def save_user_selection(request: Dict[str, Any], current_user: Dict[str, Any] = Depends(verify_token)):
    """사용자 종목 선택 기록 저장"""
    try:
        user_id = current_user["user_id"]

        result = supabase.table("user_selections").insert({
            "user_id": user_id,
            "symbol": request.get("symbol"),
            "context": request.get("context"),
            "action": request.get("action", "view")
        }).execute()

        return {
            "success": True,
            "selection": result.data[0] if result.data else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/user/selections")
async def get_user_selections(current_user: Dict[str, Any] = Depends(verify_token)):
    """사용자 종목 선택 이력 조회"""
    try:
        user_id = current_user["user_id"]

        result = supabase.table("user_selections").select("*").eq("user_id", user_id).order("selected_at", desc=True).limit(50).execute()

        return {
            "success": True,
            "selections": result.data,
            "count": len(result.data)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "selections": []
        }

@app.post("/api/user/ai-analysis")
async def save_user_ai_analysis(request: Dict[str, Any], current_user: Dict[str, Any] = Depends(verify_token)):
    """사용자별 AI 분석 결과 저장"""
    try:
        user_id = current_user["user_id"]

        result = supabase.table("user_ai_analyses").insert({
            "user_id": user_id,
            "symbol": request.get("symbol"),
            "analysis_text": request.get("analysis_text"),
            "recommendation": request.get("recommendation"),
            "confidence_score": request.get("confidence_score")
        }).execute()

        return {
            "success": True,
            "analysis": result.data[0] if result.data else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/user/ai-analyses")
async def get_user_ai_analyses(symbol: Optional[str] = None, current_user: Dict[str, Any] = Depends(verify_token)):
    """사용자 AI 분석 이력 조회"""
    try:
        user_id = current_user["user_id"]

        query = supabase.table("user_ai_analyses").select("*").eq("user_id", user_id)

        if symbol:
            query = query.eq("symbol", symbol)

        result = query.order("created_at", desc=True).limit(50).execute()

        return {
            "success": True,
            "analyses": result.data,
            "count": len(result.data)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "analyses": []
        }


# ==================== 즐겨찾기 API ====================

@app.post("/api/rag-search")
async def rag_search(request: Dict[str, Any]):
    """RAG 기반 투자 인사이트 검색 (1시간 캐싱)

    Args:
        query: 검색 쿼리 (예: "삼성전자", "HBM", "AI 반도체")
        top_k: 상위 K개 결과 (기본값: 5)

    Returns:
        관련 블로그 인사이트 리스트
    """
    try:
        query = request.get("query", "")
        top_k = request.get("top_k", 5)

        if not query or not query.strip():
            return {
                "success": False,
                "message": "검색어를 입력해주세요."
            }

        # 캐시 조회 (query + top_k로 1시간 캐싱)
        cache_params = {"query": query, "top_k": top_k}
        cached = cache_manager.get_cached("rag-search", params=cache_params, ttl_seconds=3600)
        if cached:
            logger.info(f"✅ 캐시에서 RAG 검색 반환 (query={query}, top_k={top_k})")
            return cached

        logger.info(f"🔄 RAG 검색 새로 계산 중 (query={query}, top_k={top_k})")

        # Supabase RAG 검색
        insights = get_relevant_insights(query, top_k=top_k)

        if not insights:
            result = {
                "success": True,
                "query": query,
                "insights": [],
                "count": 0,
                "message": f"'{query}'에 대한 검색 결과가 없습니다."
            }

            # 캐시 저장 (1시간)
            cache_manager.set_cached("rag-search", result, params=cache_params, ttl_seconds=3600)
            logger.info(f"💾 RAG 검색 결과 없음 캐시 저장 완료 (query={query})")

            return result

        result = {
            "success": True,
            "query": query,
            "insights": insights,
            "count": len(insights),
            "message": f"'{query}'에 대한 {len(insights)}개의 인사이트를 찾았습니다."
        }

        # 캐시 저장 (1시간)
        cache_manager.set_cached("rag-search", result, params=cache_params, ttl_seconds=3600)
        logger.info(f"💾 RAG 검색 캐시 저장 완료 (query={query}, {len(insights)}개 인사이트)")

        return result
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"검색 실패: {str(e)}"
        }


@app.post("/api/user/favorites")
async def add_favorite(request: Dict[str, Any], current_user: Dict[str, Any] = Depends(verify_token)):
    """즐겨찾기에 종목 추가

    Args:
        symbol: 종목 심볼

    Returns:
        추가된 즐겨찾기 정보
    """
    try:
        user_id = current_user["user_id"]
        symbol = request.get("symbol")

        if not symbol:
            raise HTTPException(status_code=400, detail="symbol이 필요합니다")

        # 이미 즐겨찾기에 있는지 확인 (admin 클라이언트 사용)
        if not supabase_admin:
            raise HTTPException(status_code=500, detail="관리자 권한이 설정되지 않았습니다")

        existing = supabase_admin.table("user_favorites").select("*").eq("user_id", user_id).eq("symbol", symbol).execute()

        if existing.data:
            # 이미 있어도 캐시 무효화 (UI 동기화를 위해)
            cache_manager.invalidate_cache("favorites", {"user_id": user_id})
            logger.info(f"🗑️ 사용자 {user_id[:8]}의 즐겨찾기 캐시 무효화 (이미 존재: {symbol})")
            return {
                "success": True,
                "message": "이미 즐겨찾기에 추가되어 있습니다",
                "favorite": existing.data[0]
            }

        # 즐겨찾기 추가 (admin 클라이언트로 RLS 우회)
        result = supabase_admin.table("user_favorites").insert({
            "user_id": user_id,
            "symbol": symbol
        }).execute()

        # 캐시 무효화 (즐겨찾기 목록이 변경되었으므로)
        cache_manager.invalidate_cache("favorites", {"user_id": user_id})
        logger.info(f"🗑️ 사용자 {user_id[:8]}의 즐겨찾기 캐시 무효화 (추가: {symbol})")

        return {
            "success": True,
            "message": "즐겨찾기에 추가되었습니다",
            "favorite": result.data[0] if result.data else None
        }
    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"즐겨찾기 추가 실패: {str(e)}"
        }


@app.delete("/api/user/favorites/{symbol}")
async def remove_favorite(symbol: str, current_user: Dict[str, Any] = Depends(verify_token)):
    """즐겨찾기에서 종목 제거

    Args:
        symbol: 종목 심볼

    Returns:
        삭제 결과
    """
    try:
        user_id = current_user["user_id"]

        # 즐겨찾기 삭제 (admin 클라이언트로 RLS 우회)
        if not supabase_admin:
            raise HTTPException(status_code=500, detail="관리자 권한이 설정되지 않았습니다")

        result = supabase_admin.table("user_favorites").delete().eq("user_id", user_id).eq("symbol", symbol).execute()

        # 캐시 무효화 (즐겨찾기 목록이 변경되었으므로)
        cache_manager.invalidate_cache("favorites", {"user_id": user_id})
        logger.info(f"🗑️ 사용자 {user_id[:8]}의 즐겨찾기 캐시 무효화 (삭제: {symbol})")

        return {
            "success": True,
            "message": "즐겨찾기에서 제거되었습니다"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"즐겨찾기 제거 실패: {str(e)}"
        }


@app.get("/api/blog-update-info")
async def get_blog_update_info():
    """블로그 최신 업데이트 시간 조회

    Returns:
        최근 블로그 글 날짜 및 전체 데이터 수
    """
    try:
        # Supabase에서 최신 블로그 날짜 조회
        response = supabase_rag.client.table('investment_insights') \
            .select('date') \
            .order('date', desc=True) \
            .limit(1) \
            .execute()

        # 전체 데이터 수 조회
        count_response = supabase_rag.client.table('investment_insights') \
            .select('id', count='exact') \
            .execute()

        if response.data and len(response.data) > 0:
            latest_date = response.data[0]['date']
            total_count = count_response.count if hasattr(count_response, 'count') else len(count_response.data)

            # 날짜를 한국어 형식으로 변환 (YYYY-MM-DD HH:MM)
            from datetime import datetime
            try:
                date_obj = datetime.strptime(latest_date, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%Y년 %m월 %d일')
            except:
                formatted_date = latest_date

            return {
                "success": True,
                "latest_date": latest_date,
                "formatted_date": formatted_date,
                "total_insights": total_count,
                "message": f"마지막 업데이트: {formatted_date}"
            }
        else:
            return {
                "success": False,
                "message": "데이터가 없습니다"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"업데이트 정보 조회 실패: {str(e)}"
        }


@app.get("/api/user/favorites")
async def get_favorites(current_user: Dict[str, Any] = Depends(verify_token)):
    """사용자 즐겨찾기 목록 조회 (30분 캐싱)

    Returns:
        즐겨찾기 종목 리스트 (종목 정보 포함)
    """
    try:
        user_id = current_user["user_id"]

        # 캐시 조회 (사용자별 30분 캐싱)
        cached = cache_manager.get_cached("favorites", params={"user_id": user_id}, ttl_seconds=1800)
        if cached:
            logger.info(f"✅ 캐시에서 사용자 {user_id[:8]}의 즐겨찾기 반환")
            return cached

        logger.info(f"🔄 사용자 {user_id[:8]}의 즐겨찾기 새로 조회 중...")

        # 즐겨찾기 목록 조회 (admin 클라이언트로 RLS 우회)
        if not supabase_admin:
            raise HTTPException(status_code=500, detail="관리자 권한이 설정되지 않았습니다")

        result = supabase_admin.table("user_favorites").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()

        logger.info(f"📊 조회 결과: {len(result.data)}개 종목 발견")

        # 각 종목의 실시간 정보 추가
        favorites_with_info = []

        for favorite in result.data:
            symbol = favorite['symbol']

            try:
                import yfinance as yf
                from src.tools.yahoo_finance import yahoo_analyzer

                # 한국 종목 코드 변환
                yahoo_symbol = symbol
                if symbol.isdigit() and len(symbol) == 6:
                    yahoo_symbol = f"{symbol}.KS"

                # 종목 정보 가져오기
                metrics = yahoo_analyzer.calculate_financial_metrics(yahoo_symbol)
                ticker = yf.Ticker(yahoo_symbol)
                info = ticker.info

                if metrics:
                    favorites_with_info.append({
                        "symbol": symbol,
                        "company_name": info.get('longName', symbol),
                        "current_price": metrics.get('current_price', 0),
                        "change_percent": metrics.get('change_percent', 0),
                        "volume": metrics.get('volume', 0),
                        "market_cap": metrics.get('market_cap', 0),
                        "score": metrics.get('score', 0),
                        "returns_1y": metrics.get('returns_1y', 0),
                        "volatility": metrics.get('volatility', 0),
                        "pe_ratio": metrics.get('pe_ratio', 'N/A'),
                        "created_at": favorite.get('created_at', '')
                    })
            except Exception as e:
                print(f"종목 {symbol} 정보 가져오기 실패: {e}")
                # 실패해도 기본 정보는 유지
                favorites_with_info.append({
                    "symbol": symbol,
                    "company_name": symbol,
                    "current_price": 0,
                    "created_at": favorite.get('created_at', ''),
                    "error": str(e)
                })

        response = {
            "success": True,
            "favorites": favorites_with_info,
            "count": len(favorites_with_info)
        }

        # 캐시 저장 (30분)
        cache_manager.set_cached("favorites", response, params={"user_id": user_id}, ttl_seconds=1800)
        logger.info(f"💾 사용자 {user_id[:8]}의 즐겨찾기 캐시 저장 완료")

        return response
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "favorites": [],
            "message": f"즐겨찾기 조회 실패: {str(e)}"
        }


@app.get("/api/recommendation-reason")
async def get_recommendation_reason(symbol: str):
    """AI가 종목을 추천한 이유 상세 분석

    Args:
        symbol: 종목 심볼

    Returns:
        추천 이유, 블로그 인사이트, 가격 변동 분석
    """
    try:
        import yfinance as yf
        from datetime import datetime, timedelta

        logger.info(f"🔍 {symbol} AI 추천 이유 분석 시작...")

        # 1. 종목 기본 정보 가져오기
        yahoo_symbol = symbol
        if symbol.isdigit() and len(symbol) == 6:
            yahoo_symbol = f"{symbol}.KS"

        ticker = yf.Ticker(yahoo_symbol)
        info = ticker.info
        company_name = info.get('longName', symbol)
        sector = info.get('sector', '정보 없음')

        # 2. 블로그 인사이트 조회 (상위 5개)
        insights = get_relevant_insights(symbol, top_k=5)

        # 3. 각 인사이트의 날짜와 그 이후 가격 변동 분석
        insight_analysis = []

        for insight in insights:
            try:
                # 인사이트 날짜 파싱 (여러 형식 지원)
                insight_date_str = insight.get('date', '')

                # 다양한 날짜 형식 시도
                date_formats = [
                    '%Y-%m-%d',  # 2023-06-08
                    '%Y. %m. %d. %H:%M',  # 2023. 6. 8. 0:10
                    '%Y-%m-%d %H:%M:%S'  # 2023-06-08 00:10:00
                ]

                insight_date = None
                for fmt in date_formats:
                    try:
                        insight_date = datetime.strptime(insight_date_str, fmt)
                        break
                    except ValueError:
                        continue

                if insight_date is None:
                    logger.warning(f"날짜 파싱 실패 (형식 불일치): {insight_date_str}")
                    continue

                # 그 날짜의 가격과 현재 가격 비교
                start_date = insight_date
                end_date = datetime.now()

                hist = ticker.history(start=start_date, end=end_date)

                if not hist.empty:
                    past_price = hist['Close'].iloc[0]
                    current_price = hist['Close'].iloc[-1]
                    price_change = ((current_price - past_price) / past_price) * 100

                    insight_analysis.append({
                        "title": insight.get('title', ''),
                        "date": insight_date_str,
                        "content_preview": insight.get('content', '')[:200] + "...",
                        "past_price": round(past_price, 2),
                        "current_price": round(current_price, 2),
                        "price_change_pct": round(price_change, 2),
                        "similarity": insight.get('similarity', 0),
                        "keywords": insight.get('keywords', [])[:5],
                        "sector": insight.get('sector', ''),
                        "url": insight.get('url', '')
                    })
            except Exception as e:
                logger.warning(f"인사이트 분석 실패: {e}")
                continue

        # 4. 섹터 관련 종목들 가격 변동 (간단하게 S&P 500 상위 종목 중 같은 섹터만)
        sector_stocks = []

        if sector != '정보 없음':
            # AI 추천 종목 리스트에서 같은 섹터 찾기
            try:
                from src.tools.yahoo_finance import get_top_stocks
                top_stocks = get_top_stocks(20)

                for stock in top_stocks[:10]:  # 상위 10개만
                    if stock['ticker'] == symbol:
                        continue

                    try:
                        stock_ticker = yf.Ticker(stock['ticker'])
                        stock_info = stock_ticker.info
                        stock_sector = stock_info.get('sector', '')

                        if stock_sector == sector:
                            # 최근 3개월 수익률
                            hist_3m = stock_ticker.history(period="3mo")
                            if not hist_3m.empty:
                                start_price = hist_3m['Close'].iloc[0]
                                end_price = hist_3m['Close'].iloc[-1]
                                returns_3m = ((end_price - start_price) / start_price) * 100

                                sector_stocks.append({
                                    "symbol": stock['ticker'],
                                    "company_name": stock_info.get('longName', stock['ticker']),
                                    "returns_3m": round(returns_3m, 2)
                                })
                    except Exception as e:
                        logger.warning(f"{stock['ticker']} 섹터 분석 실패: {e}")
                        continue
            except Exception as e:
                logger.warning(f"섹터 종목 분석 실패: {e}")

        # 5. 추천 이유 요약 생성
        recommendation_summary = f"""
**{company_name} ({symbol})**을 AI가 추천한 이유입니다.

### 📊 섹터 및 기본 정보
- **섹터**: {sector}
- **분석된 블로그 인사이트**: {len(insight_analysis)}개

### 💡 블로그 인사이트 기반 분석
"""

        if insight_analysis:
            avg_price_change = sum(i['price_change_pct'] for i in insight_analysis) / len(insight_analysis)
            recommendation_summary += f"\n블로그 글 작성 이후 평균 가격 변동: **{avg_price_change:+.2f}%**\n\n"

            if avg_price_change > 10:
                recommendation_summary += "✅ 블로그에서 언급된 이후 **강한 상승세**를 보이고 있습니다.\n\n"
            elif avg_price_change > 0:
                recommendation_summary += "📈 블로그에서 언급된 이후 **긍정적인 성과**를 보이고 있습니다.\n\n"
            else:
                recommendation_summary += "📉 블로그 언급 이후 **가격 조정** 단계에 있으나, 장기 전망은 긍정적입니다.\n\n"
        else:
            recommendation_summary += "\n⚠️ 관련 블로그 인사이트가 충분하지 않습니다. 기술적 분석을 기반으로 추천되었습니다.\n\n"

        # 6. 섹터 동향 분석
        if sector_stocks:
            avg_sector_returns = sum(s['returns_3m'] for s in sector_stocks) / len(sector_stocks)
            recommendation_summary += f"""
### 🏭 {sector} 섹터 동향
- **섹터 평균 3개월 수익률**: {avg_sector_returns:+.2f}%
- **분석된 동종 업계 종목**: {len(sector_stocks)}개

"""
            if avg_sector_returns > 5:
                recommendation_summary += "🔥 섹터 전체가 강한 상승세를 보이고 있어 **긍정적인 시장 환경**입니다.\n\n"
            elif avg_sector_returns > 0:
                recommendation_summary += "📊 섹터가 **안정적인 성장**을 보이고 있습니다.\n\n"
            else:
                recommendation_summary += "⚠️ 섹터가 일시적인 조정 중이나, **선별적 투자 기회**가 있습니다.\n\n"

        recommendation_summary += """
### 🎯 종합 추천 이유
AI는 다음 요소들을 종합적으로 고려하여 이 종목을 추천했습니다:
1. 최근 블로그 인사이트에서 긍정적인 언급
2. 과거 언급 이후의 실제 가격 성과
3. 섹터 전반의 동향 및 시장 환경
4. 기술적 지표 및 수익률 분석

**이 종목은 데이터 기반으로 선별된 투자 기회입니다.**
"""

        return {
            "success": True,
            "symbol": symbol,
            "company_name": company_name,
            "sector": sector,
            "insights_count": len(insight_analysis),
            "insights": insight_analysis,
            "sector_stocks": sector_stocks,
            "recommendation_summary": recommendation_summary.strip()
        }

    except Exception as e:
        logger.error(f"❌ AI 추천 이유 분석 실패: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"AI 추천 이유 분석 실패: {str(e)}"
        }


@app.post("/api/asset-allocation")
async def get_asset_allocation(request: Dict[str, Any] = None):
    """
    총체적 자산 배분 제안 API (매크로 경제, 환율, 지정학적 리스크 종합 분석)

    Args:
        request: {
            "investment_amount": 투자 금액 (기본 1억원),
            "risk_tolerance": 리스크 허용도 (낮음/보통/높음, 기본 보통)
        }

    Returns:
        자산 배분 추천, 시장 환경 분석, 리스크 평가
    """
    if request is None:
        request = {}

    # 캐시 조회 (investment_amount + risk_tolerance로 1시간 캐싱)
    investment_amount = request.get("investment_amount", 100000000)
    risk_tolerance = request.get("risk_tolerance", "보통")
    cache_params = {"investment_amount": investment_amount, "risk_tolerance": risk_tolerance}
    cached = cache_manager.get_cached("asset-allocation", params=cache_params, ttl_seconds=3600)
    if cached:
        logger.info(f"✅ 캐시에서 자산 배분 제안 반환 (투자금액: {investment_amount:,}원, 리스크: {risk_tolerance})")
        return cached

    try:
        from src.agents.asset_allocation_agent import get_asset_allocation_agent
        from src.tools.forex_data import analyze_forex_market
        from src.tools.news_aggregator import analyze_geopolitical_risks

        logger.info(f"🔄 자산 배분 제안 새로 계산 중 (투자금액: {investment_amount:,}원, 리스크: {risk_tolerance})")

        # 자산 배분 에이전트 실행
        agent = get_asset_allocation_agent()
        recommendation = agent.generate_asset_allocation(
            investment_amount=investment_amount,
            risk_tolerance=risk_tolerance
        )

        if not recommendation:
            return {
                "success": False,
                "message": "자산 배분 제안을 생성할 수 없습니다."
            }

        # 환율 시장 분석 추가
        forex_analysis = analyze_forex_market()

        # 지정학적 리스크 추가
        geo_risk = analyze_geopolitical_risks(days=7)

        # 요약 정보 생성
        summary = agent.get_allocation_summary(recommendation)

        result = {
            "success": True,
            "investment_amount": investment_amount,
            "risk_tolerance": risk_tolerance,
            "recommendation": {
                "allocations": [
                    {
                        "asset_class": alloc.asset_class,
                        "allocation_percent": alloc.allocation_percent,
                        "reasoning": alloc.reasoning,
                        "instruments": alloc.instruments,
                        "risk_level": alloc.risk_level
                    }
                    for alloc in recommendation.allocations
                ],
                "total_allocation": recommendation.total_allocation,
                "market_environment": recommendation.market_environment,
                "risk_assessment": recommendation.risk_assessment,
                "rebalancing_frequency": recommendation.rebalancing_frequency,
                "key_catalysts": recommendation.key_catalysts,
                "warnings": recommendation.warnings
            },
            "summary": summary,
            "forex_analysis": {
                "krw_usd_trend": forex_analysis.get("krw_usd_trend", {}),
                "dollar_index": forex_analysis.get("dollar_index", {})
            },
            "geopolitical_risk": geo_risk,
            "generated_at": datetime.now().isoformat(),
            "message": "매크로 경제, 환율, 지정학적 리스크를 종합한 자산 배분 제안입니다."
        }

        # 캐시 저장 (1시간)
        cache_manager.set_cached("asset-allocation", result, params=cache_params, ttl_seconds=3600)
        logger.info(f"💾 자산 배분 제안 캐시 저장 완료 (투자금액: {investment_amount:,}원, 리스크: {risk_tolerance})")

        return result

    except Exception as e:
        logger.error(f"❌ 자산 배분 제안 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "message": f"자산 배분 제안 생성 실패: {str(e)}"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)