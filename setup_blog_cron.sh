#!/bin/bash
# 블로그 자동 업데이트 크론잡 설정 스크립트

SCRIPT_DIR="/home/harvis/ai-hedge-fund"
PYTHON_PATH="/home/harvis/ai-hedge-fund/ai-hedge-env/bin/python"
UPDATE_SCRIPT="$SCRIPT_DIR/update_blog_insights.py"
LOG_FILE="/tmp/update_blog_insights.log"

# 크론 작업 내용 (매일 새벽 3시 실행)
CRON_JOB="0 3 * * * cd $SCRIPT_DIR && $PYTHON_PATH $UPDATE_SCRIPT >> $LOG_FILE 2>&1"

echo "================================================"
echo "블로그 자동 업데이트 크론잡 설정"
echo "================================================"
echo ""
echo "작업 내용:"
echo "  - 스크립트: $UPDATE_SCRIPT"
echo "  - 실행 시간: 매일 새벽 3시"
echo "  - 로그 파일: $LOG_FILE"
echo ""

# 기존 크론탭 백업
echo "📋 기존 크론탭 백업 중..."
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null || echo "기존 크론탭이 없습니다."

# 기존에 동일한 작업이 있는지 확인
if crontab -l 2>/dev/null | grep -q "$UPDATE_SCRIPT"; then
    echo "⚠️  이미 크론잡이 등록되어 있습니다."
    echo "   기존 작업을 제거하고 새로 등록합니다."
    # 기존 작업 제거
    (crontab -l 2>/dev/null | grep -v "$UPDATE_SCRIPT") | crontab -
fi

# 새 크론잡 추가
echo "✅ 크론잡 등록 중..."
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

# 등록 확인
echo ""
echo "================================================"
echo "✅ 크론잡 등록 완료!"
echo "================================================"
echo ""
echo "등록된 크론잡:"
crontab -l | grep "$UPDATE_SCRIPT"
echo ""
echo "크론 로그 확인 방법:"
echo "  tail -f $LOG_FILE"
echo ""
echo "크론잡 목록 확인:"
echo "  crontab -l"
echo ""
echo "크론잡 제거:"
echo "  crontab -e"
echo ""
