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
                timeout=30
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
        """인사이트 삽입"""
        try:
            # 제목 + 내용으로 임베딩 생성
            text = f"{insight['title']} {insight['content']}"
            embedding = self.generate_embedding(text)

            # Supabase에 삽입
            data = {
                "title": insight["title"],
                "content": insight["content"],
                "sector": insight.get("sector", ""),
                "sentiment": insight.get("sentiment", ""),
                "keywords": insight.get("keywords", []),
                "date": insight.get("date", ""),
                "url": insight.get("url", ""),
                "embedding": embedding
            }

            result = self.client.table("investment_insights").insert(data).execute()

            logger.info(f"✅ 인사이트 삽입 완료: {insight['title'][:50]}...")
            return True

        except Exception as e:
            logger.error(f"❌ 인사이트 삽입 실패: {e}")
            return False

    def search_similar(self, query: str, top_k: int = 3) -> List[Dict]:
        """벡터 유사도 기반 검색"""
        try:
            # 쿼리 임베딩 생성
            query_embedding = self.generate_embedding(query)

            # pgvector 유사도 검색 (RPC 함수 호출)
            # Supabase에서 아래 함수를 미리 만들어야 함:
            # CREATE FUNCTION match_insights(query_embedding vector(768), match_count int)
            # RETURNS TABLE (id int, title text, content text, sector text, sentiment text, keywords text[], similarity float)
            # AS $$
            #   SELECT id, title, content, sector, sentiment, keywords,
            #          1 - (embedding <=> query_embedding) as similarity
            #   FROM investment_insights
            #   ORDER BY embedding <=> query_embedding
            #   LIMIT match_count;
            # $$ LANGUAGE sql;

            result = self.client.rpc(
                "match_insights",
                {
                    "query_embedding": query_embedding,
                    "match_count": top_k
                }
            ).execute()

            insights = result.data
            logger.info(f"✅ {len(insights)}개 유사 인사이트 발견")

            return insights

        except Exception as e:
            logger.error(f"❌ 검색 실패: {e}")
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
