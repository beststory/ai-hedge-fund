"""기존 글도 제목으로 검색이 안 되는지 확인"""
import sys
sys.path.append('/home/harvis/ai-hedge-fund')

from src.tools.supabase_rag import SupabaseRAG

def test_old_posts():
    """기존 글들도 제목으로 검색 안 되는지 테스트"""
    rag = SupabaseRAG()

    print("=" * 80)
    print("기존 글 제목 검색 테스트")
    print("=" * 80)

    # 작동한다고 확인된 기존 글들
    old_ids = [2115, 2110, 2100, 2090, 2080]

    for old_id in old_ids:
        # 글 정보 가져오기
        response = rag.client.table('investment_insights') \
            .select('id, title, content') \
            .eq('id', old_id) \
            .execute()

        if not response.data:
            print(f"\nID {old_id}: ❌ 없음")
            continue

        post = response.data[0]
        title = post['title']
        content = post['content']

        print(f"\n" + "=" * 80)
        print(f"ID {old_id}")
        print(f"제목: {title}")
        print(f"내용 길이: {len(content)} 자")
        print("-" * 80)

        # 제목으로 검색
        results = rag.search_similar(title, top_k=10)

        found = False
        for i, r in enumerate(results, 1):
            if r['id'] == old_id:
                found = True
                print(f"  ✅ 제목으로 검색 시 발견: {i}위, 유사도: {r['similarity']:.6f}")
                break

        if not found:
            print(f"  ❌ 제목으로 검색 시 발견 안 됨")
            print(f"  상위 3개:")
            for i, r in enumerate(results[:3], 1):
                print(f"    {i}. [ID: {r['id']}] {r['title'][:50]}... (유사도: {r['similarity']:.6f})")

    # 결론
    print("\n" + "=" * 80)
    print("결론")
    print("=" * 80)
    print("모든 글이 제목만으로는 검색되지 않는다면:")
    print("  → 이것은 새 글만의 문제가 아니라 시스템 전체의 구조적 문제")
    print("  → 제목+내용으로 임베딩을 생성하면 제목 검색이 어려움")
    print("\n일부 기존 글이 제목으로 검색된다면:")
    print("  → 새 글과 기존 글의 차이점을 분석해야 함")
    print("=" * 80)

if __name__ == '__main__':
    test_old_posts()
