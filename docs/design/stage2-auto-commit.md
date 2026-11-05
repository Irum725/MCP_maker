# 2단계 설계: 작업 완료 시 git 자동 커밋

- 허브 작업: `MCP_maker#1` · 작성: claude (설계 검토 역할) · 2026-11-05
- 상태: **제안** (사람 승인 전. 승인되면 decision 노트를 `approve_note.py`로 승인)

## 1. 목표와 범위
`complete_task`로 작업을 끝낼 때 그 작업의 코드 변경이 **검증을 통과한 커밋으로 남고**, 허브의 작업 기록이
그 **커밋 해시를 가리키게** 한다 (AGENTS.md 4절 "요약보다 포인터", 7절 "작업 단위마다 커밋·푸시").

범위 밖: 브랜치/PR 자동화, 충돌 해결, 리뷰 승인 흐름(MRTR은 별도 단계).

## 2. 핵심 결정: 커밋은 클라이언트가 하고, 허브는 검증·기록만 한다

| 안 | 내용 | 판단 |
|---|---|---|
| A. 서버가 커밋 | `complete_task(commit=true, files=[...])` → 서버 프로세스가 `git add/commit/push` | **기각** |
| **B. 클라이언트가 커밋, 서버는 검증·기록** | 에이전트가 헬퍼 스크립트로 커밋 → `complete_task(..., commit="<sha>")` → 서버가 읽기 전용으로 확인 후 저장 | **채택** |
| C. 서버가 커밋 메시지만 생성 | B에서 검증 없이 메시지 템플릿만 제공 | B의 부분집합 |

A를 기각한 이유:
1. **작업 트리가 서버 것이 아니다.** 에이전트마다 작업 디렉터리, 브랜치, 미커밋 변경이 다를 수 있다. 서버가 커밋하면 남의 변경이 섞인다.
2. **보안.** 서버가 쓰기 git 명령을 실행하면 `.git/hooks`, `core.fsmonitor`, `core.sshCommand` 같은 저장소 설정을 거쳐 임의 코드가 실행된다. 이렇게 되면 모델이 넘긴 인자 하나로 서버 권한의 코드가 돈다.
3. **원칙 충돌.** AGENTS.md 4절 "파괴적·외부 전송 도구는 만들지 않는다". `push`는 외부 전송이다.
4. **검증 비용.** `pytest`와 eval을 서버 요청 안에서 돌리면 도구 호출이 수십 초 동안 막힌다 (stateless HTTP와 맞지 않음).

B는 에이전트가 이미 가진 셸 권한 안에서 커밋하고, 서버는 **"그 커밋이 정말 있고, 이 작업의 것이 맞는지"만** 확인하므로
서버의 신뢰 경계가 늘지 않는다.

## 3. 흐름
```
에이전트                                  허브 서버
  │ (코드 수정)                              │
  │ scripts/task_commit.py --task 1 ...      │
  │   1) 검증: pytest -q, eval --dry-run     │
  │   2) 지정 파일만 stage (비밀 파일 거부)    │
  │   3) commit (메시지에 Hub-Task 트레일러)  │
  │   4) push (기본, --no-push로 끔)          │
  │   → sha 출력                              │
  │ complete_task(task_id=1, result, commit=sha) ─►│ 읽기 전용 git 검증
  │                                          │  - 커밋 존재 / 트레일러 일치
  │ ◄──── {status: done, commit: {sha, verified}} │ task_commits에 기록
```

## 4. 구성 요소

### 4.1 `scripts/task_commit.py` (신규, 클라이언트 측)
```
uv run python scripts/task_commit.py --project MCP_maker --task 1 \
    --type feat -m "작업 완료 시 커밋 해시 기록" [--no-push] [--skip-verify] -- <경로...>
```
- **검증 먼저:** AGENTS.md 6절 두 명령을 실행하고, 실패하면 커밋하지 않고 종료 코드 1로 끝낸다. `--skip-verify`는 문서만 바꾼 경우를 위한 것이고, 트레일러에 `Hub-Verified: skipped`를 남긴다.
- **명시한 경로만 stage:** `git add -- <경로...>`. 경로가 없거나 `.`/`-A`면 거부한다. 다른 사람의 변경이 섞이는 것을 막기 위해서다.
- **비밀 차단:** stage된 목록(`git diff --cached --name-only`)에 `tokens.json`, `.env*`, `.hub_env`, `.mcp.json`, `hub_data/*.db*`가 있으면 중단한다. 이 목록은 `.gitignore`와 같은 원본 상수에서 가져온다.
- **메시지 형식:** AGENTS.md 7절 규칙에 트레일러를 더한다.
  ```
  feat: 작업 완료 시 커밋 해시 기록

  Hub-Task: MCP_maker#1
  Hub-Agent: claude
  Hub-Verified: pytest,eval-dry-run
  Co-Authored-By: ...
  ```
  `git interpret-trailers`로 파싱할 수 있는 표준 트레일러라서 서버 검증과 사람의 `git log --grep` 모두에 쓸 수 있다.
- **push:** 기본으로 `git push origin HEAD`를 실행한다 (AGENTS.md 7절). 실패해도 커밋은 남기고 sha를 출력한 뒤 경고만 남긴다. 이 경우 `complete_task`는 해도 되고 결과에 "push 실패"를 적는다.
- **허브와 통신하지 않는다.** 스크립트는 토큰이 필요 없다. `complete_task` 호출은 에이전트가 MCP로 한다 (신원은 토큰으로만 정한다는 원칙 유지).

### 4.2 프로젝트 → 저장소 매핑 (신규 설정, 사람이 관리)
`hub_projects.toml` (gitignore 대상 아님, 비밀 없음):
```toml
[projects.MCP_maker]
repo = "/Users/irum/AppDeloper/MCP_maker"
verify_commits = "required"   # required | optional | off
```
- 에이전트 도구로는 바꿀 수 없다 (승인 기능과 같은 원칙).
- 매핑이 없는 프로젝트는 커밋을 **미검증으로만 기록**한다 (`verified=false`).

### 4.3 서버 검증 (`context_hub/gitcheck.py`, 신규, 읽기 전용)
- sha 형식 검사: `^[0-9a-f]{7,40}$`. 이 검사를 통과한 값만 인자로 넘기고 셸은 쓰지 않는다 (`subprocess.run([...], shell=False)`).
- 실행 형태:
  ```
  git -C <repo> -c core.fsmonitor=false -c core.hooksPath=/dev/null \
      --no-optional-locks log -1 --format=%H%x00%(trailers:key=Hub-Task,valueonly) <sha> --
  ```
  타임아웃은 3초. 환경 변수는 `GIT_TERMINAL_PROMPT=0`과 `GIT_CONFIG_NOSYSTEM=1`.
- 확인 항목:
  1. 커밋이 존재한다 (짧은 sha는 전체 40자로 정규화해서 저장).
  2. `Hub-Task` 트레일러가 `<project>#<task_id>`와 일치한다. 다른 작업의 커밋을 갖다 붙이는 것을 막는다.
  3. (선택) `git merge-base --is-ancestor <sha> origin/main`로 push 여부를 확인하고 `pushed` 플래그로 기록한다. 실패해도 오류로 처리하지 않는다.
- `verify_commits="required"`에서 검증에 실패하면 `HubError`를 낸다. 작업은 **claimed로 남고** 에이전트가 고쳐서 다시 호출한다.

### 4.4 스키마 변경
작업 하나에 커밋이 여러 개일 수 있으므로 별도 테이블로 둔다.
```sql
CREATE TABLE IF NOT EXISTS task_commits (
    task_id   INTEGER NOT NULL REFERENCES tasks(id),
    sha       TEXT NOT NULL,          -- 40자 정규화
    verified  INTEGER NOT NULL,       -- 서버가 트레일러까지 확인했는가
    pushed    INTEGER,                -- NULL = 확인 안 함
    agent     TEXT NOT NULL,          -- 토큰 신원
    added_at  TEXT NOT NULL,
    PRIMARY KEY (task_id, sha)
);
```
`CREATE TABLE IF NOT EXISTS`라 기존 DB에 그대로 적용된다 (별도 마이그레이션 불필요).

### 4.5 도구 인터페이스 변경
- `complete_task(task_id, result, commit: str = "")`: 쉼표로 여러 sha를 받는다. 비워 두면 지금처럼 동작한다 (하위 호환).
  설명 첫 문장: "내가 점유한 작업을 끝낼 때 호출한다. 코드를 바꿨다면 task_commit.py가 출력한 커밋 해시를 commit에 넣는다."
- `list_tasks`, `start_session` 결과의 작업 항목에 `commits: [{sha, verified, pushed}]`를 붙인다.
- 새 도구는 만들지 않는다 (작은 모델의 도구 선택 부담을 늘리지 않기 위해서다).

## 5. 위협과 대응 요약
| 위협 | 대응 |
|---|---|
| 모델이 넘긴 sha로 명령 주입 | 정규식 검사, `shell=False`, 인자 뒤 `--` |
| 저장소 설정(hooks/fsmonitor)으로 서버에서 코드 실행 | 서버는 읽기 명령만, `-c core.hooksPath=/dev/null -c core.fsmonitor=false` |
| 다른 작업·다른 AI의 커밋을 내 작업으로 기록 | `Hub-Task` 트레일러 일치 검사, 기록자는 토큰 신원 |
| 비밀 파일 커밋 | 스크립트가 stage 목록 차단 + 기존 `.gitignore` |
| 검증 없이 커밋 | 스크립트 기본이 검증. 건너뛰면 트레일러에 남아 감사할 수 있음 |
| 저장소 경로 조작 | 경로는 사람이 관리하는 `hub_projects.toml`에서만 읽음 |

## 6. 구현 순서 (antigravity 담당 제안, 커밋 단위)
1. `feat:` `task_commits` 스키마와 `Hub.add_task_commits` / 조회 (+ `tests/test_db.py`)
2. `feat:` `gitcheck.py` 읽기 전용 검증 (+ 임시 git 저장소 fixture로 테스트: 존재, 트레일러 불일치, 잘못된 sha, 매핑 없음)
3. `feat:` `complete_task`에 `commit` 인자 추가, `hub_projects.toml` 로드 (+ `tests/test_server.py`, **`eval/scenarios.json`에 commit 시나리오 추가**: AGENTS.md 5절)
4. `feat:` `scripts/task_commit.py` (+ 비밀 차단, 경로 미지정 거부 테스트)
5. `docs:` MANUAL.md 도구 레퍼런스와 AGENTS.md 3절 루틴 4번 갱신

## 7. 결정이 필요한 것 (사람)
1. push를 스크립트 기본값으로 둘지 (제안: 기본 push, AGENTS.md 7절과 일치).
2. `verify_commits` 기본값을 `required`로 할지 `optional`로 할지 (제안: 처음 1주는 `optional`로 데이터를 본 뒤 `required`).
3. 코드 변경이 없는 작업(설계, 조사)에서 commit을 생략해도 되는지 (제안: 허용).
