"""RPC 함수 직접 테스트"""
import sys
sys.path.append('/home/harvis/ai-hedge-fund')

from src.tools.supabase_rag import SupabaseRAG
import subprocess
import json

def test_rpc_direct():
    """match_insights RPC 함수 직접 테스트"""
    rag = SupabaseRAG()

    print("=" * 80)
    print("match_insights RPC 함수 직접 테스트")
    print("=" * 80)

    # 1. ID 2122의 임베딩을 그대로 가져와서 검색
    print("\n1. ID 2122의 임베딩으로 자기 자신 검색")
    print("-" * 80)

    # ID 2122 데이터 가져오기
    response = rag.client.table('investment_insights') \
        .select('id, title, embedding') \
        .eq('id', 2122) \
        .execute()

    if not response.data:
        print("❌ ID 2122 없음")
        return

    post = response.data[0]
    print(f"제목: {post['title']}")

    # Supabase에서 반환된 embedding 확인
    emb = post['embedding']
    print(f"임베딩 타입: {type(emb)}")
    print(f"임베딩 길이: {len(emb) if isinstance(emb, (list, str)) else 'N/A'}")

    # 이 임베딩으로 직접 검색
    try:
        # embedding이 string이면 파싱
        if isinstance(emb, str):
            # '[...]' 형식에서 숫자 추출
            emb_list = json.loads(emb)
            print(f"파싱된 임베딩: list, 길이 {len(emb_list)}")
        else:
            emb_list = emb

        # RPC 함수 호출
        result = rag.client.rpc(
            'match_insights',
            {'query_embedding': emb_list, 'match_count': 30}
        ).execute()

        print(f"\n검색 결과: {len(result.data)}개")

        found = False
        for i, r in enumerate(result.data, 1):
            if r['id'] == 2122:
                found = True
                print(f"  ✅ 자기 자신 발견! 순위: {i}위")
                print(f"     유사도: {r['similarity']:.6f}")
                break

        if not found:
            print(f"  ❌ 자기 자신도 검색 안 됨!")
            print(f"  상위 5개:")
            for i, r in enumerate(result.data[:5], 1):
                print(f"    {i}. [ID: {r['id']}] {r['title'][:50]}... (유사도: {r['similarity']:.6f})")

    except Exception as e:
        print(f"❌ 검색 실패: {e}")

    # 2. PostgreSQL에서 직접 SQL로 검색
    print("\n2. PostgreSQL 직접 SQL 쿼리")
    print("=" * 80)

    sql = f"""
    SELECT
        id, title,
        1 - (embedding <=> (SELECT embedding FROM investment_insights WHERE id = 2122)) as similarity
    FROM investment_insights
    WHERE id IN (2115, 2122, 2123, 2124)
    ORDER BY similarity DESC;
    """

    cmd = ["docker", "exec", "supabase-db", "psql", "-U", "postgres", "-c", sql]
    process = subprocess.run(cmd, capture_output=True, text=True)

    print(process.stdout)

    if "2122" in process.stdout:
        print("✅ PostgreSQL 직접 쿼리에서는 ID 2122가 나옴")
    else:
        print("❌ PostgreSQL 직접 쿼리에서도 ID 2122가 안 나옴")

    # 3. 다른 쿼리로 전체 테이블 검색
    print("\n3. ID 2122 임베딩으로 전체 테이블 검색 (상위 5개)")
    print("-" * 80)

    sql2 = """
    SELECT
        id, title,
        1 - (embedding <=> (SELECT embedding FROM investment_insights WHERE id = 2122)) as similarity
    FROM investment_insights
    ORDER BY similarity DESC
    LIMIT 5;
    """

    cmd2 = ["docker", "exec", "supabase-db", "psql", "-U", "postgres", "-c", sql2]
    process2 = subprocess.run(cmd2, capture_output=True, text=True)

    print(process2.stdout)

    # 4. match_insights 함수 정의 확인
    print("\n4. match_insights 함수 정의 확인")
    print("=" * 80)

    sql3 = """
    SELECT prosrc
    FROM pg_proc
    WHERE proname = 'match_insights';
    """

    cmd3 = ["docker", "exec", "supabase-db", "psql", "-U", "postgres", "-t", "-c", sql3]
    process3 = subprocess.run(cmd3, capture_output=True, text=True)

    print("함수 정의:")
    print(process3.stdout)

    print("\n" + "=" * 80)
    print("테스트 완료")
    print("=" * 80)

if __name__ == '__main__':
    test_rpc_direct()
