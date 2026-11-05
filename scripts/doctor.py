"""실행 전 진단: 무엇이 빠졌는지 확인하고, 다음에 칠 명령을 알려 준다.

사용: uv run python scripts/doctor.py [--url http://127.0.0.1:8765/mcp]
(토큰으로 도구 목록까지 확인하려면 HUB_TOKEN=<토큰> 을 함께 지정)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
Check = tuple[bool, str, str]  # (통과, 설명, 실패 시 할 일)


def check_python() -> Check:
    v = sys.version_info
    return (v >= (3, 10), f"Python {v.major}.{v.minor}", "Python 3.10 이상이 필요합니다: `uv python install 3.12`")


def check_venv(root: Path = ROOT) -> Check:
    """다른 OS에서 만든 .venv가 남아 있으면 실행이 깨진다. pyvenv.cfg로 감지한다."""
    cfg = root / ".venv" / "pyvenv.cfg"
    if not cfg.exists():
        return False, ".venv 없음", "`uv sync` 를 실행하세요"
    home = ""
    for line in cfg.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("home"):
            home = line.split("=", 1)[1].strip()
    if home and not Path(home).exists():
        return False, f".venv가 다른 환경에서 만들어짐 (파이썬 경로 없음: {home})", \
            "`rm -rf .venv && uv sync` 로 다시 만드세요"
    return True, ".venv 정상", ""


def check_tokens(path: Path | None = None) -> Check:
    p = path or Path(os.environ.get("HUB_TOKENS", ROOT / "tokens.json"))
    if not p.exists():
        return False, f"{p.name} 없음", "`uv run python scripts/gen_tokens.py` 로 토큰을 발급하세요 (평문은 한 번만 표시)"
    try:
        names = list(json.loads(p.read_text(encoding="utf-8")).get("agents", {}))
    except (ValueError, AttributeError):
        return False, f"{p.name} 형식 오류", "`gen_tokens.py --force` 로 다시 발급하세요 (기존 토큰은 무효화)"
    if not names:
        return False, "등록된 에이전트 없음", "`gen_tokens.py --force` 로 다시 발급하세요"
    return True, f"토큰 등록: {', '.join(names)}", ""


def check_db_dir(path: Path | None = None) -> Check:
    d = (path or Path(os.environ.get("HUB_DB", ROOT / "hub_data" / "hub.db"))).parent
    ok = d.exists() and os.access(d, os.W_OK)
    return ok, f"데이터 폴더 {d.name}/ 쓰기 {'가능' if ok else '불가'}", f"`mkdir -p {d}` 후 권한을 확인하세요"


def check_server(url: str, timeout: float = 2.0) -> Check:
    """토큰 없이 두드려 본다: 401이면 서버가 떠 있고 인증이 켜진 것(정상)."""
    req = urllib.request.Request(url, data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
    try:
        urllib.request.urlopen(req, timeout=timeout)
        return False, "서버가 토큰 없이 응답함 (인증이 꺼져 있음)", "서버가 이 프로젝트의 버전인지 확인하세요"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return True, f"서버 응답 + 인증 동작 ({url})", ""
        return False, f"예상 밖 응답 HTTP {e.code}", "서버 터미널의 로그를 확인하세요"
    except (urllib.error.URLError, OSError):
        return False, f"서버에 연결 안 됨 ({url})", "다른 터미널에서 `uv run python -m context_hub.server` 를 실행하세요"


async def _tool_names(url: str, token: str) -> list[str]:
    from fastmcp import Client
    async with Client(url, auth=token) as c:
        return [t.name for t in await c.list_tools()]


def check_login(url: str, token: str | None) -> Check | None:
    if not token:
        return None
    try:
        names = asyncio.run(_tool_names(url, token))
    except Exception as e:  # 인증 실패/연결 실패 모두 안내
        return False, f"토큰으로 연결 실패: {type(e).__name__}", "토큰을 다시 확인하세요 (발급 시 한 번만 표시됨)"
    return True, f"토큰 인증 성공, 도구 {len(names)}개", ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8765/mcp")
    url = ap.parse_args().url
    results = [check_python(), check_venv(), check_tokens(), check_db_dir(), check_server(url)]
    server_ok = results[-1][0]
    login = check_login(url, os.environ.get("HUB_TOKEN")) if server_ok else None
    if login:
        results.append(login)
    todo = []
    for ok, msg, hint in results:
        print(f"{'✓' if ok else '✗'} {msg}")
        if not ok:
            todo.append(hint)
    if not os.environ.get("HUB_TOKEN") and server_ok:
        print("· HUB_TOKEN=<토큰> 을 지정하면 도구 목록까지 확인합니다")
    if todo:
        print("\n다음에 할 일:")
        for i, h in enumerate(todo, 1):
            print(f"  {i}. {h}")
        return 1
    print("\n모두 정상입니다. 이제 Claude Code 등에 연결하세요 (README '클라이언트 연결').")
    return 0


if __name__ == "__main__":
    sys.exit(main())
