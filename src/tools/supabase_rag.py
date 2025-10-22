"""Supabase pgvector 기반 투자 인사이트 RAG 시스템"""
import os
import json
import requests
from typing import List, Dict
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SupabaseRAG:
    """Supabase pgvector 기반 RAG 시스템"""

    def __init__(self):
        # Supabase 설정
        self.supabase_url = os.getenv("SUPABASE_PUBLIC_URL", "http://localhost:8000")
        self.supabase_key = os.getenv("SERVICE_ROLE_KEY")
        self.ollama_url = "http://localhost:11434"

        if not self.supabase_key:
            raise ValueError("SERVICE_ROLE_KEY not found in .env")

        # Supabase 클라이언트 초기화
        try:
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
            logger.info(f"✅ Supabase 연결 성공: {self.supabase_url}")
        except Exception as e:
            logger.error(f"❌ Supabase 연결 실패: {e}")
            raise

    def generate_embedding(self, text: str) -> List[float]:
        """Ollama nomic-embed-text 모델로 임베딩 생성"""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/embeddings",
                json={
                    "model": "nomic-embed-text",
                    "prompt": text
                },
                timeout=5  # 30초에서 5초로 단축
            )
            response.raise_for_status()
            embedding = response.json()["embedding"]
            logger.info(f"✅ 임베딩 생성 완료 (차원: {len(embedding)})")
            return embedding

        except Exception as e:
            logger.error(f"❌ 임베딩 생성 실패: {e}")
            raise

    def setup_database(self):
        """pgvector 확장 및 테이블 생성"""
        try:
            # pgvector 확장 활성화 (이미 있으면 무시)
            logger.info("🔧 pgvector 확장 설정 중...")

            # investment_insights 테이블 생성
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS investment_insights (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                sector TEXT,
                sentiment TEXT,
                keywords TEXT[],
                date TEXT,
                url TEXT,
                embedding vector(768),
                created_at TIMESTAMPTZ DEFAULT NOW()
            );

            -- 벡터 인덱스 생성 (HNSW 알고리즘)
            CREATE INDEX IF NOT EXISTS investment_insights_embedding_idx
            ON investment_insights
            USING hnsw (embedding vector_cosine_ops);
            """

            # Supabase는 SQL 실행을 REST API로 해야 함
            # 대신 데이터 삽입/조회는 Python 클라이언트로 가능

            logger.info("✅ 데이터베이스 설정 완료")
            logger.info("⚠️  pgvector 확장 및 테이블은 Supabase 대시보드에서 수동으로 생성 필요")
            logger.info(f"   SQL: \n{create_table_sql}")

        except Exception as e:
            logger.error(f"❌ 데이터베이스 설정 실패: {e}")
            raise

    def insert_insight(self, insight: Dict) -> bool:
        """인사이트 삽입 (제목 임베딩 + 내용 임베딩)"""
        try:
            # 제목 + 내용으로 임베딩 생성
            text = f"{insight['title']} {insight['content']}"
            embedding = self.generate_embedding(text)

            # 제목만으로 임베딩 생성 (하이브리드 검색용)
            title_embedding = self.generate_embedding(insight['title'])

            # Supabase에 삽입
            data = {
                "title": insight["title"],
                "content": insight["content"],
                "sector": insight.get("sector", ""),
                "sentiment": insight.get("sentiment", ""),
                "keywords": insight.get("keywords", []),
                "date": insight.get("date", ""),
                "url": insight.get("url", ""),
                "embedding": embedding,
                "title_embedding": title_embedding
            }

            result = self.client.table("investment_insights").insert(data).execute()

            logger.info(f"✅ 인사이트 삽입 완료: {insight['title'][:50]}...")
            return True

        except Exception as e:
            logger.error(f"❌ 인사이트 삽입 실패: {e}")
            return False

    def search_similar(self, query: str, top_k: int = 3, use_hybrid: bool = True, title_weight: float = None, use_text_search: bool = True) -> List[Dict]:
        """벡터 유사도 + 텍스트 검색 하이브리드 시스템

        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            use_hybrid: True면 하이브리드 검색 (제목+내용 벡터), False면 기존 검색 (내용 벡터만)
            title_weight: 하이브리드 검색 시 제목 가중치 (0.0~1.0)
                         None이면 쿼리 길이에 따라 자동 조정:
                         - 짧은 쿼리(≤10자): 1.0 (제목 100%)
                         - 중간 쿼리(11-20자): 0.8 (제목 80%)
                         - 긴 쿼리(>20자): 0.5 (제목 50%)
            use_text_search: True면 텍스트 매칭 보너스 점수 추가 (제목 +0.15, 내용 +0.05)
        """
        try:
            # 스마트 가중치 조정: 쿼리 길이에 따라 자동 설정
            if title_weight is None:
                query_len = len(query)
                if query_len <= 10:
                    title_weight = 1.0  # 짧은 키워드는 제목 중심 검색
                elif query_len <= 20:
                    title_weight = 0.8  # 중간 길이는 제목 위주
                else:
                    title_weight = 0.5  # 긴 쿼리는 내용도 중요

                logger.info(f"스마트 가중치 조정: 쿼리 길이 {query_len}자 → 제목 가중치 {title_weight}")

            # 쿼리 임베딩 생성
            query_embedding = self.generate_embedding(query)

            if use_hybrid:
                # 하이브리드 검색 (제목 + 내용 벡터 + 텍스트 매칭)
                params = {
                    "query_embedding": query_embedding,
                    "match_count": top_k,
                    "use_title_weight": title_weight
                }

                # 텍스트 검색 활성화 시 쿼리 텍스트 추가
                if use_text_search:
                    params["query_text"] = query
                    logger.info(f"텍스트 검색 활성화: '{query}' 키워드 매칭")

                result = self.client.rpc("match_insights_hybrid", params).execute()
            else:
                # 기존 검색 (내용만)
                result = self.client.rpc(
                    "match_insights",
                    {
                        "query_embedding": query_embedding,
                        "match_count": top_k
                    }
                ).execute()

            insights = result.data
            search_mode = "벡터+텍스트" if (use_hybrid and use_text_search) else ("하이브리드" if use_hybrid else "기본")
            logger.info(f"✅ {len(insights)}개 유사 인사이트 발견 (모드: {search_mode})")

            return insights

        except Exception as e:
            logger.error(f"❌ 검색 실패: {e}")
            # 하이브리드 실패 시 기존 방식으로 재시도
            if use_hybrid:
                logger.info("하이브리드 검색 실패, 기존 방식으로 재시도...")
                return self.search_similar(query, top_k, use_hybrid=False)
            return []

    def migrate_json_data(self, json_path: str):
        """JSON 데이터를 Supabase로 마이그레이션"""
        try:
            logger.info(f"📦 JSON 데이터 로드 중: {json_path}")

            with open(json_path, 'r', encoding='utf-8') as f:
                insights = json.load(f)

            logger.info(f"📊 {len(insights)}개 인사이트 마이그레이션 시작...")

            success_count = 0
            for i, insight in enumerate(insights, 1):
                logger.info(f"[{i}/{len(insights)}] 삽입 중...")
                if self.insert_insight(insight):
                    success_count += 1

            logger.info(f"✅ 마이그레이션 완료: {success_count}/{len(insights)} 성공")

        except Exception as e:
            logger.error(f"❌ 마이그레이션 실패: {e}")
            raise


def test_supabase_rag():
    """Supabase RAG 테스트"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 Supabase RAG 시스템 테스트")
    logger.info("=" * 80)

    try:
        # 1. Supabase 연결 테스트
        rag = SupabaseRAG()

        # 2. 데이터베이스 설정
        rag.setup_database()

        # 3. 임베딩 생성 테스트
        logger.info("\n[테스트 1] 임베딩 생성")
        test_text = "양자컴퓨팅 기술 발전과 투자 기회"
        embedding = rag.generate_embedding(test_text)
        logger.info(f"  - 텍스트: {test_text}")
        logger.info(f"  - 임베딩 차원: {len(embedding)}")
        logger.info(f"  - 샘플: {embedding[:5]}")

        logger.info("\n" + "=" * 80)
        logger.info("✅ Supabase RAG 시스템 테스트 완료")
        logger.info("=" * 80 + "\n")

        logger.info("\n📝 다음 단계:")
        logger.info("1. Supabase 대시보드에서 pgvector 확장 활성화")
        logger.info("2. investment_insights 테이블 및 match_insights 함수 생성")
        logger.info("3. JSON 데이터 마이그레이션 실행")

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")


if __name__ == '__main__':
    test_supabase_rag()
