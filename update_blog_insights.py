"""블로그 신규 글 자동 업데이트 스크립트 - 매일 새벽 3시 실행"""
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from src.tools.blog_crawler import NaverBlogCrawler
from src.tools.supabase_rag import SupabaseRAG
from extract_insights import extract_metadata_from_post

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/update_blog_insights.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_latest_post_date_from_supabase() -> Optional[str]:
    """Supabase에서 가장 최근 글의 날짜 조회"""
    try:
        rag = SupabaseRAG()

        # investment_insights 테이블에서 최신 날짜 조회
        response = rag.client.table('investment_insights') \
            .select('date') \
            .order('date', desc=True) \
            .limit(1) \
            .execute()

        if response.data and len(response.data) > 0:
            latest_date = response.data[0]['date']
            logger.info(f"📅 Supabase 최신 글 날짜: {latest_date}")
            return latest_date
        else:
            logger.warning("⚠️  Supabase에 데이터가 없습니다.")
            return None

    except Exception as e:
        logger.error(f"❌ Supabase 최신 날짜 조회 실패: {e}")
        return None


def parse_relative_time(date_str: str) -> Optional[datetime]:
    """상대 시간 문자열을 datetime 객체로 변환"""
    if not date_str:
        return None

    try:
        # 절대 시간 형식 (예: "2025. 9. 9. 11:00")
        if '.' in date_str and ':' in date_str:
            return datetime.strptime(date_str.strip(), '%Y. %m. %d. %H:%M')

        # 상대 시간 형식 (예: "6시간 전", "3일 전")
        now = datetime.now()
        if '시간 전' in date_str:
            hours = int(date_str.replace('시간 전', '').strip())
            return now - timedelta(hours=hours)
        elif '일 전' in date_str:
            days = int(date_str.replace('일 전', '').strip())
            return now - timedelta(days=days)
        elif '분 전' in date_str:
            minutes = int(date_str.replace('분 전', '').strip())
            return now - timedelta(minutes=minutes)

        return None
    except Exception as e:
        logger.warning(f"⚠️  날짜 파싱 실패: {date_str} - {e}")
        return None


def crawl_new_posts(blog_id: str, since_date: Optional[str] = None) -> List[Dict]:
    """신규 블로그 글 크롤링"""
    logger.info(f"🔍 신규 글 크롤링 시작 (블로그: {blog_id})")
    if since_date:
        logger.info(f"  - 기준 날짜: {since_date} 이후")

    crawler = NaverBlogCrawler(blog_id)
    new_posts = []

    try:
        # 최근 100개 글만 체크 (보통 하루에 몇 개 안 올라옴)
        all_posts = crawler.crawl_all(max_posts=100, save_path=None)

        if not since_date:
            # 기준 날짜가 없으면 모두 새 글
            new_posts = all_posts
        else:
            # 기준 날짜를 datetime으로 변환
            since_datetime = parse_relative_time(since_date)

            if not since_datetime:
                # 파싱 실패 시 모든 글을 새 글로 간주
                logger.warning("⚠️  기준 날짜 파싱 실패, 모든 글을 새 글로 간주합니다.")
                new_posts = all_posts
            else:
                # 기준 날짜 이후 글만 필터링
                for post in all_posts:
                    post_date_str = post.get('date', '')
                    post_datetime = parse_relative_time(post_date_str)

                    if post_datetime and post_datetime > since_datetime:
                        new_posts.append(post)
                        logger.debug(f"  - 신규 글 발견: {post['title'][:50]}... ({post_date_str})")

        logger.info(f"✅ 신규 글 {len(new_posts)}개 발견")

    except Exception as e:
        logger.error(f"❌ 크롤링 실패: {e}")
    finally:
        crawler.close()

    return new_posts


def process_and_upload_new_posts(new_posts: List[Dict]) -> Dict[str, int]:
    """신규 글 메타데이터 추출 및 Supabase 업로드"""
    if not new_posts:
        logger.info("ℹ️  신규 글이 없습니다.")
        return {"success": 0, "failed": 0}

    logger.info(f"\n{'=' * 80}")
    logger.info(f"🤖 신규 글 메타데이터 추출 및 업로드 시작: {len(new_posts)}개")
    logger.info(f"{'=' * 80}\n")

    rag = SupabaseRAG()
    success_count = 0
    failed_count = 0

    # 최신 ID 조회 (이어서 번호 부여)
    try:
        response = rag.client.table('investment_insights') \
            .select('id') \
            .order('id', desc=True) \
            .limit(1) \
            .execute()

        next_id = response.data[0]['id'] + 1 if response.data else 1
    except:
        next_id = 1

    for i, post in enumerate(new_posts, 1):
        try:
            # 메타데이터 추출
            logger.info(f"[{i}/{len(new_posts)}] 처리 중: {post['title'][:50]}...")
            metadata = extract_metadata_from_post(post, i, len(new_posts))

            # 투자 인사이트 형식으로 변환
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
            success_count += 1
            next_id += 1

            logger.info(f"  ✅ 업로드 완료: {post['title'][:50]}...")
            logger.info(f"     섹터: {metadata['sector']}, 감성: {metadata['sentiment']}")

        except Exception as e:
            failed_count += 1
            logger.error(f"  ❌ 처리 실패: {e}")

    logger.info(f"\n{'=' * 80}")
    logger.info(f"✅ 신규 글 업데이트 완료!")
    logger.info(f"  - 성공: {success_count}개")
    logger.info(f"  - 실패: {failed_count}개")
    logger.info(f"{'=' * 80}\n")

    return {"success": success_count, "failed": failed_count}


def main():
    """메인 실행 함수"""
    start_time = datetime.now()
    logger.info(f"\n{'=' * 80}")
    logger.info(f"🚀 블로그 신규 글 업데이트 시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'=' * 80}\n")

    blog_id = "ranto28"

    # 1. Supabase에서 최신 글 날짜 조회
    latest_date = get_latest_post_date_from_supabase()

    # 2. 신규 글 크롤링
    new_posts = crawl_new_posts(blog_id, since_date=latest_date)

    # 3. 신규 글 처리 및 업로드
    result = process_and_upload_new_posts(new_posts)

    # 실행 시간 계산
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    logger.info(f"\n{'=' * 80}")
    logger.info(f"🎉 업데이트 작업 완료!")
    logger.info(f"  - 실행 시간: {duration:.1f}초")
    logger.info(f"  - 신규 글: {len(new_posts)}개")
    logger.info(f"  - 성공: {result['success']}개")
    logger.info(f"  - 실패: {result['failed']}개")
    logger.info(f"{'=' * 80}\n")


if __name__ == '__main__':
    main()
