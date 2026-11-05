import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import print_client_config as pc  # noqa: E402

URL = "http://127.0.0.1:8765/mcp"


def test_claude_uses_local_scope_not_project():
    s = pc.build("claude", "hub_x", URL)
    assert "--scope local" in s and "--scope project" not in s and "Bearer hub_x" in s


def test_antigravity_json_is_valid_and_has_remote_fields():
    cfg = json.loads(pc.build("antigravity", "hub_x", URL))
    srv = cfg["mcpServers"]["context-hub"]
    assert srv["serverUrl"] == URL and srv["headers"]["Authorization"] == "Bearer hub_x"


def test_ollmcp_command():
    s = pc.build("ollmcp", "hub_x", URL)
    assert s.startswith("ollmcp mcp add --transport http") and "--header" in s and URL in s
