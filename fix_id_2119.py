"""ID 2119를 삭제하고 다시 추가"""
import sys
sys.path.append('/home/harvis/ai-hedge-fund')

from src.tools.supabase_rag import SupabaseRAG
import subprocess
import json

def fix_id_2119():
    """ID 2119를 완전히 삭제하고 PostgreSQL로 직접 INSERT"""
    rag = SupabaseRAG()

    print("=" * 80)
    print("ID 2119 수정 작업")
    print("=" * 80)

    # 1. ID 2119 데이터 백업
    print("\n1. ID 2119 데이터 백업...")
    response = rag.client.table('investment_insights') \
        .select('*') \
        .eq('id', 2119) \
        .execute()

    if not response.data:
        print("❌ ID 2119가 존재하지 않습니다")
        return

    data = response.data[0]
    print(f"✅ 백업 완료: {data['title']}")

    # 2. 삭제
    print("\n2. ID 2119 삭제...")
    rag.client.table('investment_insights') \
        .delete() \
        .eq('id', 2119) \
        .execute()
    print("✅ 삭제 완료")

    # 3. 임베딩 준비
    print("\n3. 임베딩 준비...")
    embedding = json.loads(data['embedding'])
    print(f"임베딩 차원: {len(embedding)}")

    # 4. PostgreSQL로 직접 INSERT
    print("\n4. PostgreSQL로 직접 INSERT...")

    # 임베딩을 PostgreSQL array 형식으로 변환
    embedding_str = '[' + ','.join(map(str, embedding)) + ']'

    # SQL 이스케이프
    title = data['title'].replace("'", "''")
    content = data['content'].replace("'", "''")
    sector = data['sector'].replace("'", "''")
    sentiment = data['sentiment'].replace("'", "''")
    url = data['url'].replace("'", "''")
    date = data['date'].replace("'", "''")

    # keywords 배열 처리
    keywords_str = "ARRAY["
    for i, kw in enumerate(data['keywords']):
        if i > 0:
            keywords_str += ","
        escaped_kw = kw.replace('"', '').replace("'", "''")
        keywords_str += f"'{escaped_kw}'"
    keywords_str += "]"

    sql = f"""
    INSERT INTO investment_insights
    (id, title, content, sector, sentiment, keywords, url, date, embedding)
    VALUES
    (
        2119,
        '{title}',
        '{content}',
        '{sector}',
        '{sentiment}',
        {keywords_str},
        '{url}',
        '{date}',
        '{embedding_str}'::vector(768)
    );
    """

    # SQL 파일로 저장
    with open('/tmp/insert_2119.sql', 'w', encoding='utf-8') as f:
        f.write(sql)

    # Docker로 실행
    cmd = "docker exec supabase-db psql -U postgres -f -"
    process = subprocess.Popen(
        cmd.split(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    stdout, stderr = process.communicate(input=sql)

    if process.returncode == 0:
        print("✅ INSERT 성공")
        print(stdout)
    else:
        print("❌ INSERT 실패")
        print(stderr)
        return

    # 5. 검색 테스트
    print("\n5. 검색 테스트...")
    import time
    time.sleep(1)  # 인덱스 업데이트 대기

    # 제목으로 검색
    results = rag.search_similar(data['title'], top_k=10)
    found = any(r['id'] == 2119 for r in results)

    status = "✅ 발견" if found else "❌ 없음"
    print(f"제목으로 검색: {status}")

    if found:
        for r in results:
            if r['id'] == 2119:
                print(f"  순위: {results.index(r) + 1}위")
                print(f"  유사도: {r['similarity']:.4f}")
    else:
        print("  상위 3개:")
        for i, r in enumerate(results[:3], 1):
            print(f"    {i}. [ID: {r['id']}] {r['title'][:40]}... (유사도: {r['similarity']:.4f})")

    # "토요일 새벽"으로 검색
    results2 = rag.search_similar("토요일 새벽", top_k=10)
    found2 = any(r['id'] == 2119 for r in results2)

    status2 = "✅ 발견" if found2 else "❌ 없음"
    print(f"\n\"토요일 새벽\" 검색: {status2}")

    if found2:
        for r in results2:
            if r['id'] == 2119:
                print(f"  순위: {results2.index(r) + 1}위")
                print(f"  유사도: {r['similarity']:.4f}")

    print("\n" + "=" * 80)
    if found or found2:
        print("✅ 문제 해결됨!")
    else:
        print("❌ 여전히 검색 안 됨 - 추가 조치 필요")
    print("=" * 80)

if __name__ == '__main__':
    fix_id_2119()
