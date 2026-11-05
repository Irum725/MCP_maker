from datetime import timedelta

import pytest

from context_hub.db import Hub, HubError, utcnow


@pytest.fixture
def hub(tmp_path):
    return Hub(tmp_path / "hub.db")


def test_note_search_and_trust(hub):
    n = hub.add_note("proj", "결정: 저장소", "SQLite와 FTS5를 쓴다", "claude", kind="decision")
    assert n["status"] == "draft"
    hits = hub.search_notes("proj", "SQLite")
    assert hits and hits[0]["trusted"] is False
    assert hub.search_notes("proj", "SQLite", include_drafts=False) == []
    hub.approve_note(n["id"], "human")
    assert hub.search_notes("proj", "SQLite", include_drafts=False)[0]["trusted"] is True


def test_search_is_project_scoped_and_safe(hub):
    hub.add_note("a", "t", "비밀 내용 alpha", "claude")
    assert hub.search_notes("b", "alpha") == []
    hub.search_notes("a", 'alpha" OR "x')  # FTS 구문 주입이 오류를 내지 않아야 함
    with pytest.raises(HubError):
        hub.search_notes("../etc", "x")


def test_draft_note_has_warning(hub):
    n = hub.add_note("p", "t", "본문", "local")
    assert "warning" in hub.read_note(n["id"])


def test_claim_is_exclusive_and_lease_expires(hub):
    t = hub.create_task("p", "작업", "", "claude")["task_id"]
    now = utcnow()
    hub.claim_task(t, "antigravity", 30, now=now)
    with pytest.raises(HubError):
        hub.claim_task(t, "local", 30, now=now + timedelta(minutes=5))
    # 리스 만료 후에는 다른 에이전트가 가져갈 수 있다
    r = hub.claim_task(t, "local", 30, now=now + timedelta(minutes=31))
    assert r["assignee"] == "local"


def test_only_assignee_can_complete(hub):
    t = hub.create_task("p", "작업", "", "claude")["task_id"]
    hub.claim_task(t, "antigravity")
    with pytest.raises(HubError):
        hub.complete_task(t, "local", "x")
    assert hub.complete_task(t, "antigravity", "완료")["status"] == "done"


def test_session_handoff_roundtrip(hub):
    s = hub.start_session("p", "claude")
    out = hub.end_session(s["session_id"], "claude", "요약", handoff="다음은 X를 하세요")
    assert "handoff_note" in out
    nxt = hub.start_session("p", "local")
    assert nxt["latest_handoff"]["status"] == "draft"
    with pytest.raises(HubError):
        hub.end_session(s["session_id"], "local", "탈취 시도")


def test_korean_and_short_queries(hub):
    hub.add_note("p", "한글 노트", "토큰 인증은 서버가 신원을 정한다. 50% 완료_됨", "claude")
    assert hub.search_notes("p", "인증은")          # 조사 포함 부분 일치
    assert hub.search_notes("p", "서버")            # 2글자 → LIKE 대체
    assert hub.search_notes("p", "50%")             # LIKE 와일드카드가 이스케이프되는지
    assert hub.search_notes("p", "없는검색어") == []
