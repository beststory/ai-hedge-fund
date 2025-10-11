"""블로그 글에서 투자 인사이트 메타데이터 추출 (테스트용 - 5개만)"""
import json
import os
from typing import List, Dict
import logging
from src.utils.llm import call_llm
from src.llm.models import ModelProvider
from pydantic import BaseModel, Field

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InsightMetadata(BaseModel):
    """투자 인사이트 메타데이터"""
    sector: str = Field(description="산업 섹터 (예: 기술/양자컴퓨팅, 거시경제/금리, 에너지/원자력)")
    sentiment: str = Field(description="투자 감성 (매우 긍정적/긍정적/조심스럽게 긍정적/중립/주의/부정적)")
    keywords: List[str] = Field(description="주요 키워드 5-10개 (종목명, 주제, 기술 등)")


def extract_metadata_from_post(post: Dict, index: int, total: int) -> Dict:
    """개별 글에서 메타데이터 추출"""
    title = post['title']
    content = post['content']

    # 본문이 너무 길면 앞부분만 사용 (약 2000자)
    content_sample = content[:2000] if len(content) > 2000 else content

    prompt = f"""다음은 투자 관련 블로그 글입니다. 이 글을 분석하여 투자 인사이트 메타데이터를 추출해주세요.

제목: {title}

본문:
{content_sample}

위 글을 분석하여 다음 정보를 추출하세요:
1. sector: 어떤 산업 분야인지 (예: "기술/양자컴퓨팅", "거시경제/금리", "에너지/원자력", "기술/반도체")
2. sentiment: 투자 감성 (매우 긍정적, 긍정적, 조심스럽게 긍정적, 중립, 주의, 부정적 중 선택)
3. keywords: 주요 키워드 5-10개 (종목명, 기술명, 주제 등을 배열로)

JSON 형식으로 응답하세요."""

    try:
        logger.info(f"[{index}/{total}] 메타데이터 추출 중: {title[:50]}...")

        # LLM 호출 (Ollama 로컬 사용 - Mistral Small 3.1)
        metadata = call_llm(
            prompt=prompt,
            model_name="mistral-small3.1",
            model_provider=ModelProvider.OLLAMA,
            pydantic_model=InsightMetadata
        )

        logger.info(f"  ✅ 섹터: {metadata.sector}, 감성: {metadata.sentiment}")
        logger.info(f"  키워드: {', '.join(metadata.keywords[:5])}...")

        return {
            "sector": metadata.sector,
            "sentiment": metadata.sentiment,
            "keywords": metadata.keywords
        }

    except Exception as e:
        logger.error(f"  ❌ 메타데이터 추출 실패: {e}")
        # 기본값 반환
        return {
            "sector": "기타",
            "sentiment": "중립",
            "keywords": [title]
        }


if __name__ == '__main__':
    # 크롤링된 원본 데이터 로드
    raw_file = "data/blog_raw_100.json"

    logger.info(f"원본 데이터 로드 중: {raw_file}")
    with open(raw_file, 'r', encoding='utf-8') as f:
        raw_posts = json.load(f)

    # 처음 5개만 테스트
    test_posts = raw_posts[:5]
    logger.info(f"테스트: {len(test_posts)}개 글\n")

    logger.info(f"=" * 80)
    logger.info(f"투자 인사이트 메타데이터 추출 시작 (테스트)")
    logger.info(f"=" * 80 + "\n")

    insights = []
    for i, post in enumerate(test_posts, 1):
        try:
            # 메타데이터 추출
            metadata = extract_metadata_from_post(post, i, len(test_posts))

            # 결과 저장
            insight = {
                "id": i,
                "date": post['date'],
                "title": post['title'],
                "sector": metadata['sector'],
                "sentiment": metadata['sentiment'],
                "keywords": metadata['keywords'],
            }

            insights.append(insight)

        except Exception as e:
            logger.error(f"[{i}/{len(test_posts)}] 변환 실패: {e}")

    logger.info(f"\n" + "=" * 80)
    logger.info(f"✅ 테스트 완료!")
    logger.info(f"  - 성공: {len(insights)}개")
    logger.info(f"=" * 80)

    # 결과 출력
    if insights:
        logger.info(f"\n📝 결과:")
        for insight in insights:
            logger.info(f"\n{insight['id']}. {insight['title']}")
            logger.info(f"   섹터: {insight['sector']}")
            logger.info(f"   감성: {insight['sentiment']}")
            logger.info(f"   키워드: {', '.join(insight['keywords'][:5])}")
