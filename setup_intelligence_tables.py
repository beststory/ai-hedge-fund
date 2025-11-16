"""Intelligence 시스템 테이블 생성 스크립트

Supabase에 AI 투자 지능 시스템 테이블을 생성합니다.
"""
import os
from dotenv import load_dotenv
from src.tools.supabase_rag import SupabaseRAG

load_dotenv()

# SQL 파일 읽기
with open("supabase_intelligence_system.sql", "r", encoding="utf-8") as f:
    sql_content = f.read()

print("=" * 80)
print("🔧 Intelligence 시스템 테이블 생성")
print("=" * 80)

# SQL을 개별 명령어로 분할
sql_commands = []
current_command = []

for line in sql_content.split("\n"):
    # 주석 제거
    if line.strip().startswith("--"):
        continue

    current_command.append(line)

    # 세미콜론으로 명령어 종료
    if line.strip().endswith(";"):
        command = "\n".join(current_command).strip()
        if command:
            sql_commands.append(command)
        current_command = []

print(f"\n📊 총 {len(sql_commands)}개의 SQL 명령어 발견\n")

# Supabase 클라이언트
try:
    rag = SupabaseRAG()
    supabase = rag.client
    print("✅ Supabase 연결 성공\n")
except Exception as e:
    print(f"❌ Supabase 연결 실패: {e}")
    print("\n⚠️  Supabase가 설정되지 않았거나 로컬 인스턴스가 실행되지 않았습니다.")
    print("테이블 생성을 건너뛰고 웹 서버를 시작합니다.\n")
    exit(0)

# 각 명령어 실행
success_count = 0
error_count = 0

for i, command in enumerate(sql_commands, 1):
    # 명령어 종류 파악
    command_type = "Unknown"
    if command.upper().startswith("CREATE TABLE"):
        command_type = "CREATE TABLE"
        # 테이블 이름 추출
        table_name = command.split("CREATE TABLE IF NOT EXISTS")[1].split("(")[0].strip()
    elif command.upper().startswith("CREATE INDEX"):
        command_type = "CREATE INDEX"
    elif command.upper().startswith("CREATE POLICY"):
        command_type = "CREATE POLICY"
    elif command.upper().startswith("CREATE OR REPLACE VIEW"):
        command_type = "CREATE VIEW"
    elif command.upper().startswith("CREATE OR REPLACE FUNCTION"):
        command_type = "CREATE FUNCTION"
    elif command.upper().startswith("ALTER TABLE"):
        command_type = "ALTER TABLE"
    elif command.upper().startswith("INSERT INTO"):
        command_type = "INSERT"
    elif command.upper().startswith("COMMENT ON"):
        command_type = "COMMENT"

    try:
        print(f"[{i}/{len(sql_commands)}] {command_type}...", end=" ")

        # Supabase는 직접 SQL 실행을 지원하지 않으므로
        # 중요한 테이블만 Python API로 생성
        if command_type == "CREATE TABLE":
            print(f"⚠️  수동 생성 필요: {table_name}")
            error_count += 1
        else:
            print("⏭️  건너뜀")

    except Exception as e:
        print(f"❌ 실패: {e}")
        error_count += 1

print("\n" + "=" * 80)
print(f"✅ 성공: {success_count}개")
print(f"❌ 실패: {error_count}개")
print("=" * 80)

print("\n⚠️  Supabase Python 클라이언트는 직접 SQL 실행을 지원하지 않습니다.")
print("다음 방법 중 하나를 선택하세요:\n")
print("1. Supabase Dashboard (https://supabase.com)에서 SQL Editor 사용")
print("2. psql CLI로 직접 연결")
print("3. Supabase Studio에서 테이블 수동 생성")
print("\n📝 SQL 파일 위치: supabase_intelligence_system.sql")
