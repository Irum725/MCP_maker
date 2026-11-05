#!/bin/bash
# Claude Code 원클릭 연결: .hub_env의 claude 토큰으로 context-hub를 등록한다.
# 등록 범위는 local(저장소 밖, ~/.claude.json)이다. project 범위는 토큰이 .mcp.json에 평문으로 들어가
# 공개 저장소로 유출될 수 있어 쓰지 않는다.
cd "$(dirname "$0")" || exit 1
pause() { echo; read -r -p "Enter 키를 누르면 창이 닫힙니다" _; }
URL="http://127.0.0.1:${HUB_PORT:-8765}/mcp"

if ! command -v claude >/dev/null 2>&1; then
  echo "✗ claude 명령을 찾을 수 없습니다. Claude Code가 설치되어 있는지 확인하세요."
  pause; exit 1
fi

if [ ! -f .hub_env ]; then
  echo "토큰 평문 파일(.hub_env)이 없습니다."
  echo "새로 발급하면 기존 토큰은 모두 무효화되고, 실행 중인 서버를 껐다 켜야 합니다."
  read -r -p "새로 발급할까요? [y/N] " ans
  if [ "$ans" != "y" ] && [ "$ans" != "Y" ]; then echo "취소했습니다."; pause; exit 1; fi
  command -v uv >/dev/null 2>&1 || { echo "✗ uv가 없습니다"; pause; exit 1; }
  uv run python scripts/gen_tokens.py --force --env-out .hub_env > /dev/null || { pause; exit 1; }
  echo "✓ 재발급 완료. start.command로 서버를 (다시) 시작하세요."
fi

# shellcheck disable=SC1091
source .hub_env
if [ -z "$HUB_TOKEN_CLAUDE" ]; then echo "✗ .hub_env에 claude 토큰이 없습니다"; pause; exit 1; fi

claude mcp remove context-hub >/dev/null 2>&1   # 이미 있으면 교체
claude mcp add --transport http --scope local context-hub "$URL" \
  --header "Authorization: Bearer $HUB_TOKEN_CLAUDE" || { echo "✗ 등록 실패"; pause; exit 1; }
echo
claude mcp list
echo
echo "✓ 등록 완료. 이 폴더에서 Claude Code를 실행하면 context-hub 도구를 쓸 수 있습니다."
echo "  (서버는 start.command로 켜 두어야 합니다)"
pause
