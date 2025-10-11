"""JSON 데이터를 Supabase로 마이그레이션"""
from src.tools.supabase_rag import SupabaseRAG
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info("\n" + "=" * 80)
    logger.info("📦 JSON 데이터 Supabase 마이그레이션")
    logger.info("=" * 80)

    rag = SupabaseRAG()

    # 10개 샘플 데이터 마이그레이션
    rag.migrate_json_data("data/investment_insights.json")

    logger.info("\n✅ 마이그레이션 완료!")
