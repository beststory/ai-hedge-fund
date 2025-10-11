"""Supabase 벡터 검색 테스트"""
from src.tools.supabase_rag import SupabaseRAG
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info("\n" + "=" * 80)
    logger.info("🔍 Supabase 벡터 검색 테스트")
    logger.info("=" * 80)

    rag = SupabaseRAG()

    # 테스트 1: 양자컴퓨팅 검색
    logger.info("\n[테스트 1] 양자컴퓨팅 관련 검색")
    query = "양자컴퓨팅 기술과 IONQ, RGTI 투자"
    results = rag.search_similar(query, top_k=3)

    if results:
        for i, result in enumerate(results, 1):
            logger.info(f"\n{i}. {result['title']}")
            logger.info(f"   유사도: {result['similarity']:.4f}")
            logger.info(f"   섹터: {result['sector']}")
            logger.info(f"   감성: {result['sentiment']}")
    else:
        logger.warning("검색 결과 없음")

    # 테스트 2: AI 반도체 검색
    logger.info("\n[테스트 2] AI 반도체 관련 검색")
    query = "NVIDIA와 AI 반도체 시장 전망"
    results = rag.search_similar(query, top_k=3)

    if results:
        for i, result in enumerate(results, 1):
            logger.info(f"\n{i}. {result['title']}")
            logger.info(f"   유사도: {result['similarity']:.4f}")
            logger.info(f"   섹터: {result['sector']}")
    else:
        logger.warning("검색 결과 없음")

    # 테스트 3: 우주 산업 검색
    logger.info("\n[테스트 3] 우주 산업 관련 검색")
    query = "우주 산업과 위성통신 투자 기회"
    results = rag.search_similar(query, top_k=3)

    if results:
        for i, result in enumerate(results, 1):
            logger.info(f"\n{i}. {result['title']}")
            logger.info(f"   유사도: {result['similarity']:.4f}")
    else:
        logger.warning("검색 결과 없음")

    logger.info("\n" + "=" * 80)
    logger.info("✅ Supabase 벡터 검색 테스트 완료")
    logger.info("=" * 80 + "\n")
