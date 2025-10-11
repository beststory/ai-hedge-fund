"""투자 인사이트 RAG 시스템 - 키워드 기반 검색"""
import json
import os
from typing import List, Dict
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InvestmentRAG:
    """투자 인사이트 검색 시스템"""

    def __init__(self, data_path: str = None):
        if data_path is None:
            # 프로젝트 루트 기준 절대 경로
            import os
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_path = os.path.join(project_root, "data", "investment_insights.json")

        self.data_path = data_path
        self.insights = []
        self.load_data()

    def load_data(self):
        """인사이트 데이터 로드"""
        try:
            if not os.path.exists(self.data_path):
                logger.warning(f"데이터 파일이 없습니다: {self.data_path}")
                return

            with open(self.data_path, 'r', encoding='utf-8') as f:
                self.insights = json.load(f)

            logger.info(f"✅ {len(self.insights)}개 인사이트 로드 완료")

        except Exception as e:
            logger.error(f"데이터 로드 실패: {e}")
            self.insights = []

    def search_by_keywords(self, keywords: List[str], top_k: int = 3) -> List[Dict]:
        """키워드 기반 검색"""
        if not self.insights:
            return []

        # 각 인사이트에 점수 매기기
        scored_insights = []

        for insight in self.insights:
            score = 0

            # 제목, 내용, 키워드에서 매칭
            text = f"{insight['title']} {insight['content']} {' '.join(insight['keywords'])}".lower()

            for keyword in keywords:
                keyword_lower = keyword.lower()
                # 키워드 필드에 있으면 높은 점수
                if keyword_lower in [k.lower() for k in insight['keywords']]:
                    score += 3
                # 제목에 있으면 중간 점수
                elif keyword_lower in insight['title'].lower():
                    score += 2
                # 본문에 있으면 낮은 점수
                elif keyword_lower in insight['content'].lower():
                    score += 1

            if score > 0:
                scored_insights.append({
                    'insight': insight,
                    'score': score
                })

        # 점수 순 정렬
        scored_insights.sort(key=lambda x: x['score'], reverse=True)

        # 상위 k개 반환
        return [item['insight'] for item in scored_insights[:top_k]]

    def search_by_sector(self, sector: str, top_k: int = 3) -> List[Dict]:
        """섹터별 검색"""
        matches = [
            insight for insight in self.insights
            if sector.lower() in insight['sector'].lower()
        ]
        return matches[:top_k]

    def get_relevant_insights(self, symbol: str, sector: str = None, top_k: int = 3) -> List[Dict]:
        """종목 심볼 기반 관련 인사이트 가져오기"""

        # 종목 심볼 기반 키워드 매핑
        symbol_keywords = {
            # 양자컴퓨팅
            'IONQ': ['양자컴퓨팅', 'IONQ', '기술주'],
            'RGTI': ['양자컴퓨팅', 'RGTI', '기술주'],
            'QBTS': ['양자컴퓨팅', 'QBTS', '기술주'],

            # AI 반도체
            'NVDA': ['AI', '반도체', 'NVIDIA', '기술주'],
            'AMD': ['AI', '반도체', 'AMD', '기술주'],
            'MRVL': ['AI', '반도체', 'MRVL', '기술주'],
            'AVGO': ['AI', '반도체', 'AVGO', '기술주'],
            'SMCI': ['AI', '반도체', '서버', '기술주'],

            # 우주/위성
            'RKLB': ['우주산업', 'RKLB', '위성통신'],
            'ASTS': ['우주산업', 'ASTS', '위성통신'],
            'PL': ['우주산업', 'PL', '위성통신'],

            # 원자력/에너지
            'UEC': ['원자력', '우라늄', 'UEC', '에너지'],
            'CCJ': ['원자력', '우라늄', 'CCJ', '에너지'],

            # 빅테크
            'MSFT': ['클라우드', 'AI', 'MSFT', '빅테크'],
            'GOOGL': ['클라우드', 'AI', 'GOOGL', '빅테크'],
            'GOOG': ['클라우드', 'AI', 'GOOGL', '빅테크'],
            'AMZN': ['클라우드', 'AI', 'AMZN', '빅테크'],
            'AAPL': ['기술주', 'AAPL', '빅테크'],
            'META': ['AI', 'META', '빅테크'],

            # 사이버보안
            'CRWD': ['사이버보안', 'CRWD', '방어주'],
            'PANW': ['사이버보안', 'PANW', '방어주'],
            'ZS': ['사이버보안', 'ZS', '방어주'],

            # 전기차
            'TSLA': ['전기차', '테슬라', 'TSLA']
        }

        # 심볼에 해당하는 키워드 가져오기
        keywords = symbol_keywords.get(symbol, [symbol])

        # 섹터 정보가 있으면 추가
        if sector:
            keywords.append(sector)

        logger.info(f"🔍 {symbol} 검색 키워드: {keywords}")

        # 키워드 기반 검색
        results = self.search_by_keywords(keywords, top_k=top_k)

        logger.info(f"✅ {len(results)}개 관련 인사이트 발견")

        return results

    def format_insights_for_llm(self, insights: List[Dict]) -> str:
        """LLM에 전달할 형식으로 포맷팅"""
        if not insights:
            return ""

        formatted = "## 투자 인사이트 참고 자료\n\n"

        for i, insight in enumerate(insights, 1):
            formatted += f"### {i}. {insight['title']} ({insight['date']})\n"
            formatted += f"**섹터**: {insight['sector']}\n"
            formatted += f"**전망**: {insight['sentiment']}\n\n"
            formatted += f"{insight['content']}\n\n"
            formatted += f"**핵심 키워드**: {', '.join(insight['keywords'])}\n\n"
            formatted += "---\n\n"

        return formatted


# 전역 인스턴스
investment_rag = InvestmentRAG()


def get_relevant_insights(symbol: str, sector: str = None, top_k: int = 3) -> List[Dict]:
    """종목 관련 인사이트 가져오기"""
    return investment_rag.get_relevant_insights(symbol, sector, top_k)


def format_insights_for_llm(insights: List[Dict]) -> str:
    """LLM 컨텍스트 포맷팅"""
    return investment_rag.format_insights_for_llm(insights)


def test_rag():
    """RAG 시스템 테스트"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 RAG 시스템 테스트")
    logger.info("=" * 80)

    # 테스트 1: 양자컴퓨팅 종목
    logger.info("\n[테스트 1] IONQ 검색")
    insights = get_relevant_insights('IONQ', top_k=2)
    for insight in insights:
        logger.info(f"  - {insight['title']}")

    # 테스트 2: AI 반도체
    logger.info("\n[테스트 2] NVDA 검색")
    insights = get_relevant_insights('NVDA', top_k=2)
    for insight in insights:
        logger.info(f"  - {insight['title']}")

    # 테스트 3: 빅테크
    logger.info("\n[테스트 3] MSFT 검색")
    insights = get_relevant_insights('MSFT', top_k=2)
    formatted = format_insights_for_llm(insights)
    logger.info(f"\n포맷팅된 출력 (처음 200자):\n{formatted[:200]}...")

    logger.info("\n" + "=" * 80)
    logger.info("✅ RAG 시스템 테스트 완료")
    logger.info("=" * 80 + "\n")


if __name__ == '__main__':
    test_rag()
