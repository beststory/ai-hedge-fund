"""네이버 블로그 크롤러 - 투자 인사이트 수집"""
import requests
from bs4 import BeautifulSoup
import time
import json
from datetime import datetime
from typing import List, Dict
import logging
from urllib.parse import unquote_plus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NaverBlogCrawler:
    """네이버 블로그 크롤러 (모바일 버전 사용)"""

    def __init__(self, blog_id: str):
        self.blog_id = blog_id
        self.base_url = f"https://blog.naver.com/{blog_id}"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
        })

    def get_post_list(self, max_posts: int = 1877) -> List[str]:
        """블로그의 모든 글 목록 가져오기"""
        logger.info(f"📚 블로그 글 목록 수집 시작... (최대 {max_posts}개)")

        post_urls = []
        page = 1

        while len(post_urls) < max_posts:
            try:
                # 네이버 블로그 목록 API 사용 (JSON 응답)
                list_url = f"https://blog.naver.com/PostTitleListAsync.naver?blogId={self.blog_id}&viewdate=&currentPage={page}&categoryNo=&parentCategoryNo=&countPerPage=30"

                response = self.session.get(list_url, timeout=10)

                if response.status_code != 200:
                    logger.warning(f"페이지 {page} 로드 실패: {response.status_code}")
                    break

                # JSON 파싱 (잘못된 이스케이프 수정)
                fixed_text = response.text.replace("\\'", "'")
                data = json.loads(fixed_text)

                if data.get('resultCode') != 'S':
                    logger.warning(f"페이지 {page} API 오류: {data.get('resultMessage')}")
                    break

                post_list = data.get('postList', [])

                if not post_list:
                    logger.info(f"페이지 {page}에서 더 이상 글을 찾을 수 없습니다.")
                    break

                # 글 URL 생성
                for post in post_list:
                    log_no = post.get('logNo')
                    if log_no:
                        post_url = f"https://blog.naver.com/{self.blog_id}/{log_no}"
                        post_urls.append(post_url)

                logger.info(f"페이지 {page}: {len(post_list)}개 글 발견 (총 {len(post_urls)}개)")

                page += 1
                time.sleep(0.5)  # Rate limiting

            except Exception as e:
                logger.error(f"페이지 {page} 크롤링 오류: {e}")
                break

        logger.info(f"✅ 총 {len(post_urls)}개 글 URL 수집 완료")
        return post_urls[:max_posts]

    def get_post_content(self, post_url: str) -> Dict:
        """개별 글 내용 가져오기"""
        try:
            # 모바일 버전 URL 사용
            log_no = post_url.split('/')[-1]
            mobile_url = f"https://m.blog.naver.com/{self.blog_id}/{log_no}"

            response = self.session.get(mobile_url, timeout=10)

            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # 제목 추출 (se-documentTitle 클래스 사용)
            title = "제목 없음"
            title_container = soup.find('div', class_='se-documentTitle')
            if title_container:
                title_span = title_container.find('span', class_=lambda x: x and 'se-fs-' in str(x))
                if title_span:
                    title = title_span.get_text(strip=True)
                else:
                    # 대체 방법: p 태그에서 첫 번째 텍스트
                    content_elem = title_container.find('div', class_='se-component-content')
                    if content_elem:
                        p_tag = content_elem.find('p')
                        if p_tag:
                            title = p_tag.get_text(strip=True)

            # 본문 추출 (se-text 컴포넌트들에서)
            content_parts = []
            post_view = soup.find('div', class_='_postView')
            if post_view:
                main_container = post_view.find('div', class_='se-main-container')
                if main_container:
                    # se-text 클래스를 가진 컴포넌트들 찾기
                    text_components = main_container.find_all('div', class_='se-text')
                    for component in text_components:
                        text = component.get_text(separator='\n', strip=True)
                        # 의미 있는 길이의 텍스트만 추가
                        if text and len(text) > 10:
                            content_parts.append(text)

            content = '\n\n'.join(content_parts)

            # 작성일 추출
            date_str = ""
            # 방법 1: blog_date 클래스
            date_elem = soup.find('span', class_='blog_date')
            if date_elem:
                date_str = date_elem.get_text(strip=True)

            # 방법 2: se-publishDate 클래스 (documentTitle 안)
            if not date_str and title_container:
                date_p = title_container.find_all('p')
                if len(date_p) > 1:
                    date_str = date_p[1].get_text(strip=True)

            return {
                'url': post_url,
                'title': title,
                'content': content,
                'date': date_str,
                'crawled_at': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"글 내용 추출 실패 ({post_url}): {e}")
            return None

    def crawl_all(self, max_posts: int = 100, save_path: str = None) -> List[Dict]:
        """전체 블로그 크롤링"""
        logger.info(f"🚀 블로그 크롤링 시작: {self.blog_id}")

        # 1. 글 목록 가져오기
        post_urls = self.get_post_list(max_posts)

        if not post_urls:
            logger.error("글 목록을 가져올 수 없습니다.")
            return []

        # 2. 각 글 내용 크롤링
        posts = []
        failed_count = 0

        for i, url in enumerate(post_urls, 1):
            logger.info(f"[{i}/{len(post_urls)}] 크롤링 중: {url}")

            post_data = self.get_post_content(url)

            if post_data:
                posts.append(post_data)
                logger.info(f"  ✅ 제목: {post_data['title'][:50]}...")
            else:
                failed_count += 1
                logger.warning(f"  ❌ 실패")

            # Rate limiting
            time.sleep(1)

            # 진행 상황 저장 (100개마다)
            if save_path and i % 100 == 0:
                self._save_progress(posts, save_path)

        logger.info(f"✅ 크롤링 완료: {len(posts)}개 성공, {failed_count}개 실패")

        # 최종 저장
        if save_path:
            self._save_progress(posts, save_path)

        return posts

    def _save_progress(self, posts: List[Dict], save_path: str):
        """진행 상황 저장"""
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(posts, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 진행 상황 저장: {save_path} ({len(posts)}개)")
        except Exception as e:
            logger.error(f"저장 실패: {e}")

    def close(self):
        """세션 종료"""
        self.session.close()


def test_crawler():
    """크롤러 테스트"""
    crawler = NaverBlogCrawler("ranto28")

    try:
        # 먼저 10개만 테스트
        logger.info("🧪 10개 글 테스트 크롤링...")
        posts = crawler.crawl_all(max_posts=10, save_path="/tmp/blog_test.json")

        if posts:
            logger.info(f"\n📊 크롤링 결과:")
            logger.info(f"  - 총 글 수: {len(posts)}")
            logger.info(f"  - 첫 번째 글 제목: {posts[0]['title']}")
            logger.info(f"  - 본문 길이 평균: {sum(len(p['content']) for p in posts) / len(posts):.0f}자")

            # 샘플 출력
            logger.info(f"\n📄 첫 번째 글 샘플:")
            logger.info(f"  제목: {posts[0]['title']}")
            logger.info(f"  날짜: {posts[0]['date']}")
            logger.info(f"  내용 (처음 200자): {posts[0]['content'][:200]}...")

            return True
        else:
            logger.error("크롤링 실패")
            return False
    finally:
        crawler.close()


if __name__ == '__main__':
    test_crawler()
