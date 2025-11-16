"""ID 2119와 쿼리 간 직접 유사도 계산"""
import sys
sys.path.append('/home/harvis/ai-hedge-fund')

from src.tools.supabase_rag import SupabaseRAG
import numpy as np

def test_direct_similarity():
    """PostgreSQL을 거치지 않고 직접 유사도 계산"""
    rag = SupabaseRAG()

    print("=" * 80)
    print("직접 유사도 계산 테스트")
    print("=" * 80)

    # ID 2119 글 가져오기
    post = rag.client.table('investment_insights') \
        .select('id, title, content, embedding') \
        .eq('id', 2119) \
        .execute()

    if not post.data:
        print("❌ ID 2119 글을 찾을 수 없습니다")
        return

    post_data = post.data[0]
    print(f"\n대상 글 [ID: 2119]:")
    print(f"제목: {post_data['title']}")
    print(f"내용 (앞부분): {post_data['content'][:200]}...")

    # 임베딩 파싱 (string을 list로)
    import json
    post_embedding = json.loads(post_data['embedding'])
    post_embedding_np = np.array(post_embedding)

    print(f"\n임베딩 정보:")
    print(f"  - 타입: {type(post_embedding)}")
    print(f"  - 차원: {len(post_embedding)}")
    print(f"  - 첫 5개 값: {post_embedding[:5]}")

    # 테스트 쿼리들
    queries = [
        "토요일 새벽",
        "암호화폐 청산",
        "역대1위 청산",
        "암호화폐시장 청산 레버리지"
    ]

    print("\n" + "=" * 80)
    print("각 쿼리와의 코사인 유사도 직접 계산")
    print("=" * 80)

    for query in queries:
        print(f"\n쿼리: \"{query}\"")

        # 쿼리 임베딩 생성
        query_embedding = rag.generate_embedding(query)
        query_embedding_np = np.array(query_embedding)

        # 코사인 유사도 계산
        # cosine_similarity = 1 - cosine_distance
        dot_product = np.dot(post_embedding_np, query_embedding_np)
        norm_post = np.linalg.norm(post_embedding_np)
        norm_query = np.linalg.norm(query_embedding_np)
        cosine_similarity = dot_product / (norm_post * norm_query)

        # PostgreSQL 방식: 1 - cosine_distance
        # cosine_distance = 1 - cosine_similarity (보통)
        # 하지만 pgvector의 <=> 연산자는 다르게 계산할 수 있음

        print(f"  코사인 유사도: {cosine_similarity:.4f}")
        print(f"  정규화된 유사도 (1-dist): {1 - (1 - cosine_similarity):.4f}")

        # PostgreSQL에서 실제로 어떻게 계산되는지 확인
        result = rag.search_similar(query, top_k=20)

        # ID 2119가 결과에 있는지 확인
        found = any(r['id'] == 2119 for r in result)
        if found:
            for r in result:
                if r['id'] == 2119:
                    print(f"  PostgreSQL 유사도: {r['similarity']:.4f} ✅ 검색됨!")
                    print(f"  순위: {result.index(r) + 1}위")
        else:
            print(f"  PostgreSQL 검색 결과: ❌ 없음 (상위 20개 중)")

            # 상위 3개 보여주기
            print(f"\n  상위 3개:")
            for i, r in enumerate(result[:3], 1):
                print(f"    {i}. [ID: {r['id']}] {r['title'][:40]}... (유사도: {r['similarity']:.4f})")

    print("\n" + "=" * 80)
    print("결론")
    print("=" * 80)

    # ID 2119의 제목으로 검색 (100% 매치 기대)
    print(f"\n특별 테스트: 제목 자체로 검색")
    title_query = post_data['title']
    print(f"쿼리: \"{title_query[:50]}...\"")

    title_embedding = rag.generate_embedding(title_query)
    title_embedding_np = np.array(title_embedding)

    # 자기 자신과의 유사도
    dot_product = np.dot(post_embedding_np, title_embedding_np)
    norm_post = np.linalg.norm(post_embedding_np)
    norm_title = np.linalg.norm(title_embedding_np)
    self_similarity = dot_product / (norm_post * norm_title)

    print(f"자기 자신과의 유사도: {self_similarity:.4f}")

    result = rag.search_similar(title_query, top_k=10)
    found = any(r['id'] == 2119 for r in result)
    status = "✅ 발견" if found else "❌ 없음"
    print(f"PostgreSQL 검색 결과: {status}")

    if found:
        for r in result:
            if r['id'] == 2119:
                print(f"  순위: {result.index(r) + 1}위")
                print(f"  유사도: {r['similarity']:.4f}")
    else:
        print("\n이것은 매우 심각한 문제입니다!")
        print("자기 자신의 제목으로 검색해도 나오지 않는다는 것은")
        print("ID 2119가 벡터 인덱스에서 완전히 제외되어 있다는 의미입니다.")

if __name__ == '__main__':
    test_direct_similarity()
