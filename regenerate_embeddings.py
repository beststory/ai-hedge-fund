"""ID 2120, 2121 임베딩 재생성"""
import sys
sys.path.append('/home/harvis/ai-hedge-fund')

from src.tools.supabase_rag import SupabaseRAG
import time

def regenerate_embeddings():
    """ID 2120, 2121 임베딩 재생성 및 UPDATE"""
    rag = SupabaseRAG()

    print("=" * 80)
    print("ID 2120, 2121 임베딩 재생성")
    print("=" * 80)

    target_ids = [2120, 2121]

    for target_id in target_ids:
        print(f"\n처리 중: ID {target_id}")

        # 글 데이터 조회
        response = rag.client.table('investment_insights') \
            .select('*') \
            .eq('id', target_id) \
            .execute()

        if not response.data:
            print(f"  ❌ ID {target_id} 없음")
            continue

        post = response.data[0]
        print(f"  제목: {post['title'][:60]}...")

        # 새 임베딩 생성 (제목 + 내용)
        text = f"{post['title']} {post['content']}"
        new_embedding = rag.generate_embedding(text)

        print(f"  새 임베딩 생성: {len(new_embedding)}차원")

        # UPDATE
        update_result = rag.client.table('investment_insights') \
            .update({'embedding': new_embedding}) \
            .eq('id', target_id) \
            .execute()

        print(f"  ✅ 임베딩 업데이트 완료")

    # 잠시 대기
    print("\n인덱스 적용 대기 (2초)...")
    time.sleep(2)

    # 검색 테스트
    print("\n" + "=" * 80)
    print("검색 테스트")
    print("=" * 80)

    for target_id in target_ids:
        response = rag.client.table('investment_insights') \
            .select('id, title') \
            .eq('id', target_id) \
            .execute()

        if not response.data:
            continue

        post = response.data[0]
        print(f"\nID {target_id}: {post['title'][:60]}...")

        # 제목으로 검색
        results = rag.search_similar(post['title'], top_k=10)
        found = any(r['id'] == target_id for r in results)

        print(f"  제목 검색: {'✅ 발견' if found else '❌ 없음'}")

        if found:
            for r in results:
                if r['id'] == target_id:
                    print(f"    순위: {results.index(r) + 1}위")
                    print(f"    유사도: {r['similarity']:.4f}")
        else:
            print("  상위 3개:")
            for i, r in enumerate(results[:3], 1):
                print(f"    {i}. [ID: {r['id']}] {r['title'][:40]}... ({r['similarity']:.4f})")

    # 키워드 검색 테스트
    print("\n" + "=" * 80)
    print("키워드 검색 테스트")
    print("=" * 80)

    # "캄보디아" 검색
    print("\n1. '캄보디아' 검색")
    results = rag.search_similar("캄보디아 범죄", top_k=10)
    found_2120 = any(r['id'] == 2120 for r in results)
    print(f"  ID 2120 발견: {'✅ Yes' if found_2120 else '❌ No'}")

    if found_2120:
        for r in results:
            if r['id'] == 2120:
                print(f"    순위: {results.index(r) + 1}위, 유사도: {r['similarity']:.4f}")

    # "일본" 검색
    print("\n2. '일본 총리' 검색")
    results = rag.search_similar("일본 총리선거", top_k=10)
    found_2121 = any(r['id'] == 2121 for r in results)
    print(f"  ID 2121 발견: {'✅ Yes' if found_2121 else '❌ No'}")

    if found_2121:
        for r in results:
            if r['id'] == 2121:
                print(f"    순위: {results.index(r) + 1}위, 유사도: {r['similarity']:.4f}")

    print("\n" + "=" * 80)
    if found_2120 or found_2121:
        print("✅ 문제 해결!")
    else:
        print("❌ 여전히 검색 안 됨")
    print("=" * 80)

if __name__ == '__main__':
    regenerate_embeddings()
