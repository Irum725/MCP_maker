"""에이전트별 토큰 발급. 평문은 이 화면에 한 번만 출력되고, 파일에는 해시만 저장된다.

사용: uv run python scripts/gen_tokens.py [--out tokens.json] [--force] [이름 ...]
기본 이름: antigravity claude local
"""
import argparse
import json
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from context_hub.auth import DEFAULT_AGENTS, hash_token, new_token  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", default=list(DEFAULT_AGENTS))
    ap.add_argument("--out", default="tokens.json")
    ap.add_argument("--force", action="store_true", help="기존 파일을 덮어쓴다(기존 토큰 전부 무효화)")
    a = ap.parse_args()
    out = Path(a.out)
    if out.exists() and not a.force:
        sys.exit(f"{out}가 이미 있습니다. 덮어쓰려면 --force (기존 토큰이 모두 무효화됩니다)")
    agents, plain = {}, {}
    for n in a.names:
        t = new_token()
        agents[n] = {"sha256": hash_token(t)}
        plain[n] = t
    out.write_text(json.dumps({"agents": agents}, indent=2), encoding="utf-8")
    out.chmod(stat.S_IRUSR | stat.S_IWUSR)
    print(f"# {out} 저장 완료 (해시만 저장됨). 아래 토큰은 지금만 볼 수 있습니다.\n")
    for n, t in plain.items():
        print(f"{n}: {t}")


if __name__ == "__main__":
    main()
