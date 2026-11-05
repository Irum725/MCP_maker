#!/bin/bash
# Context Hub 원클릭 실행: Finder에서 더블클릭하면 환경 준비 → (최초 1회) 토큰 발급 → 서버 시작
cd "$(dirname "$0")" || exit 1
pause() { echo; read -r -p "Enter 키를 누르면 창이 닫힙니다" _; }

if ! command -v uv >/dev/null 2>&1; then
  echo "✗ uv가 설치되어 있지 않습니다."
  echo "  설치: brew install uv   (또는 curl -LsSf https://astral.sh/uv/install.sh | sh)"
  pause; exit 1
fi

echo "[1/3] 환경 준비 (uv sync)"
uv sync -q || { echo "✗ 환경 준비 실패"; pause; exit 1; }

if [ ! -f tokens.json ]; then
  echo "[2/3] 첫 실행: 에이전트 토큰 발급"
  uv run python scripts/gen_tokens.py --env-out .hub_env > /dev/null || { pause; exit 1; }
  echo "  토큰을 .hub_env에 저장했습니다 (본인만 읽기 가능, git 제외)."
  echo "  이어서 'connect-claude.command'를 더블클릭하면 Claude Code에 연결됩니다."
else
  echo "[2/3] 토큰 있음 (건너뜀)"
fi

PORT="${HUB_PORT:-8765}"
if lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "✓ 이미 포트 $PORT 에서 서버가 실행 중입니다. 이 창은 닫아도 됩니다."
  pause; exit 0
fi

echo "[3/3] 서버 시작 — 종료하려면 Ctrl+C (창을 닫아도 종료됩니다)"
uv run python -m context_hub.server
echo "서버가 종료되었습니다."
pause
