"""뉴스 통합 및 분석 모듈"""
import os
import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class NewsArticle(BaseModel):
    """뉴스 기사 모델"""
    title: str
    description: str
    url: str
    source: str
    published_at: str
    category: str  # economy, market, tech, global
    sentiment: Optional[str] = None  # positive, negative, neutral
    relevance_score: Optional[float] = None


class NewsAggregator:
    """뉴스 수집 및 통합 클래스"""
    
    def __init__(self):
        self.news_api_key = os.getenv("NEWS_API_KEY", "")
        
        # RSS 피드 소스
        self.rss_feeds = {
            "미국경제": [
                "https://www.federalreserve.gov/feeds/press_all.xml",
                "https://www.wsj.com/xml/rss/3_7085.xml",
                "https://www.cnbc.com/id/100003114/device/rss/rss.html",
                "https://www.bloomberg.com/feed/podcast/etf-report.xml"
            ],
            "한국경제": [
                "https://www.bok.or.kr/portal/bbs/B0000216/rss.do",
                "https://www.hankyung.com/feed/economy",
                "https://www.mk.co.kr/rss/30100041/",
                "https://www.edaily.co.kr/rss/rss_economy.xml"
            ],
            "글로벌시장": [
                "https://www.reuters.com/rssFeed/businessNews",
                "https://www.ft.com/?format=rss",
            ],
            "지정학": [
                "https://www.reuters.com/rssFeed/worldNews",
                "https://feeds.bbci.co.uk/news/world/rss.xml",
                "https://www.cnbc.com/id/100727362/device/rss/rss.html",  # CNBC Politics
            ],
            "국방/안보": [
                "https://www.defensenews.com/arc/outboundfeeds/rss/",
                "https://www.janes.com/feeds/news",
            ]
        }

        # 지정학적 리스크 키워드
        self.geopolitical_keywords = {
            "전쟁/분쟁": ["war", "conflict", "military", "attack", "invasion", "전쟁", "분쟁", "군사", "공격"],
            "제재": ["sanction", "embargo", "ban", "restriction", "제재", "금수"],
            "무역갈등": ["trade war", "tariff", "import ban", "export control", "무역전쟁", "관세", "수출통제"],
            "정치위기": ["coup", "revolution", "protest", "political crisis", "쿠데타", "혁명", "시위", "정치위기"],
            "테러": ["terrorism", "terrorist", "attack", "bombing", "테러", "폭탄"],
            "지역긴장": ["tension", "dispute", "standoff", "긴장", "대립", "교착"]
        }

        # 지역별 리스크 키워드
        self.regional_risks = {
            "중동": ["Middle East", "Iran", "Israel", "Gaza", "Syria", "이란", "이스라엘", "시리아"],
            "동아시아": ["Taiwan", "North Korea", "South China Sea", "대만", "북한", "남중국해"],
            "유럽": ["Ukraine", "Russia", "NATO", "우크라이나", "러시아"],
            "아프리카": ["Sudan", "Ethiopia", "Congo", "수단", "에티오피아"],
            "남미": ["Venezuela", "Colombia", "베네수엘라", "콜롬비아"]
        }
    
    def get_recent_news(
        self,
        categories: Optional[List[str]] = None,
        days: int = 7,
        limit: int = 50
    ) -> List[NewsArticle]:
        """최근 뉴스 수집"""
        all_news = []
        
        if categories is None:
            categories = ["미국경제", "한국경제", "글로벌시장"]
        
        # News API 사용
        if self.news_api_key:
            try:
                api_news = self._fetch_from_news_api(days, limit // 2)
                all_news.extend(api_news)
            except Exception as e:
                logger.error(f"News API 호출 실패: {e}")
        
        # RSS 피드 사용
        for category in categories:
            if category in self.rss_feeds:
                try:
                    rss_news = self._fetch_from_rss(category, days)
                    all_news.extend(rss_news)
                except Exception as e:
                    logger.error(f"RSS 피드 수집 실패 ({category}): {e}")
        
        # 샘플 데이터 (실제 데이터 없을 때)
        if not all_news:
            all_news = self._get_sample_news()
        
        # 날짜순 정렬 및 제한
        all_news.sort(key=lambda x: x.published_at, reverse=True)
        return all_news[:limit]
    
    def _fetch_from_news_api(self, days: int, limit: int) -> List[NewsArticle]:
        """News API에서 뉴스 가져오기"""
        articles = []
        
        try:
            from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            # 경제 및 금융 관련 키워드
            keywords = "economy OR market OR stock OR Fed OR inflation OR GDP"
            
            url = "https://newsapi.org/v2/everything"
            params = {
                "apiKey": self.news_api_key,
                "q": keywords,
                "language": "en",
                "from": from_date,
                "sortBy": "publishedAt",
                "pageSize": limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("status") == "ok" and "articles" in data:
                for article in data["articles"]:
                    articles.append(NewsArticle(
                        title=article.get("title", ""),
                        description=article.get("description", ""),
                        url=article.get("url", ""),
                        source=article.get("source", {}).get("name", "Unknown"),
                        published_at=article.get("publishedAt", ""),
                        category="economy"
                    ))
        except Exception as e:
            logger.error(f"News API 오류: {e}")
        
        return articles
    
    def _fetch_from_rss(self, category: str, days: int) -> List[NewsArticle]:
        """RSS 피드에서 뉴스 가져오기"""
        articles = []
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for feed_url in self.rss_feeds.get(category, []):
            try:
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:10]:  # 각 피드에서 최대 10개
                    # 날짜 파싱
                    published = entry.get("published_parsed") or entry.get("updated_parsed")
                    if published:
                        pub_date = datetime(*published[:6])
                        if pub_date < cutoff_date:
                            continue
                        pub_date_str = pub_date.isoformat()
                    else:
                        pub_date_str = datetime.now().isoformat()
                    
                    articles.append(NewsArticle(
                        title=entry.get("title", ""),
                        description=entry.get("summary", ""),
                        url=entry.get("link", ""),
                        source=feed.feed.get("title", "RSS Feed"),
                        published_at=pub_date_str,
                        category=category
                    ))
            except Exception as e:
                logger.error(f"RSS 피드 파싱 실패 ({feed_url}): {e}")
        
        return articles
    
    def _get_sample_news(self) -> List[NewsArticle]:
        """샘플 뉴스 데이터"""
        today = datetime.now().isoformat()
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        
        return [
            NewsArticle(
                title="Fed Holds Interest Rates Steady, Signals Caution on Inflation",
                description="미 연준이 금리를 동결하며 인플레이션에 대한 신중한 입장을 표명했습니다.",
                url="https://example.com/fed-rates",
                source="Reuters",
                published_at=today,
                category="미국경제",
                sentiment="neutral"
            ),
            NewsArticle(
                title="한국은행, 기준금리 3.50% 유지...경기 회복세 주목",
                description="한국은행이 통화정책방향 회의에서 기준금리를 현행 3.50%로 동결했습니다.",
                url="https://example.com/bok-rate",
                source="연합뉴스",
                published_at=today,
                category="한국경제",
                sentiment="neutral"
            ),
            NewsArticle(
                title="S&P 500 Reaches New All-Time High on Tech Rally",
                description="기술주 랠리에 힘입어 S&P 500 지수가 사상 최고치를 경신했습니다.",
                url="https://example.com/sp500-high",
                source="CNBC",
                published_at=yesterday,
                category="글로벌시장",
                sentiment="positive"
            ),
            NewsArticle(
                title="삼성전자, AI 반도체 수주 확대...실적 개선 기대",
                description="삼성전자가 AI 반도체 시장에서 주요 고객사 확보에 성공하며 실적 개선이 기대됩니다.",
                url="https://example.com/samsung-ai",
                source="매일경제",
                published_at=yesterday,
                category="한국경제",
                sentiment="positive"
            ),
            NewsArticle(
                title="Oil Prices Surge on Middle East Tensions",
                description="중동 지역 긴장 고조로 유가가 급등했습니다.",
                url="https://example.com/oil-surge",
                source="Bloomberg",
                published_at=yesterday,
                category="글로벌시장",
                sentiment="negative"
            ),
            NewsArticle(
                title="코스피, 외국인 순매수에 2600선 회복",
                description="외국인 투자자들의 순매수세가 이어지며 코스피가 2600선을 회복했습니다.",
                url="https://example.com/kospi-2600",
                source="한국경제",
                published_at=yesterday,
                category="한국경제",
                sentiment="positive"
            )
        ]
    
    def analyze_news_sentiment(self, news_list: List[NewsArticle]) -> Dict:
        """뉴스 감성 분석 (간단한 규칙 기반)"""
        positive_keywords = ["rally", "surge", "growth", "gain", "high", "상승", "회복", "개선", "성장"]
        negative_keywords = ["fall", "decline", "loss", "drop", "low", "하락", "둔화", "악화", "감소"]
        
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        
        for article in news_list:
            text = (article.title + " " + article.description).lower()
            
            pos_count = sum(1 for word in positive_keywords if word in text)
            neg_count = sum(1 for word in negative_keywords if word in text)
            
            if pos_count > neg_count:
                article.sentiment = "positive"
                sentiment_counts["positive"] += 1
            elif neg_count > pos_count:
                article.sentiment = "negative"
                sentiment_counts["negative"] += 1
            else:
                article.sentiment = "neutral"
                sentiment_counts["neutral"] += 1
        
        total = len(news_list)
        if total == 0:
            return {"overall": "neutral", "distribution": sentiment_counts}
        
        # 전체 감성 판단
        pos_ratio = sentiment_counts["positive"] / total
        neg_ratio = sentiment_counts["negative"] / total
        
        if pos_ratio > 0.5:
            overall = "positive"
        elif neg_ratio > 0.5:
            overall = "negative"
        else:
            overall = "neutral"
        
        return {
            "overall": overall,
            "distribution": sentiment_counts,
            "positive_ratio": round(pos_ratio * 100, 1),
            "negative_ratio": round(neg_ratio * 100, 1),
            "neutral_ratio": round((1 - pos_ratio - neg_ratio) * 100, 1)
        }


# 전역 인스턴스
news_aggregator = NewsAggregator()


def get_recent_news(categories: Optional[List[str]] = None, days: int = 7, limit: int = 50) -> List[NewsArticle]:
    """최근 뉴스 가져오기"""
    return news_aggregator.get_recent_news(categories, days, limit)


def analyze_news_sentiment(news_list: List[NewsArticle]) -> Dict:
    """뉴스 감성 분석"""
    return news_aggregator.analyze_news_sentiment(news_list)


def analyze_geopolitical_risks(days: int = 7) -> Dict:
    """
    지정학적 리스크 분석

    Args:
        days: 분석할 기간 (일)

    Returns:
        지정학적 리스크 분석 결과
    """
    try:
        # 지정학 뉴스 수집
        geopolitical_news = news_aggregator.get_recent_news(
            categories=["지정학", "국방/안보"],
            days=days,
            limit=100
        )

        # 리스크 유형별 분류
        risk_by_type = {risk_type: [] for risk_type in news_aggregator.geopolitical_keywords.keys()}
        risk_by_region = {region: [] for region in news_aggregator.regional_risks.keys()}

        for article in geopolitical_news:
            text = (article.title + " " + article.description).lower()

            # 리스크 유형 분류
            for risk_type, keywords in news_aggregator.geopolitical_keywords.items():
                if any(keyword.lower() in text for keyword in keywords):
                    risk_by_type[risk_type].append(article)

            # 지역별 분류
            for region, keywords in news_aggregator.regional_risks.items():
                if any(keyword.lower() in text for keyword in keywords):
                    risk_by_region[region].append(article)

        # 리스크 점수 계산 (간단한 규칙 기반)
        total_articles = len(geopolitical_news)
        risk_score = 0

        # 전쟁/분쟁 뉴스가 많으면 리스크 높음
        war_count = len(risk_by_type.get("전쟁/분쟁", []))
        sanction_count = len(risk_by_type.get("제재", []))
        trade_war_count = len(risk_by_type.get("무역갈등", []))

        if total_articles > 0:
            risk_score = (
                (war_count / total_articles) * 40 +
                (sanction_count / total_articles) * 30 +
                (trade_war_count / total_articles) * 20 +
                (len([a for articles in risk_by_type.values() for a in articles]) / total_articles) * 10
            )

        # 리스크 레벨 판단
        if risk_score >= 70:
            risk_level = "매우 높음"
            recommendation = "안전자산 비중 확대, 지정학적 리스크 헤지 필수"
        elif risk_score >= 50:
            risk_level = "높음"
            recommendation = "방어적 포지션 강화, 변동성 대비"
        elif risk_score >= 30:
            risk_level = "보통"
            recommendation = "균형적 포트폴리오 유지, 지속 모니터링"
        else:
            risk_level = "낮음"
            recommendation = "정상적 투자 전략 유지"

        # 활발한 리스크 지역 (뉴스가 많은 순)
        active_regions = sorted(
            [(region, len(articles)) for region, articles in risk_by_region.items()],
            key=lambda x: x[1],
            reverse=True
        )[:3]

        return {
            "risk_score": round(risk_score, 1),
            "risk_level": risk_level,
            "recommendation": recommendation,
            "total_articles": total_articles,
            "risk_by_type": {
                risk_type: len(articles)
                for risk_type, articles in risk_by_type.items()
                if len(articles) > 0
            },
            "active_regions": [
                {"region": region, "article_count": count}
                for region, count in active_regions
                if count > 0
            ],
            "top_news": [
                {
                    "title": article.title,
                    "description": article.description[:200] + "...",
                    "source": article.source,
                    "published_at": article.published_at,
                    "url": article.url
                }
                for article in geopolitical_news[:5]
            ]
        }

    except Exception as e:
        logger.error(f"❌ 지정학적 리스크 분석 실패: {e}")
        return {
            "risk_score": 0,
            "risk_level": "알 수 없음",
            "recommendation": "데이터 수집 실패",
            "error": str(e)
        }


