"""클라이언트별 연결 설정 조각을 토큰이 채워진 상태로 출력한다 (복사해서 붙여넣기용).

사용: uv run python scripts/print_client_config.py {claude|antigravity|ollmcp} [--url URL]
주의: 출력에 실제 토큰이 들어 있으니 화면 공유·캡처·채팅 붙여넣기를 피할 것.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from print_token import read_token  # noqa: E402

ENV = Path(__file__).resolve().parent.parent / ".hub_env"
AGENT_FOR = {"claude": "claude", "antigravity": "antigravity", "ollmcp": "local"}


def build(client: str, token: str, url: str) -> str:
    if client == "claude":
        return ('claude mcp add --transport http --scope local context-hub '
                f'{url} --header "Authorization: Bearer {token}"')
    if client == "antigravity":
        cfg = {"mcpServers": {"context-hub": {
            "serverUrl": url,
            "headers": {"Authorization": f"Bearer {token}"},
            "timeoutSeconds": 600}}}
        return json.dumps(cfg, indent=2, ensure_ascii=False)
    if client == "ollmcp":
        return ('ollmcp mcp add --transport http --header "Authorization: Bearer '
                f'{token}" context-hub {url}')
    raise ValueError(client)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("client", choices=sorted(AGENT_FOR))
    ap.add_argument("--url", default="http://127.0.0.1:8765/mcp")
    a = ap.parse_args()
    token = read_token(ENV, AGENT_FOR[a.client])
    if not token:
        print(f"{ENV.name}에서 '{AGENT_FOR[a.client]}' 토큰을 찾지 못했습니다. "
              "start.command(.bat)를 실행하거나 gen_tokens.py --env-out .hub_env 로 발급하세요.", file=sys.stderr)
        return 1
    print("# 경고: 아래에 실제 토큰이 들어 있습니다. 화면 공유/캡처/채팅 붙여넣기 금지", file=sys.stderr)
    print(build(a.client, token, a.url))
    return 0


if __name__ == "__main__":
    sys.exit(main())
