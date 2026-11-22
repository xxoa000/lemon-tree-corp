# LemonTree Corp — Phase 1 Scaffold

10 AI employees, with the junior backend role open for hiring. External manager: 백서윤 부장 (LT-SYS-001).

## Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload
```
API: http://localhost:8000/docs

## Frontend
```bash
cd frontend
npm install
npm run dev
```
UI: http://localhost:3000

## Local services
```bash
docker compose up --build
```

## Scope / limitations
- Employees, teams, and external manager are currently in-memory initial fixtures, **not persisted in MySQL**.
- MySQL/Redis are provisioned in Compose but not yet connected to business operations.
- JWT, LemonTalk, Jira-like tasks, GitHub integration, actual agent runtime, approval gates, and Kubernetes are **not implemented**.
- The invocation semantics are represented as configuration data only; no secure command router exists yet.
- No GitHub repository, push, external deployment, or paid API call was performed.

## 워크스페이스 코드리뷰

기존 로컬 리뷰 계정 `junior`는 저장된 지원 기록에 접근할 때 사용할 수 있습니다.
백엔드 디렉터리에서 의존성을 설치하고, 로컬 리뷰용 비밀번호와 JWT 서명 키를 지정한 후 서버를 실행하세요.

```bash
cd backend
python -m pip install -r requirements.txt
export WORKPLACE_PASSWORD="$(python -c 'import secrets; print(secrets.token_urlsafe(18))')"
export WORKPLACE_JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python -m uvicorn app.main:app --reload
```

로컬 터미널의 `$WORKPLACE_PASSWORD` 값으로 로그인합니다. 프런트엔드는 별도 터미널에서
`cd frontend && npm ci && npm run dev`로 실행합니다.
업무 상태와 변경 이력은 기본적으로 `backend/.local/workplace.sqlite3`에 저장됩니다.
다른 API 주소가 필요하면 프런트엔드의 `BACKEND_URL`을 지정하세요.

## 백엔드 모듈과 DB 변경

기능 코드는 `backend/app/modules/<기능>/`에 둡니다. 각 모듈은 사용 범위에 따라
`<기능>_router.py`(API), `<기능>_schemas.py`(요청·응답),
`<기능>_service.py`(처리 로직), `<기능>_model.py`(DB 모델)를 둡니다.
파일과 함수의 역할은 docstring으로, 모델의 컬럼 설명은 `comment=`로 작성합니다.

서버는 시작할 때 업무 SQLite 파일에 미적용 Alembic 리비전을 반영합니다.
별도 파일에서 마이그레이션을 확인하려면 `WORKPLACE_DB_PATH`를 지정할 수 있습니다.

```bash
cd backend
python -m alembic upgrade head
python -m alembic check
# 모델을 바꾼 뒤 리비전을 만들고 생성된 내용을 검토합니다.
python -m alembic revision --autogenerate -m "describe schema change"
```

SQLite에서는 컬럼 코멘트를 테이블에 저장하지 않으므로 설명은 SQLAlchemy 모델에서 확인합니다.

프런트엔드에서는 `frontend/app/`이 Next.js 경로와 전역 스타일 진입점을 맡고,
`frontend/features/`에 화면·타입·API를 기능별로 모읍니다.
공통 데스크톱 화면은 `frontend/desk/`, 공통 API 호출과 기본 스타일은
`frontend/shared/`에 둡니다.

양쪽에서 공통으로 쓰는 기능명은 `org`(조직), `auth`(인증과 세션),
`task`(업무)입니다. 프런트엔드의 일정과 공고에는 `plan`, `jobs`를 사용합니다.
새 기능명은 의미가 분명한 3~4글자를 우선합니다.

스타일은 Tailwind CSS의 `@apply`를 사용해 별도 CSS 파일에 작성합니다.
컴포넌트 전용 스타일이 필요하면 조직 화면의 `org.module.css`처럼 CSS Modules로 분리합니다.

## 가입과 모의 채용

백엔드 의존성을 다시 설치한 뒤 리뷰용 실행 안내의 `WORKPLACE_JWT_SECRET`을 지정합니다.
신규 계정은 `WORKPLACE_PASSWORD` 설정 없이 생성하고 로그인할 수 있습니다. 이 변수는 기존
`junior` 리뷰 계정에만 필요합니다. 새 테이블은 서버 시작 시 Alembic으로 생성됩니다.

로그인 창에서 회원가입을 선택하고, 가입 완료 화면에서 복구 코드를 한 번 확인해 보관하세요.
아이디 찾기와 비밀번호 재설정에는 가입 이메일과 복구 코드가 필요합니다. 비밀번호를 재설정하면
이전 세션과 복구 코드는 무효화됩니다. 현재 복구 방식은 이메일 전송 없이 동작합니다.

공고 메뉴에서 로그인 후 주니어 백엔드·프런트엔드·풀스택 개발자 또는 AI 엔지니어 공고를 선택합니다.
텍스트 기반 PDF(최대 10쪽) 또는
UTF-8 TXT 이력서(최대 2MB)를 제출합니다. 이력서에서 추출한 텍스트와 답변, 전형 결과는
로컬 업무 DB에 저장합니다. 연습용 이력서를 사용하세요. 지원 건별로 서류 심사, 기술 면접,
인성 면접, 최종 결과가 진행됩니다. 면접은 직무별 기술 질문, 공통 인성 질문과 규칙 기반 평가를 사용합니다.
지원 내역에서 이전 전형 결과나 중단한 면접을 확인할 수 있고, 언제든 새로 지원할 수 있습니다.

## 로컬 MySQL과 Alembic

Compose의 백엔드와 Alembic은 같은 MySQL 데이터베이스를 사용합니다. 루트 `.env`에
`MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD`와 공개 포트
`MYSQL_PORT`, `REDIS_PORT`, `BACK_PORT`를 설정합니다. 로그인을 사용하려면
`WORKPLACE_JWT_SECRET`도 지정합니다.

```bash
docker compose config --quiet
docker compose up -d --build backend
docker compose exec backend python -m alembic current
docker compose exec backend python -m alembic check
```

백엔드가 시작되면 마이그레이션을 적용합니다. DBeaver에서 호스트 `127.0.0.1`,
포트 `MYSQL_PORT`, 데이터베이스 `MYSQL_DATABASE`로 연결하고 테이블 목록을 새로고침합니다.
프런트엔드는 Mac에서 `BACKEND_URL=http://127.0.0.1:<BACK_PORT> npm run dev`로 실행합니다
(`<BACK_PORT>`는 실제 포트 번호로 바꿉니다).

Uvicorn을 Mac에서 직접 실행한다면 같은 터미널에 `MYSQL_HOST=127.0.0.1`과 실제 공개
`MYSQL_PORT`, 계정 변수들을 내보내거나 `DATABASE_URL=mysql+pymysql://…`을 지정합니다.
그 상태에서 `backend/`의 `python -m alembic upgrade head`와 Uvicorn이 같은 DB에 연결됩니다.
`DATABASE_URL`이 있으면 우선 사용하며, 두 연결 설정이 모두 없으면 기존 로컬 SQLite를 사용합니다.
SQLite에 저장된 계정·지원·업무 데이터는 MySQL로 자동 복사되지 않습니다.

### 기존 SQLite 데이터 가져오기

대상 MySQL에 Alembic `0003`~`0010`가 적용돼 있어야 합니다. 이전 백엔드에서 저장한 SQLite
백업을 준비하고, 프로젝트 루트에서 아래 명령을 실행합니다. `backup`은 실제 백업 파일
경로로 바꿉니다.

```bash
backup="$PWD/backend/.local/workplace-backup.sqlite3"
docker compose run --rm --no-deps -T \
  -v "$PWD/backend/tools/import_sqlite.py:/app/import_sqlite.py:ro" \
  -v "$backup:/tmp/source.sqlite3:ro" \
  backend python /app/import_sqlite.py /tmp/source.sqlite3
```

기본 실행은 계획과 충돌 여부만 표시합니다. 계획을 확인하면 백엔드를 잠시 중지하고,
위 명령의 마지막에 `--apply`를 붙여 복사한 뒤 백엔드를 다시 시작합니다.
기존 업무 상태·이력과 지원 및 답변의 식별자를 유지합니다. 계정 ID가 직원 시드와 겹치면 해당 계정과 지원 소유권을 함께 연결합니다. 변경되지 않은 초기
업무는 SQLite 값으로 갱신할 수 있으며, 다른 데이터와 식별자나 고유값이 충돌하면
이번 가져오기를 취소합니다. SQLite 백업 파일은 읽기 전용으로 엽니다.

### 직원 계정과 마이페이지

Alembic `0005`는 기존 가입 정보를 보존하면서 직원 계정을 양수 ID와 영문 이름으로 정리합니다.
`0006`에서 채용 전인 주니어 백엔드 자리를 비워 조직 구성원 10명과 외부 관리자 백서윤만
시드로 유지합니다. 백서윤은 `admin`, 나머지와 신규 가입 계정은 사원(`member`)입니다.
시드 계정의 비밀번호 미설정 상태는 DB에 `NULL`로 저장합니다. 사용할 계정만 운영자가 다음 명령으로 활성화합니다.

```bash
docker compose exec backend python -m app.modules.auth.auth_seed LT-SYS-001
```

명령에 입력한 비밀번호와 출력된 복구 코드를 안전하게 보관하세요. 로그인 아이디는
`seoyun`입니다. 일반 직원은 사번에 맞춰 명령을 실행하며, 예를 들어
`LT-004`의 아이디는 `junhyeok`입니다. 같은 명령을 다시 실행하면 해당 계정의
비밀번호와 복구 코드가 교체되고 이전 세션이 무효화됩니다.

로그인한 가입·직원 계정은 마이페이지에서 이름, 이메일, 전화번호, 자기소개와 프로필 사진을
수정할 수 있습니다. 직원 계정은 처음 로그인한 뒤 복구에 사용할 이메일을 등록하세요.
사진은 JPEG·PNG·WebP(최대 5MB)를 받고 WebP로 저장합니다. 관리자는 직원 계정의 활성 상태도
확인할 수 있습니다.

### 마이페이지 이력서, LemonTalk와 TechVlog

Alembic `0007`은 개인 이력서 원본과 편집본, 대화방과 메시지 및 읽음 상태, TechVlog 게시글을 저장합니다.
이력서 관리에서는 텍스트 기반 PDF 또는 UTF-8 TXT를 업로드해 내용을 편집하고 원본을 다운로드할 수 있습니다.
원본은 최대 2MB를 DB에 저장하며 채용 지원 기록과는 별개입니다.

LemonTalk의 1:1 및 팀 대화는 로그인 계정 간에 실시간 이벤트(SSE)로 전달됩니다. 팀방을 만든
사용자만 참여자를 초대하거나 내보낼 수 있고, 초대받은 사용자는 참여 이후의 메시지를 볼 수 있습니다.
직원 계정도 로그인한 사용자가 직접 대화할 수 있으며, 로컬 모의 답장은 아래 설정을 따릅니다.

TechVlog 게시글은 계정으로 작성할 수 있으며 작성자와 관리자가 수정·삭제합니다.
기능 변경을 push할 때 `backend/app/modules/vlog/releases/`에 날짜로 시작하는 Markdown 파일을
포함하면, 해당 커밋의 백엔드에서 공개 노트로 표시됩니다. 기존 SQLite 이전 도구의 범위는 업무,
계정, 지원·면접 테이블입니다.

### Redis 대화 기록과 모의 예산

Alembic `0008`은 직원별 가상 연봉, 월 예산과 모의 사용 내역을 저장합니다. LemonTalk의 새 메시지와
읽음 위치는 Redis를 사용합니다. 방별 최근 1,000개, 전체 최근 3,000개를 유지하고 7일 동안 메시지가
없으면 대화 기록이 만료됩니다. `TALK_ROOM_LIMIT`, `TALK_TOTAL_LIMIT`, `TALK_TTL_SECONDS`로
조정할 수 있습니다. 기본 Compose Redis는 디스크에 기록을 남기지 않습니다.
계정과 대화방·멤버십은 MySQL에 남습니다. 이전 MySQL 메시지는 보존되며 새 채팅 화면은 Redis 기록을 사용합니다.

로컬에서 `WORKPLACE_LLM_MODE`의 기본값은 `mock`입니다. 직원에게 DM을 보내면 규칙 기반 모의 응답이
돌아오며 가상 예산만 처리합니다. `off`로 설정하면 모의 답장을 끌 수 있습니다. 실제 모델 호출은 구현하지
않았습니다. 관리자 마이페이지의 모의 LLM 예산 메뉴에서 연봉과 월 한도를 확인하고 조정할 수 있습니다.

공고에서는 파일을 생략해 기술 면접부터 연습할 수 있습니다. 파일을 올리면 기존대로 서류 심사를 먼저 진행합니다.

### 로컬 AI 모의면접 채점

Mac에 Ollama를 설치하고 모델을 다운로드합니다. 기존 Ollama 앱이나 서버가 이미 실행 중이면
먼저 종료하고 로컬 전용 서버를 실행합니다.

```bash
OLLAMA_NO_CLOUD=1 ollama serve
```

별도 터미널에서 모델을 받습니다.

```bash
ollama pull qwen2.5:7b
docker compose up -d --build backend
```

Compose 백엔드는 기본적으로 `http://host.docker.internal:11434`를 사용합니다. Mac에서
Uvicorn을 직접 실행하면 기본 주소는 `http://127.0.0.1:11434`입니다.
`INTERVIEW_OLLAMA_URL`과 `INTERVIEW_OLLAMA_MODEL`로 설정할 수 있으며,
채점에 지원하는 다운로드형 모델은 `qwen2.5:3b`와 `qwen2.5:7b`입니다.

채점에는 질문, 기준, 이번 답변을 사용합니다. 로컬 모델이 연결되지 않거나 검증 가능한 결과를
반환하지 않으면 점수를 기록하지 않고 같은 질문에서 다시 제출할 수 있습니다.
기존 면접 점수는 보존합니다. Alembic `0009`는 새 AI 평가 근거를 저장하고 직원 월 가상 예산
합계를 50,000원으로 조정합니다. 관리자가 인상하려면 다른 직원의 한도를 먼저 줄일 수 있습니다.

로컬 모델을 설치한 환경에서 의미 채점 검증을 실제로 실행하려면, 백엔드 가상환경을 활성화하고
`backend/`에서 다음을 실행합니다.

```bash
TEST_LOCAL_OLLAMA=1 python -m pytest -q tests/test_jobs_evaluator.py -k real_ollama
```

키워드 없이 올바르게 설명한 답변과 상태 코드를 반대로 사용한 답변을 비교합니다.

### 면접 복습과 코딩 테스트

Alembic `0010`은 생성한 면접 질문과 채점 기준, 개인 이력서 항목, 문제별 코딩 풀이를 저장합니다.
질문은 현재 직무와 전형, 공고에서 제출한 경우 이력서의 제한된 발췌를 로컬 모델에 전달해 작성합니다.
같은 질문을 다시 열어도 저장된 내용과 평가 기준을 사용합니다. 마이페이지의 모의면접 기록에서
1차·2차 또는 최종 결과, 제출 답변과 AI 피드백을 볼 수 있습니다.

마이페이지 이력서 관리와 직원 프로필은 같은 이력서 양식을 사용합니다. 개인 양식은 파일 없이도
작성할 수 있습니다. 파일을 올린 경우에는 원본과 추출 텍스트도 별도로 관리할 수 있습니다.

시작 메뉴의 코딩 테스트에서 LemonTree 연습 문제를 풀거나, 프로그래머스·백준·LeetCode·AtCoder의
공식 문제 URL을 연결할 수 있습니다. 풀이 코드는 문제별로 본인 계정에 저장되며, 외부 문제 본문과
제출·채점은 공식 사이트에서 이용합니다.
