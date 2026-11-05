import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import print_token as pt  # noqa: E402


def test_read_token(tmp_path):
    f = tmp_path / ".hub_env"
    f.write_text("export HUB_TOKEN_CLAUDE='hub_abc-DEF_123'\nexport HUB_TOKEN_LOCAL='hub_zzz'\r\n")
    assert pt.read_token(f, "claude") == "hub_abc-DEF_123"
    assert pt.read_token(f, "LOCAL") == "hub_zzz"          # CRLF·대소문자 허용
    assert pt.read_token(f, "antigravity") is None
    assert pt.read_token(tmp_path / "none", "claude") is None
