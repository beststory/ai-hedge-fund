"""
예측 시장 (Prediction Market) 시스템
Polymarket 스타일 예측 플랫폼

주요 기능:
1. 예측 주제 관리 (생성, 조회, 종료)
2. 예측 제출 (사용자, AI 에이전트)
3. 실시간 컨센서스 집계
4. 결과 검증 및 정확도 계산
5. 투자 시그널 생성
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime, timedelta
import logging
from supabase import Client

logger = logging.getLogger(__name__)


# ===================================================================
# Pydantic 모델 정의
# ===================================================================

class PredictionTopic(BaseModel):
    """예측 주제 모델"""
    id: Optional[int] = None
    title: str = Field(..., description="예측 주제 제목")
    description: Optional[str] = Field(None, description="상세 설명")
    category: Literal["stock", "economy", "culture", "tech", "politics", "other"] = Field(..., description="카테고리")
    question_type: Literal["binary", "probability"] = Field(default="binary", description="질문 유형")

    # 타임라인
    created_at: Optional[datetime] = None
    deadline: datetime = Field(..., description="예측 마감일")
    resolution_date: Optional[datetime] = None

    # 결과
    status: Literal["open", "closed", "resolved", "cancelled"] = Field(default="open")
    actual_outcome: Optional[str] = None
    resolution_notes: Optional[str] = None

    # 메타데이터
    tags: List[str] = Field(default_factory=list)
    related_tickers: List[str] = Field(default_factory=list)
    data_source: Optional[str] = None

    created_by: Optional[str] = None
    view_count: int = 0
    prediction_count: int = 0

    @validator('deadline')
    def validate_deadline(cls, v):
        if v <= datetime.now():
            raise ValueError("마감일은 현재 시간보다 미래여야 합니다")
        return v


class UserPrediction(BaseModel):
    """사용자/AI 예측 모델"""
    id: Optional[int] = None
    topic_id: int = Field(..., description="예측 주제 ID")

    # 예측자 정보
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    predictor_type: Literal["human", "ai_agent"] = Field(default="human")
    agent_name: Optional[str] = None

    # 예측 내용
    prediction_value: float = Field(..., ge=0, le=100, description="예측 확률 (0-100)")
    prediction_text: Optional[str] = None  # "Yes" / "No"
    confidence_level: Literal["low", "medium", "high"] = Field(default="medium")
    reasoning: Optional[str] = None

    # 시간
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # 메타데이터
    data_sources: List[str] = Field(default_factory=list)


class PredictionAccuracy(BaseModel):
    """예측 정확도 모델"""
    id: Optional[int] = None
    topic_id: int
    prediction_id: int

    # 정확도 메트릭
    brier_score: Optional[float] = None  # 0 = 완벽, 1 = 최악
    log_score: Optional[float] = None
    accuracy_percentage: Optional[float] = None

    # 결과 비교
    predicted_value: float
    actual_value: float
    error_margin: Optional[float] = None

    calculated_at: Optional[datetime] = None


class CommunityConsensus(BaseModel):
    """커뮤니티 컨센서스 모델"""
    topic_id: int
    title: str
    category: str
    status: str
    deadline: datetime

    # 전체 통계
    total_predictions: int
    avg_prediction: Optional[float] = None
    prediction_stddev: Optional[float] = None

    # 인간 vs AI
    human_avg: Optional[float] = None
    ai_avg: Optional[float] = None
    human_count: int
    ai_count: int

    last_prediction_at: Optional[datetime] = None


class InvestmentSignal(BaseModel):
    """투자 시그널 모델"""
    topic_id: int
    title: str
    category: str
    related_tickers: List[str]

    # 예측 집계
    consensus_probability: float
    prediction_count: int
    confidence_weighted_avg: float

    # 시그널 강도
    signal_strength: Literal["strong_bullish", "bullish", "neutral", "bearish", "strong_bearish"]

    deadline: datetime


class PredictorPerformance(BaseModel):
    """예측자 성과 모델"""
    id: Optional[int] = None
    user_id: Optional[str] = None
    agent_name: Optional[str] = None
    predictor_type: Literal["human", "ai_agent"]

    # 성과 지표
    total_predictions: int = 0
    resolved_predictions: int = 0
    avg_brier_score: Optional[float] = None
    avg_accuracy: Optional[float] = None

    # 카테고리별 성과
    category_stats: Dict[str, Any] = Field(default_factory=dict)

    # 순위
    global_rank: Optional[int] = None
    category_rank: Dict[str, int] = Field(default_factory=dict)

    updated_at: Optional[datetime] = None


# ===================================================================
# 예측 시장 클래스
# ===================================================================

class PredictionMarket:
    """예측 시장 메인 클래스"""

    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client

    # ================================================================
    # 1. 예측 주제 관리
    # ================================================================

    async def create_topic(self, topic: PredictionTopic) -> Dict[str, Any]:
        """새 예측 주제 생성"""
        try:
            data = topic.dict(exclude_none=True, exclude={'id', 'created_at', 'view_count', 'prediction_count'})

            result = self.supabase.table("prediction_topics").insert(data).execute()

            logger.info(f"새 예측 주제 생성: {topic.title}")
            return {"success": True, "data": result.data[0] if result.data else None}

        except Exception as e:
            logger.error(f"예측 주제 생성 실패: {e}")
            return {"success": False, "error": str(e)}

    async def get_topics(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """예측 주제 목록 조회"""
        try:
            query = self.supabase.table("prediction_topics").select("*")

            if status:
                query = query.eq("status", status)
            if category:
                query = query.eq("category", category)

            query = query.order("created_at", desc=True).range(offset, offset + limit - 1)

            result = query.execute()
            return result.data or []

        except Exception as e:
            logger.error(f"예측 주제 조회 실패: {e}")
            return []

    async def get_topic_by_id(self, topic_id: int) -> Optional[Dict[str, Any]]:
        """특정 예측 주제 조회"""
        try:
            result = self.supabase.table("prediction_topics").select("*").eq("id", topic_id).execute()

            if result.data:
                # 조회수 증가
                self.supabase.table("prediction_topics").update({"view_count": result.data[0].get("view_count", 0) + 1}).eq("id", topic_id).execute()

                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"예측 주제 조회 실패 (ID: {topic_id}): {e}")
            return None

    async def close_topic(self, topic_id: int) -> Dict[str, Any]:
        """예측 주제 마감 (더 이상 예측 불가)"""
        try:
            result = self.supabase.table("prediction_topics").update({"status": "closed"}).eq("id", topic_id).execute()

            logger.info(f"예측 주제 마감: {topic_id}")
            return {"success": True, "data": result.data[0] if result.data else None}

        except Exception as e:
            logger.error(f"예측 주제 마감 실패: {e}")
            return {"success": False, "error": str(e)}

    async def resolve_topic(self, topic_id: int, actual_outcome: str, resolution_notes: Optional[str] = None) -> Dict[str, Any]:
        """예측 주제 결과 확정 및 정확도 계산 트리거"""
        try:
            result = self.supabase.table("prediction_topics").update({"status": "resolved", "actual_outcome": actual_outcome, "resolution_date": datetime.now().isoformat(), "resolution_notes": resolution_notes}).eq("id", topic_id).execute()

            logger.info(f"예측 주제 결과 확정: {topic_id} -> {actual_outcome}")
            return {"success": True, "data": result.data[0] if result.data else None}

        except Exception as e:
            logger.error(f"예측 주제 결과 확정 실패: {e}")
            return {"success": False, "error": str(e)}

    # ================================================================
    # 2. 예측 제출
    # ================================================================

    async def submit_prediction(self, prediction: UserPrediction) -> Dict[str, Any]:
        """예측 제출 (사용자 또는 AI 에이전트)"""
        try:
            # 주제 상태 확인
            topic = await self.get_topic_by_id(prediction.topic_id)
            if not topic:
                return {"success": False, "error": "존재하지 않는 주제입니다"}

            if topic["status"] != "open":
                return {"success": False, "error": "마감되었거나 종료된 주제입니다"}

            # 마감일 확인
            deadline = datetime.fromisoformat(topic["deadline"].replace("Z", "+00:00"))
            if deadline <= datetime.now():
                return {"success": False, "error": "예측 마감 시간이 지났습니다"}

            # 예측 저장
            data = prediction.dict(exclude_none=True, exclude={'id', 'created_at', 'updated_at'})
            result = self.supabase.table("user_predictions").insert(data).execute()

            # 주제의 prediction_count 증가
            self.supabase.table("prediction_topics").update({"prediction_count": topic.get("prediction_count", 0) + 1}).eq("id", prediction.topic_id).execute()

            logger.info(f"예측 제출: 주제 {prediction.topic_id}, 예측자 {prediction.user_name or prediction.agent_name}")
            return {"success": True, "data": result.data[0] if result.data else None}

        except Exception as e:
            logger.error(f"예측 제출 실패: {e}")
            return {"success": False, "error": str(e)}

    async def get_predictions_by_topic(self, topic_id: int) -> List[Dict[str, Any]]:
        """특정 주제의 모든 예측 조회"""
        try:
            result = self.supabase.table("user_predictions").select("*").eq("topic_id", topic_id).order("created_at", desc=False).execute()

            return result.data or []

        except Exception as e:
            logger.error(f"예측 조회 실패 (주제 ID: {topic_id}): {e}")
            return []

    async def get_user_predictions(self, user_id: str) -> List[Dict[str, Any]]:
        """특정 사용자의 모든 예측 조회"""
        try:
            result = self.supabase.table("user_predictions").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()

            return result.data or []

        except Exception as e:
            logger.error(f"사용자 예측 조회 실패 (사용자 ID: {user_id}): {e}")
            return []

    # ================================================================
    # 3. 컨센서스 및 통계
    # ================================================================

    async def get_community_consensus(self, topic_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """커뮤니티 컨센서스 조회"""
        try:
            query = self.supabase.table("community_consensus").select("*")

            if topic_id:
                query = query.eq("topic_id", topic_id)

            result = query.execute()
            return result.data or []

        except Exception as e:
            logger.error(f"커뮤니티 컨센서스 조회 실패: {e}")
            return []

    async def get_ai_agent_consensus(self, topic_id: int) -> List[Dict[str, Any]]:
        """AI 에이전트들의 예측 조회"""
        try:
            result = self.supabase.table("ai_agent_consensus").select("*").eq("topic_id", topic_id).execute()

            return result.data or []

        except Exception as e:
            logger.error(f"AI 에이전트 컨센서스 조회 실패: {e}")
            return []

    async def get_investment_signals(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """투자 시그널 조회"""
        try:
            query = self.supabase.table("investment_signals").select("*")

            if category:
                query = query.eq("category", category)

            result = query.order("consensus_probability", desc=True).execute()
            return result.data or []

        except Exception as e:
            logger.error(f"투자 시그널 조회 실패: {e}")
            return []

    # ================================================================
    # 4. 성과 추적
    # ================================================================

    async def get_predictor_performance(
        self,
        predictor_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """예측자 성과 조회 (리더보드)"""
        try:
            query = self.supabase.table("predictor_performance").select("*")

            if predictor_type:
                query = query.eq("predictor_type", predictor_type)

            result = query.order("avg_accuracy", desc=True).limit(limit).execute()
            return result.data or []

        except Exception as e:
            logger.error(f"예측자 성과 조회 실패: {e}")
            return []

    async def get_prediction_accuracy(self, topic_id: int) -> List[Dict[str, Any]]:
        """특정 주제의 예측 정확도 조회"""
        try:
            result = self.supabase.table("prediction_accuracy").select("*").eq("topic_id", topic_id).order("accuracy_percentage", desc=True).execute()

            return result.data or []

        except Exception as e:
            logger.error(f"예측 정확도 조회 실패: {e}")
            return []

    # ================================================================
    # 5. 통계 및 분석
    # ================================================================

    async def get_trending_topics(self, limit: int = 10) -> List[Dict[str, Any]]:
        """인기 있는 예측 주제 (예측 수 기준)"""
        try:
            result = self.supabase.table("prediction_topics").select("*").eq("status", "open").order("prediction_count", desc=True).limit(limit).execute()

            return result.data or []

        except Exception as e:
            logger.error(f"인기 주제 조회 실패: {e}")
            return []

    async def get_recent_predictions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """최근 예측 활동"""
        try:
            result = self.supabase.table("user_predictions").select("*, prediction_topics(title, category)").order("created_at", desc=True).limit(limit).execute()

            return result.data or []

        except Exception as e:
            logger.error(f"최근 예측 조회 실패: {e}")
            return []

    async def calculate_market_sentiment(self, category: str) -> Dict[str, Any]:
        """카테고리별 시장 감성 계산"""
        try:
            # 해당 카테고리의 모든 열린 주제에 대한 평균 예측 확률
            topics = await self.get_topics(status="open", category=category)

            if not topics:
                return {"category": category, "sentiment": "neutral", "avg_probability": 50.0, "topic_count": 0}

            total_prob = 0
            topic_count = 0

            for topic in topics:
                consensus = await self.get_community_consensus(topic_id=topic["id"])
                if consensus and consensus[0].get("avg_prediction"):
                    total_prob += consensus[0]["avg_prediction"]
                    topic_count += 1

            if topic_count == 0:
                return {"category": category, "sentiment": "neutral", "avg_probability": 50.0, "topic_count": 0}

            avg_prob = total_prob / topic_count

            # 감성 판정
            if avg_prob > 65:
                sentiment = "매우 긍정적"
            elif avg_prob > 55:
                sentiment = "긍정적"
            elif avg_prob < 35:
                sentiment = "매우 부정적"
            elif avg_prob < 45:
                sentiment = "부정적"
            else:
                sentiment = "중립적"

            return {"category": category, "sentiment": sentiment, "avg_probability": round(avg_prob, 2), "topic_count": topic_count}

        except Exception as e:
            logger.error(f"시장 감성 계산 실패: {e}")
            return {"category": category, "sentiment": "중립적", "avg_probability": 50.0, "topic_count": 0, "error": str(e)}


# ===================================================================
# 헬퍼 함수
# ===================================================================

def calculate_brier_score(predicted_prob: float, actual_outcome: float) -> float:
    """
    Brier Score 계산
    - predicted_prob: 예측 확률 (0-100)
    - actual_outcome: 실제 결과 (0 또는 1)
    - 반환값: 0 = 완벽한 예측, 1 = 최악의 예측
    """
    return (predicted_prob / 100.0 - actual_outcome) ** 2


def interpret_brier_score(score: float) -> str:
    """Brier Score 해석"""
    if score < 0.1:
        return "매우 정확"
    elif score < 0.25:
        return "정확"
    elif score < 0.5:
        return "보통"
    elif score < 0.75:
        return "부정확"
    else:
        return "매우 부정확"
