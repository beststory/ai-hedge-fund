"""올바른 ID로 검색 테스트"""
import sys
sys.path.append('/home/harvis/ai-hedge-fund')

from src.tools.supabase_rag import SupabaseRAG

def test_correct_ids():
    """ID 2122, 2123, 2124 검색 테스트"""
    rag = SupabaseRAG()

    print("=" * 80)
    print("ID 2122, 2123, 2124 검색 테스트 (벡터 인덱스 없음)")
    print("=" * 80)

    # 글 정보 확인
    print("\n1. 글 정보 확인")
    print("-" * 80)

    target_ids = [2122, 2123, 2124]
    posts_info = {}

    for post_id in target_ids:
        response = rag.client.table('investment_insights') \
            .select('id, title, embedding, created_at') \
            .eq('id', post_id) \
            .execute()

        if response.data:
            post = response.data[0]
            posts_info[post_id] = post
            has_embedding = post.get('embedding') is not None
            print(f"\nID {post_id}:")
            print(f"  제목: {post['title']}")
            print(f"  생성: {post['created_at']}")
            print(f"  임베딩: {'✅ 있음' if has_embedding else '❌ 없음'}")

    # 검색 테스트
    print("\n2. 검색 테스트")
    print("=" * 80)

    test_cases = [
        ("토요일 새벽", 2122, "토요일 새벽, 암호화폐시장에 역대1위 청산이 터진 비밀"),
        ("암호화폐 청산", 2122, "토요일 새벽, 암호화폐시장에 역대1위 청산이 터진 비밀"),
        ("캄보디아 범죄", 2123, "캄보디아 범죄단지가 왜 생겼고, 어떤 일이 일어나고 있을까?"),
        ("일본 총리", 2124, "일본 총리선거는 어떻게 흘러갈까? (feat, 국민민주당 다마키, 엔화)")
    ]

    all_found = True

    for query, expected_id, expected_title in test_cases:
        print(f"\n검색어: \"{query}\"")
        print(f"기대: ID {expected_id} - {expected_title[:40]}...")
        print("-" * 80)

        try:
            results = rag.search_similar(query, top_k=20)

            found = False
            for i, result in enumerate(results, 1):
                if result['id'] == expected_id:
                    found = True
                    print(f"  ✅ 발견! 순위: {i}위")
                    print(f"     유사도: {result['similarity']:.4f}")
                    break

            if not found:
                all_found = False
                print(f"  ❌ ID {expected_id} 검색 안 됨")
                print(f"  상위 5개 결과:")
                for i, result in enumerate(results[:5], 1):
                    print(f"    {i}. [ID: {result['id']}] {result['title'][:50]}... (유사도: {result['similarity']:.4f})")

        except Exception as e:
            all_found = False
            print(f"  ❌ 검색 오류: {e}")

    # 결론
    print("\n" + "=" * 80)
    if all_found:
        print("✅ 모든 글 검색 성공!")
        print("   → 벡터 인덱스 없이도 검색 가능")
        print("   → 문제는 벡터 인덱스 때문이었음")
    else:
        print("❌ 일부 글 검색 실패")
        print("   → 벡터 인덱스가 아닌 다른 문제")
    print("=" * 80)

if __name__ == '__main__':
    test_correct_ids()
