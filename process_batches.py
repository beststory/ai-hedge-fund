"""크롤링된 블로그를 100개씩 배치로 나누어 인사이트 추출 - 백그라운드 실행용"""
import json
import sys
import logging
from pathlib import Path
from extract_insights import convert_to_investment_insights

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/process_batches.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def split_into_batches(all_posts, batch_size=100):
    """데이터를 배치로 나누기"""
    batches = []
    for i in range(0, len(all_posts), batch_size):
        batches.append(all_posts[i:i+batch_size])
    return batches

if __name__ == '__main__':
    input_file = "data/blog_raw_all.json"
    batch_size = 100

    # 입력 파일 확인
    if not Path(input_file).exists():
        logger.error(f"입력 파일을 찾을 수 없습니다: {input_file}")
        logger.info("먼저 crawl_all_blogs.py를 실행하세요.")
        sys.exit(1)

    # 전체 데이터 로드
    logger.info(f"📖 데이터 로드 중: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        all_posts = json.load(f)

    logger.info(f"✅ 총 {len(all_posts)}개 블로그 글 로드 완료")

    # 배치로 나누기
    batches = split_into_batches(all_posts, batch_size)
    logger.info(f"📦 {len(batches)}개 배치로 분할 완료 (배치당 {batch_size}개)")

    # 각 배치 처리
    all_insights = []
    for i, batch in enumerate(batches, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"배치 {i}/{len(batches)} 처리 중 (글 {(i-1)*batch_size+1} ~ {(i-1)*batch_size+len(batch)})")
        logger.info(f"{'='*80}\n")

        try:
            # 배치별 출력 파일
            batch_output = f"data/investment_insights_batch_{i}.json"

            # 인사이트 추출 및 Supabase 삽입
            insights = convert_to_investment_insights(
                batch,
                batch_output,
                enable_supabase=True  # Supabase 자동 삽입 활성화
            )

            all_insights.extend(insights)
            logger.info(f"✅ 배치 {i} 완료: {len(insights)}개 인사이트 추출")

        except Exception as e:
            logger.error(f"❌ 배치 {i} 처리 실패: {e}")
            continue

    # 전체 결과 저장
    final_output = "data/investment_insights_all.json"
    with open(final_output, 'w', encoding='utf-8') as f:
        json.dump(all_insights, f, ensure_ascii=False, indent=2)

    logger.info(f"\n{'='*80}")
    logger.info(f"🎉 전체 처리 완료!")
    logger.info(f"  - 총 인사이트: {len(all_insights)}개")
    logger.info(f"  - 최종 파일: {final_output}")
    logger.info(f"{'='*80}")
