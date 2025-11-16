"""벡터 인덱스 없이 Sequential Scan으로 검색 테스트"""
import sys
sys.path.append('/home/harvis/ai-hedge-fund')

from src.tools.supabase_rag import SupabaseRAG

def test_search_without_index():
    """인덱스 없이 검색 테스트 (Sequential Scan 사용)"""
    rag = SupabaseRAG()

    print("=" * 80)
    print("벡터 인덱스 없이 검색 테스트 (Sequential Scan)")
    print("=" * 80)

    # 최근 추가된 글들 확인
    print("\n1. 최근 추가된 글 확인 (ID 2116~2118)")
    print("-" * 80)

    recent_ids = [2116, 2117, 2118]
    posts_data = {}

    for post_id in recent_ids:
        response = rag.client.table('investment_insights') \
            .select('id, title, embedding') \
            .eq('id', post_id) \
            .execute()

        if response.data:
            post = response.data[0]
            posts_data[post_id] = post
            has_embedding = post.get('embedding') is not None
            print(f"ID {post_id}: ✅ 존재")
            print(f"  제목: {post['title'][:60]}...")
            print(f"  임베딩: {'✅ 있음' if has_embedding else '❌ 없음'}")
        else:
            print(f"ID {post_id}: ❌ 없음")

    # 검색 테스트
    print("\n2. 검색 테스트 (Sequential Scan)")
    print("=" * 80)

    test_queries = [
        ("토요일 새벽", 2116),
        ("암호화폐 청산", 2116),
        ("캄보디아 범죄", 2117),
        ("일본 총리", 2118)
    ]

    for query, expected_id in test_queries:
        print(f"\n검색어: \"{query}\" (기대 ID: {expected_id})")
        print("-" * 80)

        try:
            results = rag.search_similar(query, top_k=10)

            found = False
            for i, result in enumerate(results, 1):
                if result['id'] == expected_id:
                    found = True
                    print(f"  ✅ 발견! 순위: {i}위")
                    print(f"     유사도: {result['similarity']:.4f}")
                    print(f"     제목: {result['title'][:50]}...")
                    break

            if not found:
                print(f"  ❌ ID {expected_id} 검색 안 됨")
                print(f"  상위 3개 결과:")
                for i, result in enumerate(results[:3], 1):
                    print(f"    {i}. [ID: {result['id']}] {result['title'][:40]}... (유사도: {result['similarity']:.4f})")

        except Exception as e:
            print(f"  ❌ 검색 오류: {e}")

    # 쿼리 플랜 확인 (Sequential Scan인지 확인)
    print("\n3. 쿼리 실행 계획 확인")
    print("=" * 80)

    try:
        # 테스트 임베딩 생성
        test_embedding = rag.generate_embedding("테스트")

        # EXPLAIN으로 쿼리 플랜 확인
        result = rag.client.rpc(
            'match_insights',
            {'query_embedding': test_embedding, 'match_count': 5}
        ).execute()

        print("✅ match_insights RPC 함수 실행 성공")
        print(f"   반환된 결과 수: {len(result.data)}")

        # PostgreSQL에서 직접 EXPLAIN 실행
        print("\n   PostgreSQL EXPLAIN 결과:")
        import subprocess
        explain_query = f"""
        EXPLAIN ANALYZE
        SELECT
            id, title, content, sector, sentiment, keywords, url, date,
            1 - (embedding <=> '[{','.join(map(str, test_embedding[:5]))}]'::vector(768)) as similarity
        FROM investment_insights
        ORDER BY embedding <=> '[{','.join(map(str, test_embedding[:5]))}]'::vector(768)
        LIMIT 5;
        """

        cmd = ["docker", "exec", "supabase-db", "psql", "-U", "postgres", "-c", explain_query]
        process = subprocess.run(cmd, capture_output=True, text=True)

        if "Seq Scan" in process.stdout:
            print("   ✅ Sequential Scan 사용 중")
        elif "Index" in process.stdout:
            print("   ⚠️ 여전히 인덱스 사용 중")

        print(process.stdout)

    except Exception as e:
        print(f"❌ 쿼리 플랜 확인 실패: {e}")

    print("\n" + "=" * 80)
    print("테스트 완료")
    print("=" * 80)

if __name__ == '__main__':
    test_search_without_index()
