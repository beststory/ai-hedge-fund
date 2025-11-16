"""검색이 되는 마지막 ID 찾기"""
import sys
sys.path.append('/home/harvis/ai-hedge-fund')

from src.tools.supabase_rag import SupabaseRAG

def test_id_searchable(rag, test_id):
    """특정 ID가 검색되는지 테스트"""
    # ID 존재 확인
    post = rag.client.table('investment_insights') \
        .select('id, title, embedding') \
        .eq('id', test_id) \
        .execute()

    if not post.data:
        return None, "ID 없음"

    post_data = post_data[0]

    # 임베딩 확인
    if not post_data.get('embedding'):
        return None, "임베딩 없음"

    # 제목으로 검색
    results = rag.search_similar(post_data['title'], top_k=20)
    found = any(r['id'] == test_id for r in results)

    return found, post_data['title']

def find_boundary():
    """검색이 되는 마지막 ID 찾기 (이진 탐색)"""
    rag = SupabaseRAG()

    # 전체 ID 범위 확인
    max_response = rag.client.table('investment_insights') \
        .select('id') \
        .order('id', desc=True) \
        .limit(1) \
        .execute()

    if not max_response.data:
        print("❌ 데이터 없음")
        return

    max_id = max_response.data[0]['id']
    print(f"최대 ID: {max_id}")

    # 이진 탐색
    left = 1
    right = max_id
    last_searchable = None

    print("\n이진 탐색 시작...")
    print("=" * 80)

    while left <= right:
        mid = (left + right) // 2

        # mid ID 확인
        post = rag.client.table('investment_insights') \
            .select('id, title, embedding') \
            .eq('id', mid) \
            .execute()

        if not post.data:
            # ID 없음 - 더 큰 ID 탐색
            print(f"ID {mid}: 없음 → 더 큰 ID 탐색")
            left = mid + 1
            continue

        post_data = post.data[0]

        # 임베딩 확인
        if not post_data.get('embedding'):
            print(f"ID {mid}: 임베딩 없음 → 더 작은 ID 탐색")
            right = mid - 1
            continue

        # 검색 테스트
        results = rag.search_similar(post_data['title'], top_k=20)
        found = any(r['id'] == mid for r in results)

        if found:
            print(f"ID {mid}: ✅ 검색됨 - '{post_data['title'][:40]}...'")
            last_searchable = mid
            # 더 큰 ID 탐색
            left = mid + 1
        else:
            print(f"ID {mid}: ❌ 검색 안 됨 - '{post_data['title'][:40]}...'")
            # 더 작은 ID 탐색
            right = mid - 1

    print("\n" + "=" * 80)
    print("이진 탐색 완료!")
    print("=" * 80)

    if last_searchable:
        print(f"\n✅ 검색이 되는 마지막 ID: {last_searchable}")

        # 경계 확인
        print(f"\n경계 확인:")
        for test_id in [last_searchable - 1, last_searchable, last_searchable + 1, last_searchable + 2]:
            post = rag.client.table('investment_insights') \
                .select('id, title, embedding') \
                .eq('id', test_id) \
                .execute()

            if not post.data:
                print(f"  ID {test_id}: 없음")
                continue

            post_data = post.data[0]

            if not post_data.get('embedding'):
                print(f"  ID {test_id}: 임베딩 없음")
                continue

            results = rag.search_similar(post_data['title'], top_k=20)
            found = any(r['id'] == test_id for r in results)

            status = "✅ 검색됨" if found else "❌ 검색 안 됨"
            print(f"  ID {test_id}: {status} - '{post_data['title'][:40]}...'")

        print(f"\n🔍 결론: ID {last_searchable + 1} 이상의 글이 벡터 인덱스에 포함되지 않음")
    else:
        print("\n❌ 검색되는 ID를 찾을 수 없습니다")

if __name__ == '__main__':
    find_boundary()
