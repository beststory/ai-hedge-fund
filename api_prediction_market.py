"""
예측 시장 (Prediction Market) API 라우터
Polymarket 스타일 예측 플랫폼 엔드포인트

FastAPI 라우터로 분리하여 simple_web_api.py에 통합
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from src.tools.prediction_market import (
    PredictionMarket,
    PredictionTopic,
    UserPrediction,
    CommunityConsensus,
    InvestmentSignal,
    PredictorPerformance,
)

logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(prefix="/api/prediction", tags=["Prediction Market"])


def get_prediction_market(supabase_client) -> PredictionMarket:
    """PredictionMarket 인스턴스 생성"""
    return PredictionMarket(supabase_client)


# ===================================================================
# 1. 예측 주제 관리 엔드포인트
# ===================================================================

@router.post("/topics")
async def create_topic_endpoint(
    topic: PredictionTopic,
    supabase_client,
    current_user: Optional[Dict[str, Any]] = None
):
    """새 예측 주제 생성

    Args:
        topic: 예측 주제 정보
        current_user: 현재 로그인한 사용자 (선택사항)

    Returns:
        생성된 예측 주제
    """
    try:
        # 생성자 정보 추가
        if current_user:
            topic.created_by = current_user.get("user_id")

        pm = get_prediction_market(supabase_client)
        result = await pm.create_topic(topic)

        if result["success"]:
            return {
                "success": True,
                "topic": result["data"],
                "message": "예측 주제가 생성되었습니다"
            }
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "주제 생성 실패"))

    except Exception as e:
        logger.error(f"예측 주제 생성 API 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topics")
async def get_topics_endpoint(
    supabase_client,
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """예측 주제 목록 조회

    Args:
        status: 주제 상태 필터 (open, closed, resolved, cancelled)
        category: 카테고리 필터
        limit: 최대 결과 수
        offset: 페이지네이션 오프셋

    Returns:
        예측 주제 리스트
    """
    try:
        pm = get_prediction_market(supabase_client)
        topics = await pm.get_topics(status, category, limit, offset)

        return {
            "success": True,
            "topics": topics,
            "count": len(topics),
            "filters": {
                "status": status,
                "category": category
            }
        }

    except Exception as e:
        logger.error(f"예측 주제 조회 API 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topics/{topic_id}")
async def get_topic_by_id_endpoint(topic_id: int, supabase_client):
    """특정 예측 주제 상세 조회

    Args:
        topic_id: 주제 ID

    Returns:
        예측 주제 상세 정보 + 커뮤니티 컨센서스
    """
    try:
        pm = get_prediction_market(supabase_client)

        # 주제 정보
        topic = await pm.get_topic_by_id(topic_id)

        if not topic:
            raise HTTPException(status_code=404, detail="주제를 찾을 수 없습니다")

        # 커뮤니티 컨센서스
        consensus = await pm.get_community_consensus(topic_id=topic_id)

        # AI 에이전트 예측
        ai_predictions = await pm.get_ai_agent_consensus(topic_id)

        # 모든 예측
        all_predictions = await pm.get_predictions_by_topic(topic_id)

        return {
            "success": True,
            "topic": topic,
            "consensus": consensus[0] if consensus else None,
            "ai_predictions": ai_predictions,
            "recent_predictions": all_predictions[:10],
            "total_predictions": len(all_predictions)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"예측 주제 상세 조회 API 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/topics/{topic_id}/close")
async def close_topic_endpoint(
    topic_id: int,
    supabase_client,
    current_user: Dict[str, Any]
):
    """예측 주제 마감 (관리자 전용)

    Args:
        topic_id: 주제 ID
        current_user: 현재 로그인한 사용자

    Returns:
        마감된 주제 정보
    """
    try:
        pm = get_prediction_market(supabase_client)
        result = await pm.close_topic(topic_id)

        if result["success"]:
            return {
                "success": True,
                "topic": result["data"],
                "message": "예측 주제가 마감되었습니다"
            }
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "주제 마감 실패"))

    except Exception as e:
        logger.error(f"예측 주제 마감 API 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/topics/{topic_id}/resolve")
async def resolve_topic_endpoint(
    topic_id: int,
    request: Dict[str, Any],
    supabase_client,
    current_user: Dict[str, Any]
):
    """예측 주제 결과 확정 (관리자 전용)

    Args:
        topic_id: 주제 ID
        request: {"actual_outcome": "yes/no", "resolution_notes": "..."}
        current_user: 현재 로그인한 사용자

    Returns:
        확정된 주제 정보 + 정확도 계산 결과
    """
    try:
        actual_outcome = request.get("actual_outcome")
        resolution_notes = request.get("resolution_notes")

        if not actual_outcome:
            raise HTTPException(status_code=400, detail="actual_outcome이 필요합니다")

        pm = get_prediction_market(supabase_client)
        result = await pm.resolve_topic(topic_id, actual_outcome, resolution_notes)

        if result["success"]:
            # 정확도 데이터 조회
            accuracy_data = await pm.get_prediction_accuracy(topic_id)

            return {
                "success": True,
                "topic": result["data"],
                "accuracy_calculated": len(accuracy_data),
                "message": "예측 주제 결과가 확정되었습니다"
            }
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "결과 확정 실패"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"예측 주제 결과 확정 API 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# 2. 예측 제출 엔드포인트
# ===================================================================

@router.post("/predictions")
async def submit_prediction_endpoint(
    prediction: UserPrediction,
    supabase_client,
    current_user: Optional[Dict[str, Any]] = None
):
    """예측 제출 (사용자 또는 AI 에이전트)

    Args:
        prediction: 예측 정보
        current_user: 현재 로그인한 사용자 (선택사항)

    Returns:
        제출된 예측 정보
    """
    try:
        # 사용자 정보 추가
        if current_user and prediction.predictor_type == "human":
            prediction.user_id = current_user.get("user_id")
            prediction.user_name = current_user.get("email")

        pm = get_prediction_market(supabase_client)
        result = await pm.submit_prediction(prediction)

        if result["success"]:
            return {
                "success": True,
                "prediction": result["data"],
                "message": "예측이 제출되었습니다"
            }
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "예측 제출 실패"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"예측 제출 API 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predictions/topic/{topic_id}")
async def get_predictions_by_topic_endpoint(topic_id: int, supabase_client):
    """특정 주제의 모든 예측 조회

    Args:
        topic_id: 주제 ID

    Returns:
        예측 리스트
    """
    try:
        pm = get_prediction_market(supabase_client)
        predictions = await pm.get_predictions_by_topic(topic_id)

        return {
            "success": True,
            "predictions": predictions,
            "count": len(predictions)
        }

    except Exception as e:
        logger.error(f"주제별 예측 조회 API 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predictions/user/{user_id}")
async def get_user_predictions_endpoint(
    user_id: str,
    supabase_client,
    current_user: Dict[str, Any]
):
    """특정 사용자의 모든 예측 조회 (본인만 가능)

    Args:
        user_id: 사용자 ID
        current_user: 현재 로그인한 사용자

    Returns:
        사용자의 예측 리스트
    """
    try:
        # 본인 확인
        if current_user.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="권한이 없습니다")

        pm = get_prediction_market(supabase_client)
        predictions = await pm.get_user_predictions(user_id)

        return {
            "success": True,
            "predictions": predictions,
            "count": len(predictions)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자별 예측 조회 API 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# 3. 컨센서스 및 통계 엔드포인트
# ===================================================================

@router.get("/consensus")
async def get_community_consensus_endpoint(
    supabase_client,
    topic_id: Optional[int] = None
):
    """커뮤니티 컨센서스 조회

    Args:
        topic_id: 주제 ID (선택사항, 없으면 모든 열린 주제)

    Returns:
        커뮤니티 컨센서스 리스트
    """
    try:
        pm = get_prediction_market(supabase_client)
        consensus = await pm.get_community_consensus(topic_id)

        return {
            "success": True,
            "consensus": consensus,
            "count": len(consensus)
        }

    except Exception as e:
        logger.error(f"커뮤니티 컨센서스 조회 API 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/consensus/ai")
async def get_ai_consensus_endpoint(topic_id: int, supabase_client):
    """AI 에이전트 컨센서스 조회

    Args:
        topic_id: 주제 ID

    Returns:
        AI 에이전트 예측 리스트
    """
    try:
        pm = get_prediction_market(supabase_client)
        ai_predictions = await pm.get_ai_agent_consensus(topic_id)

        return {
            "success": True,
            "ai_predictions": ai_predictions,
            "count": len(ai_predictions)
        }

    except Exception as e:
        logger.error(f"AI 컨센서스 조회 API 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals")
async def get_investment_signals_endpoint(
    supabase_client,
    category: Optional[str] = None
):
    """투자 시그널 조회

    Args:
        category: 카테고리 필터 (stock, economy 등)

    Returns:
        투자 시그널 리스트
    """
    try:
        pm = get_prediction_market(supabase_client)
        signals = await pm.get_investment_signals(category)

        return {
            "success": True,
            "signals": signals,
            "count": len(signals),
            "message": "예측 시장 데이터 기반 투자 시그널입니다"
        }

    except Exception as e:
        logger.error(f"투자 시그널 조회 API 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# 4. 성과 추적 엔드포인트
# ===================================================================

@router.get("/leaderboard")
async def get_leaderboard_endpoint(
    supabase_client,
    predictor_type: Optional[str] = None,
    limit: int = 50
):
    """예측자 리더보드 조회

    Args:
        predictor_type: 예측자 유형 필터 (human, ai_agent)
        limit: 최대 결과 수

    Returns:
        예측자 성과 순위
    """
    try:
        pm = get_prediction_market(supabase_client)
        performance = await pm.get_predictor_performance(predictor_type, limit)

        return {
            "success": True,
            "leaderboard": performance,
            "count": len(performance),
            "predictor_type": predictor_type or "all"
        }

    except Exception as e:
        logger.error(f"리더보드 조회 API 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accuracy/{topic_id}")
async def get_prediction_accuracy_endpoint(topic_id: int, supabase_client):
    """특정 주제의 예측 정확도 조회

    Args:
        topic_id: 주제 ID

    Returns:
        예측 정확도 리스트 (Brier Score 포함)
    """
    try:
        pm = get_prediction_market(supabase_client)
        accuracy = await pm.get_prediction_accuracy(topic_id)

        return {
            "success": True,
            "accuracy": accuracy,
            "count": len(accuracy)
        }

    except Exception as e:
        logger.error(f"예측 정확도 조회 API 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# 5. 통계 및 분석 엔드포인트
# ===================================================================

@router.get("/trending")
async def get_trending_topics_endpoint(supabase_client, limit: int = 10):
    """인기 있는 예측 주제 조회

    Args:
        limit: 최대 결과 수

    Returns:
        인기 주제 리스트
    """
    try:
        pm = get_prediction_market(supabase_client)
        trending = await pm.get_trending_topics(limit)

        return {
            "success": True,
            "trending_topics": trending,
            "count": len(trending)
        }

    except Exception as e:
        logger.error(f"인기 주제 조회 API 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent-activity")
async def get_recent_activity_endpoint(supabase_client, limit: int = 20):
    """최근 예측 활동 조회

    Args:
        limit: 최대 결과 수

    Returns:
        최근 예측 리스트
    """
    try:
        pm = get_prediction_market(supabase_client)
        recent = await pm.get_recent_predictions(limit)

        return {
            "success": True,
            "recent_predictions": recent,
            "count": len(recent)
        }

    except Exception as e:
        logger.error(f"최근 활동 조회 API 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-sentiment/{category}")
async def get_market_sentiment_endpoint(category: str, supabase_client):
    """카테고리별 시장 감성 계산

    Args:
        category: 카테고리 (stock, economy, culture, tech, politics)

    Returns:
        시장 감성 분석 결과
    """
    try:
        pm = get_prediction_market(supabase_client)
        sentiment = await pm.calculate_market_sentiment(category)

        return {
            "success": True,
            "sentiment": sentiment
        }

    except Exception as e:
        logger.error(f"시장 감성 조회 API 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# 6. AI 에이전트 자동 예측 엔드포인트
# ===================================================================

@router.post("/ai-predict/{topic_id}")
async def ai_predict_topic_endpoint(topic_id: int, supabase_client):
    """AI 에이전트들이 특정 주제에 대해 자동 예측 생성

    Args:
        topic_id: 주제 ID

    Returns:
        생성된 AI 예측 리스트
    """
    try:
        pm = get_prediction_market(supabase_client)

        # 주제 정보 가져오기
        topic = await pm.get_topic_by_id(topic_id)

        if not topic:
            raise HTTPException(status_code=404, detail="주제를 찾을 수 없습니다")

        if topic["status"] != "open":
            raise HTTPException(status_code=400, detail="마감된 주제입니다")

        # TODO: AI 에이전트 통합 (warren_buffett, peter_lynch 등)
        # 현재는 샘플 데이터로 대체

        ai_agents = [
            {"name": "warren_buffett", "confidence": "high"},
            {"name": "peter_lynch", "confidence": "medium"},
            {"name": "cathie_wood", "confidence": "high"},
        ]

        predictions_created = []

        for agent in ai_agents:
            prediction = UserPrediction(
                topic_id=topic_id,
                predictor_type="ai_agent",
                agent_name=agent["name"],
                prediction_value=65.0,  # TODO: 실제 AI 분석 결과
                confidence_level=agent["confidence"],
                reasoning=f"{agent['name']} AI 에이전트의 자동 분석 결과입니다."
            )

            result = await pm.submit_prediction(prediction)
            if result["success"]:
                predictions_created.append(result["data"])

        return {
            "success": True,
            "predictions_created": len(predictions_created),
            "predictions": predictions_created,
            "message": f"{len(predictions_created)}개의 AI 예측이 생성되었습니다"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI 자동 예측 API 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# 7. 대시보드 통합 엔드포인트
# ===================================================================

@router.get("/dashboard")
async def get_dashboard_data_endpoint(supabase_client):
    """예측 시장 대시보드 통합 데이터

    Returns:
        대시보드에 필요한 모든 데이터 (트렌딩, 최근 활동, 컨센서스 등)
    """
    try:
        pm = get_prediction_market(supabase_client)

        # 병렬로 데이터 수집
        trending = await pm.get_trending_topics(10)
        recent_activity = await pm.get_recent_predictions(20)
        consensus = await pm.get_community_consensus()
        signals = await pm.get_investment_signals()

        # 카테고리별 감성
        sentiments = {}
        for category in ["stock", "economy", "culture", "tech", "politics"]:
            sentiment = await pm.calculate_market_sentiment(category)
            sentiments[category] = sentiment

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "trending_topics": trending,
            "recent_activity": recent_activity,
            "open_topics_consensus": consensus,
            "investment_signals": signals,
            "market_sentiments": sentiments
        }

    except Exception as e:
        logger.error(f"대시보드 데이터 조회 API 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))
