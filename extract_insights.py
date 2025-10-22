"""블로그 글에서 투자 인사이트 메타데이터 추출 및 Supabase 자동 삽입"""
import json
import os
from typing import List, Dict
import logging
from src.utils.llm import call_llm
from src.llm.models import ModelProvider
from src.tools.supabase_rag import SupabaseRAG
from pydantic import BaseModel, Field

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InsightMetadata(BaseModel):
    """투자 인사이트 메타데이터"""
    sector: str = Field(description="산업 섹터 하나만 선택 (예: '기술/양자컴퓨팅', '거시경제/금리', '에너지/원자력', '기술/반도체')")
    sentiment: str = Field(description="투자 감성 하나만 선택 (매우 긍정적, 긍정적, 조심스럽게 긍정적, 중립, 주의, 부정적)")
    keywords: List[str] = Field(description="주요 키워드 5-10개를 문자열 배열로 (예: ['삼성전자', 'HBM', '반도체'])")


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
1. sector: 가장 주요한 산업 분야 하나만 선택 (문자열)
   예시: "기술/양자컴퓨팅", "거시경제/금리", "에너지/원자력", "기술/반도체", "금융/은행"
   주의: 반드시 하나의 문자열만 반환하세요.

2. sentiment: 투자 감성 하나만 선택 (문자열)
   선택지: "매우 긍정적", "긍정적", "조심스럽게 긍정적", "중립", "주의", "부정적"
   주의: 반드시 하나의 문자열만 반환하세요.

3. keywords: 주요 키워드 5-10개를 문자열 배열로
   예시: ["삼성전자", "HBM", "반도체", "AI", "엔비디아"]

JSON 형식으로 응답하세요:
{{"sector": "문자열", "sentiment": "문자열", "keywords": ["키워드1", "키워드2", ...]}}
"""

    try:
        logger.info(f"[{index}/{total}] 메타데이터 추출 중: {title[:50]}...")

        # LLM 호출 (Ollama 로컬 사용 - Mistral Small 3.1)
        metadata = call_llm(
            prompt=prompt,
            model_name="mistral-small3.1",
            model_provider=ModelProvider.OLLAMA,
            pydantic_model=InsightMetadata
        )

        # sector와 sentiment가 리스트로 반환된 경우 첫 번째 요소만 사용
        sector = metadata.sector if isinstance(metadata.sector, str) else (metadata.sector[0] if metadata.sector else "기타")
        sentiment = metadata.sentiment if isinstance(metadata.sentiment, str) else (metadata.sentiment[0] if metadata.sentiment else "중립")
        keywords = metadata.keywords if isinstance(metadata.keywords, list) else [str(metadata.keywords)]

        logger.info(f"  ✅ 섹터: {sector}, 감성: {sentiment}")
        logger.info(f"  키워드: {', '.join(keywords[:5])}...")

        return {
            "sector": sector,
            "sentiment": sentiment,
            "keywords": keywords
        }

    except Exception as e:
        logger.error(f"  ❌ 메타데이터 추출 실패: {e}")
        # 기본값 반환
        return {
            "sector": "기타",
            "sentiment": "중립",
            "keywords": [title]
        }


def convert_to_investment_insights(raw_posts: List[Dict], output_file: str, enable_supabase: bool = True):
    """크롤링 데이터를 investment_insights.json 형식으로 변환 및 Supabase 자동 삽입"""
    logger.info(f"\n" + "=" * 80)
    logger.info(f"투자 인사이트 메타데이터 추출 및 Supabase 삽입 시작")
    logger.info(f"  - 입력: {len(raw_posts)}개 글")
    logger.info(f"  - 출력: {output_file}")
    logger.info(f"  - Supabase 자동 삽입: {'활성화' if enable_supabase else '비활성화'}")
    logger.info(f"=" * 80 + "\n")

    # Supabase RAG 초기화
    rag = SupabaseRAG() if enable_supabase else None

    insights = []
    failed_count = 0
    supabase_success = 0
    supabase_failed = 0

    for i, post in enumerate(raw_posts, 1):
        try:
            # 메타데이터 추출
            metadata = extract_metadata_from_post(post, i, len(raw_posts))

            # 본문 전체 사용 (Supabase 저장용)
            content_full = post['content'].strip()

            # 투자 인사이트 형식으로 변환
            insight = {
                "id": i,
                "date": post['date'],
                "title": post['title'],
                "content": content_full,
                "sector": metadata['sector'],
                "sentiment": metadata['sentiment'],
                "keywords": metadata['keywords'],
                "url": post['url']
            }

            insights.append(insight)

            # Supabase 자동 삽입
            if rag:
                try:
                    rag.insert_insight(insight)
                    supabase_success += 1
                    logger.info(f"  ✅ Supabase 삽입 완료 ({supabase_success}/{i})")
                except Exception as e:
                    supabase_failed += 1
                    logger.error(f"  ❌ Supabase 삽입 실패: {e}")

            # 10개마다 중간 저장
            if i % 10 == 0:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(insights, f, ensure_ascii=False, indent=2)
                logger.info(f"  💾 중간 저장 완료: {i}개 처리")

        except Exception as e:
            logger.error(f"[{i}/{len(raw_posts)}] 변환 실패: {e}")
            failed_count += 1

    # 최종 JSON 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(insights, f, ensure_ascii=False, indent=2)

    logger.info(f"\n" + "=" * 80)
    logger.info(f"✅ 변환 완료!")
    logger.info(f"  - 성공: {len(insights)}개")
    logger.info(f"  - 실패: {failed_count}개")
    if rag:
        logger.info(f"  - Supabase 삽입 성공: {supabase_success}개")
        logger.info(f"  - Supabase 삽입 실패: {supabase_failed}개")
    logger.info(f"  - 저장: {output_file}")
    logger.info(f"=" * 80)

    return insights


if __name__ == '__main__':
    # 크롤링된 원본 데이터 로드
    raw_file = "data/blog_raw_100.json"
    output_file = "data/investment_insights_100.json"

    logger.info(f"원본 데이터 로드 중: {raw_file}")
    with open(raw_file, 'r', encoding='utf-8') as f:
        raw_posts = json.load(f)

    logger.info(f"로드 완료: {len(raw_posts)}개 글\n")

    # 변환 실행
    insights = convert_to_investment_insights(raw_posts, output_file)

    # 샘플 출력
    if insights:
        logger.info(f"\n📝 샘플 3개:")
        for insight in insights[:3]:
            logger.info(f"\n{insight['id']}. {insight['title']}")
            logger.info(f"   섹터: {insight['sector']}")
            logger.info(f"   감성: {insight['sentiment']}")
            logger.info(f"   키워드: {', '.join(insight['keywords'][:5])}")
