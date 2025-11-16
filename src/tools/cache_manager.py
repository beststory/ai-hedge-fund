"""Supabase 기반 API 캐시 매니저 - 1시간 TTL"""
import os
import json
import hashlib
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CacheManager:
    """Supabase 기반 API 응답 캐싱 시스템"""

    def __init__(self):
        # Supabase 설정
        self.supabase_url = os.getenv("SUPABASE_URL", "http://localhost:8000")
        self.supabase_key = os.getenv("SERVICE_ROLE_KEY")

        if not self.supabase_key:
            logger.warning("⚠️ SERVICE_ROLE_KEY가 없습니다. 캐싱이 작동하지 않습니다.")
            self.client = None
            return

        # Supabase 클라이언트 초기화
        try:
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
            logger.info(f"✅ 캐시 매니저 초기화 성공: {self.supabase_url}")
        except Exception as e:
            logger.error(f"❌ 캐시 매니저 초기화 실패: {e}")
            self.client = None

    def _generate_cache_key(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> str:
        """캐시 키 생성 (엔드포인트 + 파라미터 해시)"""
        if params:
            # 파라미터를 정렬하여 일관된 해시 생성
            params_str = json.dumps(params, sort_keys=True)
            params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
            return f"{endpoint}:{params_hash}"
        return endpoint

    def get_cached(self, endpoint: str, params: Optional[Dict[str, Any]] = None, ttl_seconds: int = 3600) -> Optional[Dict[str, Any]]:
        """캐시된 데이터 조회 (TTL 이내면 반환)

        Args:
            endpoint: API 엔드포인트 (예: "top-stocks", "analyze")
            params: API 파라미터 (딕셔너리)
            ttl_seconds: TTL 시간 (초, 기본값 3600 = 1시간)

        Returns:
            캐시된 데이터 또는 None
        """
        if not self.client:
            return None

        try:
            cache_key = self._generate_cache_key(endpoint, params)

            # Supabase에서 캐시 조회
            result = self.client.table("api_cache").select("*").eq("cache_key", cache_key).execute()

            if not result.data:
                logger.info(f"💨 캐시 미스: {cache_key}")
                return None

            cached_item = result.data[0]

            # TTL 확인 (updated_at + ttl_seconds > 현재시간)
            updated_at = datetime.fromisoformat(cached_item["updated_at"].replace("Z", "+00:00"))
            ttl = cached_item.get("ttl_seconds", ttl_seconds)
            expiry_time = updated_at + timedelta(seconds=ttl)

            if datetime.now(expiry_time.tzinfo) > expiry_time:
                logger.info(f"⏰ 캐시 만료: {cache_key} (마지막 업데이트: {updated_at})")
                # 만료된 캐시 삭제
                self.invalidate_cache(endpoint, params)
                return None

            logger.info(f"✅ 캐시 히트: {cache_key} (만료까지: {(expiry_time - datetime.now(expiry_time.tzinfo)).total_seconds():.0f}초)")
            return cached_item["data"]

        except Exception as e:
            logger.error(f"❌ 캐시 조회 실패: {e}")
            return None

    def set_cached(self, endpoint: str, data: Dict[str, Any], params: Optional[Dict[str, Any]] = None, ttl_seconds: int = 3600) -> bool:
        """캐시 저장/업데이트

        Args:
            endpoint: API 엔드포인트
            data: 캐시할 데이터 (딕셔너리)
            params: API 파라미터
            ttl_seconds: TTL 시간 (초)

        Returns:
            성공 여부
        """
        if not self.client:
            return False

        try:
            cache_key = self._generate_cache_key(endpoint, params)

            # Upsert (있으면 업데이트, 없으면 삽입)
            self.client.table("api_cache").upsert({
                "cache_key": cache_key,
                "data": data,
                "ttl_seconds": ttl_seconds,
                "updated_at": datetime.now().isoformat()
            }).execute()

            logger.info(f"💾 캐시 저장: {cache_key} (TTL: {ttl_seconds}초)")
            return True

        except Exception as e:
            logger.error(f"❌ 캐시 저장 실패: {e}")
            return False

    def invalidate_cache(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> bool:
        """캐시 무효화 (삭제)

        Args:
            endpoint: API 엔드포인트
            params: API 파라미터

        Returns:
            성공 여부
        """
        if not self.client:
            return False

        try:
            cache_key = self._generate_cache_key(endpoint, params)

            # 캐시 삭제
            self.client.table("api_cache").delete().eq("cache_key", cache_key).execute()

            logger.info(f"🗑️ 캐시 삭제: {cache_key}")
            return True

        except Exception as e:
            logger.error(f"❌ 캐시 삭제 실패: {e}")
            return False

    def clear_all_cache(self) -> bool:
        """전체 캐시 삭제

        Returns:
            성공 여부
        """
        if not self.client:
            return False

        try:
            # 전체 삭제
            self.client.table("api_cache").delete().neq("cache_key", "").execute()

            logger.info("🗑️ 전체 캐시 삭제 완료")
            return True

        except Exception as e:
            logger.error(f"❌ 전체 캐시 삭제 실패: {e}")
            return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 조회

        Returns:
            캐시 통계 (총 항목 수, 유효 항목 수, 만료 항목 수)
        """
        if not self.client:
            return {
                "total_entries": 0,
                "valid_entries": 0,
                "expired_entries": 0,
                "status": "캐시 매니저 비활성화"
            }

        try:
            # 전체 캐시 조회
            result = self.client.table("api_cache").select("cache_key,updated_at,ttl_seconds").execute()

            total = len(result.data)
            valid = 0
            expired = 0

            for item in result.data:
                updated_at = datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00"))
                ttl = item.get("ttl_seconds", 3600)
                expiry_time = updated_at + timedelta(seconds=ttl)

                if datetime.now(expiry_time.tzinfo) <= expiry_time:
                    valid += 1
                else:
                    expired += 1

            return {
                "total_entries": total,
                "valid_entries": valid,
                "expired_entries": expired,
                "hit_rate": f"{(valid / total * 100):.1f}%" if total > 0 else "N/A"
            }

        except Exception as e:
            logger.error(f"❌ 캐시 통계 조회 실패: {e}")
            return {
                "total_entries": 0,
                "valid_entries": 0,
                "expired_entries": 0,
                "error": str(e)
            }


# 전역 캐시 매니저 인스턴스
cache_manager = CacheManager()


def test_cache_manager():
    """캐시 매니저 테스트"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 캐시 매니저 테스트")
    logger.info("=" * 80)

    # 1. 캐시 저장
    logger.info("\n[테스트 1] 캐시 저장")
    test_data = {
        "stocks": ["AAPL", "MSFT", "GOOGL"],
        "timestamp": datetime.now().isoformat()
    }
    cache_manager.set_cached("test-endpoint", test_data, {"limit": 3}, ttl_seconds=10)

    # 2. 캐시 조회 (히트)
    logger.info("\n[테스트 2] 캐시 조회 (히트)")
    cached = cache_manager.get_cached("test-endpoint", {"limit": 3})
    logger.info(f"캐시된 데이터: {cached}")

    # 3. 캐시 통계
    logger.info("\n[테스트 3] 캐시 통계")
    stats = cache_manager.get_cache_stats()
    logger.info(f"통계: {stats}")

    # 4. 캐시 무효화
    logger.info("\n[테스트 4] 캐시 무효화")
    cache_manager.invalidate_cache("test-endpoint", {"limit": 3})

    # 5. 캐시 조회 (미스)
    logger.info("\n[테스트 5] 캐시 조회 (미스)")
    cached = cache_manager.get_cached("test-endpoint", {"limit": 3})
    logger.info(f"캐시 미스 결과: {cached}")

    logger.info("\n" + "=" * 80)
    logger.info("✅ 캐시 매니저 테스트 완료")
    logger.info("=" * 80 + "\n")


if __name__ == '__main__':
    test_cache_manager()
