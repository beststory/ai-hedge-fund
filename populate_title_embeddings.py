"""모든 글의 제목 임베딩 생성 및 저장"""
import sys
sys.path.append('/home/harvis/ai-hedge-fund')

from src.tools.supabase_rag import SupabaseRAG
import time

def populate_title_embeddings(batch_size=50):
    """모든 글의 제목 임베딩을 생성하여 title_embedding 컬럼에 저장"""
    rag = SupabaseRAG()

    print("=" * 80)
    print("제목 임베딩 생성 작업")
    print("=" * 80)

    # 1. 전체 글 수 확인
    response = rag.client.table('investment_insights') \
        .select('id', count='exact') \
        .execute()

    total_count = response.count
    print(f"\n전체 글 수: {total_count}개")

    # 2. title_embedding이 없는 글만 선택
    response = rag.client.table('investment_insights') \
        .select('id, title') \
        .is_('title_embedding', 'null') \
        .order('id') \
        .execute()

    posts_to_update = response.data
    update_count = len(posts_to_update)

    print(f"업데이트 필요: {update_count}개")

    if update_count == 0:
        print("\n✅ 모든 글에 제목 임베딩이 이미 있습니다!")
        return

    print(f"\n배치 크기: {batch_size}개씩 처리")
    print("=" * 80)

    # 3. 배치 처리
    success_count = 0
    error_count = 0

    for i in range(0, update_count, batch_size):
        batch = posts_to_update[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (update_count + batch_size - 1) // batch_size

        print(f"\n배치 {batch_num}/{total_batches} ({len(batch)}개 글)")
        print("-" * 80)

        for j, post in enumerate(batch, 1):
            try:
                # 제목 임베딩 생성
                title_embedding = rag.generate_embedding(post['title'])

                # 업데이트
                rag.client.table('investment_insights') \
                    .update({'title_embedding': title_embedding}) \
                    .eq('id', post['id']) \
                    .execute()

                success_count += 1

                if j % 10 == 0:
                    print(f"  진행: {j}/{len(batch)} (ID {post['id']})")

            except Exception as e:
                error_count += 1
                print(f"  ❌ ID {post['id']} 실패: {e}")

        # 배치 간 짧은 대기 (API rate limit 방지)
        if i + batch_size < update_count:
            print(f"  대기 중... (1초)")
            time.sleep(1)

    # 4. 결과 요약
    print("\n" + "=" * 80)
    print("작업 완료")
    print("=" * 80)
    print(f"성공: {success_count}개")
    print(f"실패: {error_count}개")
    print(f"전체: {success_count + error_count}개")

    # 5. 인덱스 재구축 (성능 향상)
    if success_count > 0:
        print("\n인덱스 재구축 중...")
        import subprocess
        sql = "REINDEX INDEX investment_insights_title_embedding_idx;"
        cmd = ["docker", "exec", "supabase-db", "psql", "-U", "postgres", "-c", sql]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if "REINDEX" in result.stdout:
            print("✅ 인덱스 재구축 완료")
        else:
            print("⚠️ 인덱스 재구축 실패 (검색에는 영향 없음)")

    print("=" * 80)

if __name__ == '__main__':
    populate_title_embeddings()
