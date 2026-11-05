"""`.hub_env`에서 에이전트 토큰 하나를 꺼내 출력한다 (Windows .bat용 보조 도구).

사용: uv run python scripts/print_token.py claude [--file .hub_env]
없으면 아무것도 출력하지 않고 종료 코드 1.
"""
import argparse
import sys
from pathlib import Path


def read_token(path: Path, name: str) -> str | None:
    key = f"HUB_TOKEN_{name.upper()}"
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip().removeprefix("export ").strip()
        k, sep, v = line.partition("=")
        if sep and k.strip() == key:
            return v.strip().strip("'\"") or None
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--file", default=".hub_env")
    a = ap.parse_args()
    tok = read_token(Path(a.file), a.name)
    if not tok:
        return 1
    print(tok)
    return 0


if __name__ == "__main__":
    sys.exit(main())
