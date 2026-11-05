-- Context Hub 스키마. 모든 시각은 UTC ISO8601 문자열.
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- 노트: kind = note | decision | handoff
-- status: draft(미검증, 신뢰 금지) | approved(사람이 승인)
CREATE TABLE IF NOT EXISTS notes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    project    TEXT NOT NULL,
    kind       TEXT NOT NULL DEFAULT 'note' CHECK (kind IN ('note','decision','handoff')),
    title      TEXT NOT NULL,
    body       TEXT NOT NULL,
    ref        TEXT,                          -- 포인터: 커밋 해시/파일 경로 등 원본 위치
    author     TEXT NOT NULL,                 -- 서버가 토큰으로 결정 (자기 신고 금지)
    status     TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','approved')),
    approved_by TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_notes_project ON notes(project, created_at);

-- trigram: 한국어 조사("SQLite와")·부분 문자열 검색을 위해 사용 (3글자 이상)
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
    title, body, content='notes', content_rowid='id', tokenize='trigram'
);
CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
    INSERT INTO notes_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
END;
CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
    INSERT INTO notes_fts(notes_fts, rowid, title, body) VALUES ('delete', old.id, old.title, old.body);
END;

-- 작업: open -> claimed(리스 만료 시 재점유 가능) -> done
CREATE TABLE IF NOT EXISTS tasks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project       TEXT NOT NULL,
    title         TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    status        TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','claimed','done')),
    assignee      TEXT,
    lease_expires TEXT,
    created_by    TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    result        TEXT
);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project, status);

-- 세션: 인수인계 단위
CREATE TABLE IF NOT EXISTS sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    project    TEXT NOT NULL,
    agent      TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at   TEXT,
    summary    TEXT
);

-- 감사 로그: 어떤 AI가 어떤 도구를 호출했고 결과가 어땠는지
CREATE TABLE IF NOT EXISTS audit_log (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts      TEXT NOT NULL,
    agent   TEXT NOT NULL,
    tool    TEXT NOT NULL,
    project TEXT,
    ok      INTEGER NOT NULL,
    ms      INTEGER NOT NULL,
    error   TEXT
);
