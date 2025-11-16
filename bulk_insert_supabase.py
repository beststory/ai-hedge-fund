"""변환된 인사이트를 Supabase에 일괄 삽입"""
import json
import logging
from src.tools.supabase_rag import SupabaseRAG

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def bulk_insert_insights(json_file: str):
    """JSON 파일에서 인사이트를 읽어 Supabase에 일괄 삽입"""
    logger.info(f"📂 JSON 파일 로드: {json_file}")

    with open(json_file, 'r', encoding='utf-8') as f:
        insights = json.load(f)

    logger.info(f"✅ {len(insights)}개 인사이트 로드 완료")

    # Supabase RAG 초기화
    rag = SupabaseRAG()

    success = 0
    failed = 0

    for i, insight in enumerate(insights, 1):
        try:
            rag.insert_insight(insight)
            success += 1
            if i % 50 == 0:
                logger.info(f"  진행 중: {i}/{len(insights)} ({success}개 성공, {failed}개 실패)")
        except Exception as e:
            failed += 1
            if failed <= 10:  # 처음 10개 실패만 로그
                logger.error(f"  ❌ [{i}] 삽입 실패: {e}")

    logger.info(f"\n{'=' * 80}")
    logger.info(f"✅ Supabase 일괄 삽입 완료!")
    logger.info(f"  - 성공: {success}개")
    logger.info(f"  - 실패: {failed}개")
    logger.info(f"  - 총계: {len(insights)}개")
    logger.info(f"{'=' * 80}")

if __name__ == '__main__':
    bulk_insert_insights('data/investment_insights_all.json')
