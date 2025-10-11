"""네이버 블로그 크롤링 실행 스크립트"""
import sys
from src.tools.blog_crawler import NaverBlogCrawler
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    blog_id = "ranto28"

    # 크롤링할 글 개수 (기본: 100개, 전체: 1877개)
    max_posts = int(sys.argv[1]) if len(sys.argv) > 1 else 100

    output_file = f"data/blog_raw_{max_posts}.json"

    logger.info(f"=" * 80)
    logger.info(f"블로그 크롤링 시작")
    logger.info(f"  - 블로그 ID: {blog_id}")
    logger.info(f"  - 최대 글 수: {max_posts}개")
    logger.info(f"  - 출력 파일: {output_file}")
    logger.info(f"  - 예상 시간: 약 {max_posts * 1.5 / 60:.1f}분")
    logger.info(f"=" * 80)

    crawler = NaverBlogCrawler(blog_id)

    try:
        posts = crawler.crawl_all(max_posts=max_posts, save_path=output_file)

        logger.info(f"\n" + "=" * 80)
        logger.info(f"✅ 크롤링 완료!")
        logger.info(f"  - 성공: {len(posts)}개")
        logger.info(f"  - 저장: {output_file}")
        logger.info(f"=" * 80)

        # 통계 출력
        if posts:
            avg_title_len = sum(len(p['title']) for p in posts) / len(posts)
            avg_content_len = sum(len(p['content']) for p in posts) / len(posts)

            logger.info(f"\n📊 통계:")
            logger.info(f"  - 평균 제목 길이: {avg_title_len:.0f}자")
            logger.info(f"  - 평균 본문 길이: {avg_content_len:.0f}자")

            # 샘플 3개 출력
            logger.info(f"\n📝 샘플 3개:")
            for i, post in enumerate(posts[:3], 1):
                logger.info(f"\n{i}. {post['title']}")
                logger.info(f"   날짜: {post['date']}")
                logger.info(f"   본문: {post['content'][:100]}...")

    finally:
        crawler.close()
