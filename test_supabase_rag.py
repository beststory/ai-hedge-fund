"""Supabase RAG 데이터 확인 및 검증"""
import sys
from src.tools.supabase_rag import SupabaseRAG

def test_supabase_data():
    """Supabase에 저장된 데이터 개수 및 검색 테스트"""
    print("=" * 80)
    print("Supabase RAG 데이터 검증")
    print("=" * 80)

    rag = SupabaseRAG()
    table_name = "investment_insights"

    # 1. 데이터 개수 확인
    try:
        result = rag.client.table(table_name).select("id", count="exact").execute()
        count = result.count if hasattr(result, 'count') else len(result.data)
        print(f"\n✅ 총 {count}개의 인사이트가 저장되어 있습니다.")
    except Exception as e:
        print(f"\n❌ 데이터 개수 확인 실패: {e}")
        return

    # 2. 샘플 데이터 조회
    try:
        sample = rag.client.table(table_name).select("*").limit(3).execute()
        if sample.data:
            print(f"\n📊 샘플 데이터 (최근 3개):")
            for i, item in enumerate(sample.data, 1):
                print(f"\n  {i}. 제목: {item['title'][:50]}...")
                print(f"     섹터: {item['sector']}")
                print(f"     감성: {item['sentiment']}")
                print(f"     키워드: {', '.join(item['keywords'][:5])}")
    except Exception as e:
        print(f"\n❌ 샘플 데이터 조회 실패: {e}")

    # 3. 검색 테스트
    test_queries = ["삼성전자", "HBM", "AI", "반도체"]
    print(f"\n🔍 검색 테스트:")

    for query in test_queries:
        try:
            results = rag.search_similar(query, top_k=3)
            print(f"\n  '{query}' 검색 결과: {len(results)}개")
            if results:
                for j, result in enumerate(results[:2], 1):
                    similarity = result.get('similarity', 0)
                    print(f"    {j}. {result['title'][:40]}... (유사도: {similarity:.0%})")
        except Exception as e:
            print(f"  ❌ '{query}' 검색 실패: {e}")

    print("\n" + "=" * 80)
    print("검증 완료!")
    print("=" * 80)

if __name__ == '__main__':
    test_supabase_data()
