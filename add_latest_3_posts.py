"""최신 3개 블로그 글을 크롤링하여 추가"""
import sys
sys.path.append('/home/harvis/ai-hedge-fund')

from src.tools.blog_crawler import NaverBlogCrawler
from src.tools.supabase_rag import SupabaseRAG
from extract_insights import extract_metadata_from_post
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def add_latest_posts():
    """최신 3개 글을 크롤링하여 추가"""
    blog_id = "ranto28"

    logger.info("=" * 80)
    logger.info("최신 3개 글 크롤링 및 추가")
    logger.info("=" * 80)

    # 1. 크롤링
    logger.info(f"\n1. 블로그 크롤링: {blog_id}")
    crawler = NaverBlogCrawler(blog_id)

    try:
        posts = crawler.crawl_all(max_posts=3, save_path=None)
        logger.info(f"✅ {len(posts)}개 글 크롤링 완료")
    finally:
        crawler.close()

    if not posts:
        logger.error("❌ 크롤링된 글이 없습니다")
        return

    # 2. Supabase에서 최신 ID 확인
    logger.info("\n2. Supabase 최신 ID 확인")
    rag = SupabaseRAG()

    response = rag.client.table('investment_insights') \
        .select('id') \
        .order('id', desc=True) \
        .limit(1) \
        .execute()

    next_id = response.data[0]['id'] + 1 if response.data else 1
    logger.info(f"다음 ID: {next_id}")

    # 3. 메타데이터 추출 및 추가
    logger.info(f"\n3. {len(posts)}개 글 메타데이터 추출 및 추가")
    logger.info("=" * 80)

    success_count = 0

    for i, post in enumerate(posts, 1):
        try:
            logger.info(f"\n[{i}/{len(posts)}] 처리 중: {post['title'][:60]}...")

            # 메타데이터 추출
            metadata = extract_metadata_from_post(post, i, len(posts))

            # 인사이트 형식으로 변환
            insight = {
                "id": next_id,
                "date": post['date'],
                "title": post['title'],
                "content": post['content'].strip(),
                "sector": metadata['sector'],
                "sentiment": metadata['sentiment'],
                "keywords": metadata['keywords'],
                "url": post['url']
            }

            # Supabase 삽입
            rag.insert_insight(insight)

            logger.info(f"  ✅ ID {next_id} 추가 완료")
            logger.info(f"     섹터: {metadata['sector']}, 감성: {metadata['sentiment']}")

            success_count += 1
            next_id += 1

        except Exception as e:
            logger.error(f"  ❌ 처리 실패: {e}")

    logger.info("\n" + "=" * 80)
    logger.info(f"✅ 완료: {success_count}/{len(posts)}개 추가 성공")
    logger.info("=" * 80)

    return success_count

if __name__ == '__main__':
    add_latest_posts()
