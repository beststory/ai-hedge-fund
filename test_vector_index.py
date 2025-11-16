"""벡터 인덱스 상태 진단 스크립트"""
import sys
sys.path.append('/home/harvis/ai-hedge-fund')

from src.tools.supabase_rag import SupabaseRAG
import json

def test_old_vs_new_posts():
    """기존 글 vs 새 글 검색 테스트"""
    rag = SupabaseRAG()

    print("=" * 80)
    print("1. 기존 글 검색 테스트 (ID < 2117)")
    print("=" * 80)

    # 암호화폐 관련 검색 (기존 글이 있을 것으로 예상)
    results = rag.search_similar("암호화폐", top_k=20)
    old_posts = [r for r in results if r['id'] < 2117]
    new_posts = [r for r in results if r['id'] >= 2117]

    print(f"\n검색어: '암호화폐'")
    print(f"총 결과: {len(results)}개")
    print(f"기존 글 (ID < 2117): {len(old_posts)}개")
    print(f"새 글 (ID >= 2117): {len(new_posts)}개")

    if old_posts:
        print("\n✅ 기존 글 상위 5개:")
        for post in old_posts[:5]:
            print(f"  - [ID: {post['id']}] {post['title'][:50]}... (유사도: {post['similarity']:.4f})")
    else:
        print("\n❌ 기존 글도 검색 안 됨!")

    if new_posts:
        print("\n✅ 새 글 발견:")
        for post in new_posts:
            print(f"  - [ID: {post['id']}] {post['title'][:50]}... (유사도: {post['similarity']:.4f})")
    else:
        print("\n❌ 새 글 검색 안 됨")

    print("\n" + "=" * 80)
    print("2. 새로 추가된 글 직접 조회")
    print("=" * 80)

    # 새로 추가된 글 직접 조회
    new_post_ids = [2117, 2118, 2119]
    for post_id in new_post_ids:
        response = rag.client.table('investment_insights') \
            .select('id, title, embedding') \
            .eq('id', post_id) \
            .execute()

        if response.data and len(response.data) > 0:
            post = response.data[0]
            has_embedding = post.get('embedding') is not None
            embedding_type = type(post.get('embedding')).__name__ if has_embedding else 'None'
            embedding_len = len(str(post.get('embedding'))) if has_embedding else 0

            print(f"\n[ID: {post_id}] {post['title'][:60]}...")
            print(f"  임베딩 존재: {'✅ Yes' if has_embedding else '❌ No'}")
            print(f"  임베딩 타입: {embedding_type}")
            print(f"  임베딩 길이: {embedding_len} chars")
        else:
            print(f"\n[ID: {post_id}] ❌ 글이 존재하지 않음")

    print("\n" + "=" * 80)
    print("3. 임베딩 비교 (기존 글 vs 새 글)")
    print("=" * 80)

    # 기존 글 하나 조회
    old_post = rag.client.table('investment_insights') \
        .select('id, title, embedding') \
        .lt('id', 2117) \
        .not_.is_('embedding', 'null') \
        .limit(1) \
        .execute()

    # 새 글 하나 조회
    new_post = rag.client.table('investment_insights') \
        .select('id, title, embedding') \
        .eq('id', 2117) \
        .execute()

    if old_post.data and new_post.data:
        old = old_post.data[0]
        new = new_post.data[0]

        print(f"\n기존 글 [ID: {old['id']}]:")
        print(f"  제목: {old['title'][:60]}...")
        old_embedding = old['embedding']
        print(f"  임베딩 타입: {type(old_embedding).__name__}")
        print(f"  임베딩 길이: {len(str(old_embedding))} chars")
        if isinstance(old_embedding, str):
            print(f"  임베딩 시작: {old_embedding[:100]}...")

        print(f"\n새 글 [ID: {new['id']}]:")
        print(f"  제목: {new['title'][:60]}...")
        new_embedding = new['embedding']
        print(f"  임베딩 타입: {type(new_embedding).__name__}")
        print(f"  임베딩 길이: {len(str(new_embedding))} chars")
        if isinstance(new_embedding, str):
            print(f"  임베딩 시작: {new_embedding[:100]}...")

        # 형식 비교
        print(f"\n임베딩 형식 동일: {'✅ Yes' if type(old_embedding) == type(new_embedding) else '❌ No'}")

    print("\n" + "=" * 80)
    print("4. RPC 함수 직접 호출 테스트")
    print("=" * 80)

    # 새 글 임베딩으로 직접 검색
    if new_post.data:
        new_post_data = new_post.data[0]

        # 임베딩 생성
        query_embedding = rag.generate_embedding(new_post_data['title'])

        print(f"\n쿼리: '{new_post_data['title'][:50]}...'")
        print(f"쿼리 임베딩 차원: {len(query_embedding)}")

        # RPC 직접 호출
        result = rag.client.rpc(
            'match_insights',
            {
                'query_embedding': query_embedding,
                'match_count': 10
            }
        ).execute()

        print(f"검색 결과: {len(result.data)}개")

        # 자기 자신이 나오는지 확인
        self_found = any(r['id'] == new_post_data['id'] for r in result.data)
        print(f"자기 자신 발견: {'✅ Yes' if self_found else '❌ No'}")

        if result.data:
            print("\n상위 5개 결과:")
            for i, r in enumerate(result.data[:5], 1):
                is_self = '(자기자신)' if r['id'] == new_post_data['id'] else ''
                print(f"  {i}. [ID: {r['id']}] {r['title'][:50]}... (유사도: {r['similarity']:.4f}) {is_self}")

if __name__ == '__main__':
    test_old_vs_new_posts()
