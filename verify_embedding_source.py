"""임베딩이 제목+내용으로 생성되었는지 확인"""
import sys
sys.path.append('/home/harvis/ai-hedge-fund')

from src.tools.supabase_rag import SupabaseRAG
import json

def verify_embedding_source():
    """임베딩 생성 소스 확인"""
    rag = SupabaseRAG()

    print("=" * 80)
    print("임베딩 생성 소스 검증")
    print("=" * 80)

    # ID 2122 데이터 가져오기
    response = rag.client.table('investment_insights') \
        .select('*') \
        .eq('id', 2122) \
        .execute()

    post = response.data[0]
    stored_emb_str = post['embedding']
    stored_emb = json.loads(stored_emb_str) if isinstance(stored_emb_str, str) else stored_emb_str

    print(f"\nID 2122:")
    print(f"  제목: {post['title']}")
    print(f"  콘텐츠 길이: {len(post['content'])} 자")
    print(f"  콘텐츠 시작: {post['content'][:100]}")

    # 1. 제목+내용으로 임베딩 생성 (정상 방식)
    print("\n1. 제목 + 내용으로 임베딩 생성 (정상)")
    print("-" * 80)
    text_full = f"{post['title']} {post['content']}"
    emb_full = rag.generate_embedding(text_full)
    print(f"  텍스트 길이: {len(text_full)} 자")
    print(f"  임베딩: {emb_full[:5]}")

    # 2. 제목만으로 임베딩 생성
    print("\n2. 제목만으로 임베딩 생성")
    print("-" * 80)
    emb_title = rag.generate_embedding(post['title'])
    print(f"  텍스트: {post['title']}")
    print(f"  임베딩: {emb_title[:5]}")

    # 3. 내용만으로 임베딩 생성
    print("\n3. 내용만으로 임베딩 생성")
    print("-" * 80)
    emb_content = rag.generate_embedding(post['content'])
    print(f"  텍스트 길이: {len(post['content'])} 자")
    print(f"  임베딩: {emb_content[:5]}")

    # 4. 저장된 임베딩 확인
    print("\n4. 저장된 임베딩")
    print("-" * 80)
    print(f"  임베딩: {stored_emb[:5]}")

    # 5. 코사인 유사도 비교
    print("\n5. 코사인 유사도 비교")
    print("=" * 80)

    import numpy as np

    def cosine_similarity(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    stored_arr = np.array(stored_emb, dtype=float)
    emb_full_arr = np.array(emb_full, dtype=float)
    emb_title_arr = np.array(emb_title, dtype=float)
    emb_content_arr = np.array(emb_content, dtype=float)

    sim_full = cosine_similarity(stored_arr, emb_full_arr)
    sim_title = cosine_similarity(stored_arr, emb_title_arr)
    sim_content = cosine_similarity(stored_arr, emb_content_arr)

    print(f"\n저장된 임베딩 vs 제목+내용 임베딩: {sim_full:.6f}")
    print(f"저장된 임베딩 vs 제목 임베딩:       {sim_title:.6f}")
    print(f"저장된 임베딩 vs 내용 임베딩:       {sim_content:.6f}")

    # 6. 가장 유사한 것 판단
    print("\n6. 판단")
    print("=" * 80)

    max_sim = max(sim_full, sim_title, sim_content)

    if abs(sim_full - max_sim) < 0.01:
        print("✅ 저장된 임베딩은 '제목 + 내용'으로 생성됨 (정상)")
    elif abs(sim_title - max_sim) < 0.01:
        print("❌ 저장된 임베딩은 '제목만'으로 생성됨 (비정상!)")
    elif abs(sim_content - max_sim) < 0.01:
        print("❌ 저장된 임베딩은 '내용만'으로 생성됨 (비정상!)")
    else:
        print("⚠️ 저장된 임베딩의 생성 소스를 알 수 없음")

    # 7. 각각으로 검색해보기
    print("\n7. 각 임베딩으로 검색 테스트")
    print("=" * 80)

    # 제목+내용 임베딩으로 검색
    print("\n[제목+내용 임베딩]")
    result = rag.client.rpc('match_insights', {
        'query_embedding': emb_full,
        'match_count': 5
    }).execute()

    found = False
    for i, r in enumerate(result.data, 1):
        if r['id'] == 2122:
            found = True
            print(f"  ✅ ID 2122 발견! 순위: {i}위, 유사도: {r['similarity']:.6f}")
            break
    if not found:
        print(f"  ❌ ID 2122 검색 안 됨")
        print(f"  상위 1위: [ID: {result.data[0]['id']}] {result.data[0]['title'][:50]}...")

    # 제목 임베딩으로 검색
    print("\n[제목 임베딩]")
    result = rag.client.rpc('match_insights', {
        'query_embedding': emb_title,
        'match_count': 5
    }).execute()

    found = False
    for i, r in enumerate(result.data, 1):
        if r['id'] == 2122:
            found = True
            print(f"  ✅ ID 2122 발견! 순위: {i}위, 유사도: {r['similarity']:.6f}")
            break
    if not found:
        print(f"  ❌ ID 2122 검색 안 됨")
        print(f"  상위 1위: [ID: {result.data[0]['id']}] {result.data[0]['title'][:50]}...")

    # 내용 임베딩으로 검색
    print("\n[내용 임베딩]")
    result = rag.client.rpc('match_insights', {
        'query_embedding': emb_content,
        'match_count': 5
    }).execute()

    found = False
    for i, r in enumerate(result.data, 1):
        if r['id'] == 2122:
            found = True
            print(f"  ✅ ID 2122 발견! 순위: {i}위, 유사도: {r['similarity']:.6f}")
            break
    if not found:
        print(f"  ❌ ID 2122 검색 안 됨")
        print(f"  상위 1위: [ID: {result.data[0]['id']}] {result.data[0]['title'][:50]}...")

    print("\n" + "=" * 80)
    print("검증 완료")
    print("=" * 80)

if __name__ == '__main__':
    verify_embedding_source()
