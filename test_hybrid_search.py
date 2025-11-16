"""하이브리드 검색 테스트"""
import sys
sys.path.append('/home/harvis/ai-hedge-fund')

from src.tools.supabase_rag import SupabaseRAG

def test_hybrid_search():
    """하이브리드 검색 테스트"""
    rag = SupabaseRAG()

    print("=" * 80)
    print("하이브리드 검색 시스템 테스트")
    print("=" * 80)

    # 1. ID 2122, 2123, 2124의 제목 임베딩 생성
    print("\n1단계: 제목 임베딩 생성 (ID 2122, 2123, 2124)")
    print("-" * 80)

    target_ids = [2122, 2123, 2124]

    for post_id in target_ids:
        # 글 정보 가져오기
        response = rag.client.table('investment_insights') \
            .select('id, title, title_embedding') \
            .eq('id', post_id) \
            .execute()

        if not response.data:
            print(f"ID {post_id}: ❌ 없음")
            continue

        post = response.data[0]

        # title_embedding이 없으면 생성
        if post.get('title_embedding') is None:
            print(f"ID {post_id}: 제목 임베딩 생성 중...")
            title_embedding = rag.generate_embedding(post['title'])

            # 업데이트
            rag.client.table('investment_insights') \
                .update({'title_embedding': title_embedding}) \
                .eq('id', post_id) \
                .execute()

            print(f"  ✅ 생성 완료: {post['title'][:50]}...")
        else:
            print(f"ID {post_id}: ✅ 제목 임베딩 이미 있음")

    # 2. 하이브리드 검색 테스트
    print("\n2단계: 하이브리드 검색 테스트")
    print("=" * 80)

    test_cases = [
        ("토요일 새벽", 2122, "토요일 새벽, 암호화폐시장에 역대1위 청산이 터진 비밀"),
        ("암호화폐", 2122, "토요일 새벽, 암호화폐시장에 역대1위 청산이 터진 비밀"),
        ("캄보디아 범죄", 2123, "캄보디아 범죄단지가 왜 생겼고, 어떤 일이 일어나고 있을까?"),
        ("일본 총리", 2124, "일본 총리선거는 어떻게 흘러갈까? (feat, 국민민주당 다마키, 엔화)")
    ]

    for query, expected_id, expected_title in test_cases:
        print(f"\n검색어: \"{query}\"")
        print(f"기대: ID {expected_id} - {expected_title[:40]}...")
        print("-" * 80)

        # 하이브리드 검색
        print("[하이브리드 검색] (제목 가중치: 30%)")
        results = rag.search_similar(query, top_k=5, use_hybrid=True, title_weight=0.3)

        found = False
        for i, r in enumerate(results, 1):
            if r['id'] == expected_id:
                found = True
                print(f"  ✅ 발견! 순위: {i}위, 유사도: {r['similarity']:.6f}")
                break

        if not found:
            print(f"  ❌ 검색 안 됨")
            print(f"  상위 3개:")
            for i, r in enumerate(results[:3], 1):
                print(f"    {i}. [ID: {r['id']}] {r['title'][:50]}... (유사도: {r['similarity']:.6f})")

    # 3. 제목 가중치 비교
    print("\n3단계: 제목 가중치 비교 (query='토요일 새벽')")
    print("=" * 80)

    weights = [0.0, 0.3, 0.5, 0.7, 1.0]

    for weight in weights:
        print(f"\n제목 가중치: {weight:.1f} (제목 {int(weight*100)}%, 내용 {int((1-weight)*100)}%)")
        print("-" * 40)

        results = rag.search_similar("토요일 새벽", top_k=3, use_hybrid=True, title_weight=weight)

        for i, r in enumerate(results, 1):
            marker = "⭐" if r['id'] == 2122 else "  "
            print(f"{marker}{i}. [ID: {r['id']}] {r['title'][:50]}... ({r['similarity']:.4f})")

    # 4. 결론
    print("\n" + "=" * 80)
    print("테스트 완료")
    print("=" * 80)

if __name__ == '__main__':
    test_hybrid_search()
