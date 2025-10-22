"""전체 블로그 크롤링 (1800개) - 백그라운드 실행용"""
import sys
import logging
from src.tools.blog_crawler import NaverBlogCrawler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/crawl_all_blogs.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    blog_id = "ranto28"
    max_posts = 1877
    output_file = "data/blog_raw_all.json"

    logger.info(f"🚀 전체 블로그 크롤링 시작: {blog_id}")
    logger.info(f"  - 최대 개수: {max_posts}개")
    logger.info(f"  - 저장 경로: {output_file}")

    crawler = NaverBlogCrawler(blog_id)

    try:
        posts = crawler.crawl_all(max_posts=max_posts, save_path=output_file)
        logger.info(f"✅ 크롤링 완료: {len(posts)}개 수집")
    except Exception as e:
        logger.error(f"❌ 크롤링 실패: {e}")
        sys.exit(1)
    finally:
        crawler.close()
