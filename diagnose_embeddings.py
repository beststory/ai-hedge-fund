"""임베딩 진단: 작동하는 글과 작동하지 않는 글 비교"""
import sys
sys.path.append('/home/harvis/ai-hedge-fund')

from src.tools.supabase_rag import SupabaseRAG
import numpy as np

def diagnose_embeddings():
    """임베딩 비교 진단"""
    rag = SupabaseRAG()

    print("=" * 80)
    print("임베딩 진단: 작동하는 글 vs 작동하지 않는 글")
    print("=" * 80)

    # 1. 작동하는 글 (ID 2115)과 작동하지 않는 글 (ID 2122) 가져오기
    print("\n1. 글 데이터 가져오기")
    print("-" * 80)

    working_id = 2115
    broken_id = 2122

    working_post = rag.client.table('investment_insights') \
        .select('*') \
        .eq('id', working_id) \
        .execute().data[0]

    broken_post = rag.client.table('investment_insights') \
        .select('*') \
        .eq('id', broken_id) \
        .execute().data[0]

    print(f"\n작동하는 글 (ID {working_id}):")
    print(f"  제목: {working_post['title']}")
    print(f"  생성: {working_post['created_at']}")

    print(f"\n작동하지 않는 글 (ID {broken_id}):")
    print(f"  제목: {broken_post['title']}")
    print(f"  생성: {broken_post['created_at']}")

    # 2. 임베딩 형식 비교
    print("\n2. 임베딩 형식 분석")
    print("=" * 80)

    working_emb = working_post['embedding']
    broken_emb = broken_post['embedding']

    print(f"\n작동하는 글 임베딩:")
    print(f"  타입: {type(working_emb)}")
    print(f"  길이: {len(working_emb) if isinstance(working_emb, (list, str)) else 'N/A'}")
    if isinstance(working_emb, list):
        print(f"  첫 5개 값: {working_emb[:5]}")
        print(f"  값 타입: {type(working_emb[0])}")
    elif isinstance(working_emb, str):
        print(f"  첫 100자: {working_emb[:100]}")

    print(f"\n작동하지 않는 글 임베딩:")
    print(f"  타입: {type(broken_emb)}")
    print(f"  길이: {len(broken_emb) if isinstance(broken_emb, (list, str)) else 'N/A'}")
    if isinstance(broken_emb, list):
        print(f"  첫 5개 값: {broken_emb[:5]}")
        print(f"  값 타입: {type(broken_emb[0])}")
    elif isinstance(broken_emb, str):
        print(f"  첫 100자: {broken_emb[:100]}")

    # 3. 임베딩을 numpy 배열로 변환하여 비교
    print("\n3. 임베딩 통계 비교")
    print("-" * 80)

    try:
        working_arr = np.array(working_emb, dtype=float)
        broken_arr = np.array(broken_emb, dtype=float)

        print(f"\n작동하는 글:")
        print(f"  Shape: {working_arr.shape}")
        print(f"  Mean: {working_arr.mean():.6f}")
        print(f"  Std: {working_arr.std():.6f}")
        print(f"  Min: {working_arr.min():.6f}")
        print(f"  Max: {working_arr.max():.6f}")
        print(f"  Norm (L2): {np.linalg.norm(working_arr):.6f}")

        print(f"\n작동하지 않는 글:")
        print(f"  Shape: {broken_arr.shape}")
        print(f"  Mean: {broken_arr.mean():.6f}")
        print(f"  Std: {broken_arr.std():.6f}")
        print(f"  Min: {broken_arr.min():.6f}")
        print(f"  Max: {broken_arr.max():.6f}")
        print(f"  Norm (L2): {np.linalg.norm(broken_arr):.6f}")

    except Exception as e:
        print(f"❌ numpy 변환 실패: {e}")

    # 4. 수동으로 코사인 유사도 계산
    print("\n4. 수동 코사인 유사도 계산")
    print("=" * 80)

    # 테스트 쿼리: "토요일 새벽"
    test_query = "토요일 새벽"
    query_emb = rag.generate_embedding(test_query)

    print(f"\n쿼리: \"{test_query}\"")
    print(f"쿼리 임베딩:")
    print(f"  타입: {type(query_emb)}")
    print(f"  길이: {len(query_emb)}")
    print(f"  첫 5개 값: {query_emb[:5]}")

    try:
        query_arr = np.array(query_emb, dtype=float)
        working_arr = np.array(working_emb, dtype=float)
        broken_arr = np.array(broken_emb, dtype=float)

        # 코사인 유사도 = dot(A,B) / (norm(A) * norm(B))
        # pgvector는 코사인 거리 = 1 - 코사인 유사도를 사용
        def cosine_similarity(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

        working_sim = cosine_similarity(query_arr, working_arr)
        broken_sim = cosine_similarity(query_arr, broken_arr)

        print(f"\n작동하는 글 (ID {working_id})과 쿼리 유사도:")
        print(f"  코사인 유사도: {working_sim:.6f}")
        print(f"  pgvector 거리 (1-similarity): {1-working_sim:.6f}")

        print(f"\n작동하지 않는 글 (ID {broken_id})과 쿼리 유사도:")
        print(f"  코사인 유사도: {broken_sim:.6f}")
        print(f"  pgvector 거리 (1-similarity): {1-broken_sim:.6f}")

        if broken_sim > working_sim:
            print(f"\n✅ 이론적으로 ID {broken_id}가 더 높은 유사도를 가짐")
            print(f"   그런데도 검색에서 안 나옴 → RPC 함수 문제 가능성")
        else:
            print(f"\n⚠️ ID {working_id}가 더 높은 유사도를 가짐")
            print(f"   검색에 안 나오는 것이 정상일 수 있음")

    except Exception as e:
        print(f"❌ 유사도 계산 실패: {e}")

    # 5. PostgreSQL에서 직접 유사도 확인
    print("\n5. PostgreSQL 직접 쿼리")
    print("=" * 80)

    try:
        # 제목으로 임베딩 생성
        title_emb = rag.generate_embedding(broken_post['title'])

        print(f"\n글 제목으로 임베딩 생성:")
        print(f"  제목: {broken_post['title']}")
        print(f"  임베딩 첫 5개: {title_emb[:5]}")

        # match_insights로 검색
        results = rag.search_similar(broken_post['title'], top_k=30)

        found = False
        for i, result in enumerate(results, 1):
            if result['id'] == broken_id:
                found = True
                print(f"\n  ✅ 제목으로 검색 시 발견!")
                print(f"     순위: {i}위")
                print(f"     유사도: {result['similarity']:.6f}")
                break

        if not found:
            print(f"\n  ❌ 제목으로도 검색 안 됨")
            print(f"  상위 5개:")
            for i, result in enumerate(results[:5], 1):
                print(f"    {i}. [ID: {result['id']}] {result['title'][:50]}... (유사도: {result['similarity']:.6f})")

    except Exception as e:
        print(f"❌ PostgreSQL 쿼리 실패: {e}")

    print("\n" + "=" * 80)
    print("진단 완료")
    print("=" * 80)

if __name__ == '__main__':
    diagnose_embeddings()
