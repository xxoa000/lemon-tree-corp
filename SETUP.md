# LemonTree Corp 로컬 개발 가이드

기본 구성은 **Docker Compose로 백엔드·MySQL·Redis를 실행하고, Mac에서 프런트엔드를 실행**하는 방식입니다. 명령은 별도 안내가 없으면 저장소 루트 `lemon-tree-corp/`에서 실행합니다.

- [처음 내려받아 실행하기](#처음-내려받아-실행하기)
- [매일 개발하기](#매일-개발하기)
- [테스트와 DB 마이그레이션](#테스트와-db-마이그레이션)
- [Git 사용법](#git-사용법)
- [선택 설정과 문제 해결](#선택-설정과-문제-해결)

## 처음 내려받아 실행하기

### 1. 준비

Git, Docker Desktop 및 Compose v2, Node.js 22 이상과 npm을 준비합니다. Mac에서 백엔드 테스트나 실행기를 돌릴 경우 Python 3.12 또는 3.13도 준비합니다.

아직 저장소가 없다면 아래를 실행합니다. 이미 내려받았다면 기존 저장소 루트에서 시작하세요.

```bash
git clone https://github.com/xxoa000/lemon-tree-corp.git
cd lemon-tree-corp
git switch --track origin/codex
```

### 2. 환경변수 설정

기존 환경의 `.env`와 DB 설정을 유지하면 기존 계정과 기록을 계속 사용할 수 있습니다. 처음 구성할 때만 루트에 `.env`를 만들고 아래 항목을 입력합니다. **비밀번호와 JWT 값은 각자 생성한 값으로 교체**하세요.

```dotenv
BACK_PORT=8004
MYSQL_PORT=3310
REDIS_PORT=6383
MYSQL_DATABASE=lemontree
MYSQL_USER=lemontree
MYSQL_PASSWORD=replace_with_local_db_password
MYSQL_ROOT_PASSWORD=replace_with_local_root_password
WORKPLACE_JWT_SECRET=replace_with_generated_secret
```

JWT 값은 터미널에서 `openssl rand -hex 32`를 실행해 생성할 수 있습니다. `.env`에는 `KEY=value` 형식으로 값을 넣고, 포트 계산식이나 실행 명령은 터미널에서 사용하세요. 비밀값을 담은 `.env`와 `.env.local`은 커밋에서 제외됩니다.

`frontend/.env.local`을 만들고 `BACKEND_URL`을 위의 `BACK_PORT`와 맞춥니다.

```dotenv
BACKEND_URL=http://127.0.0.1:8004
```

### 3. 서버 실행

Docker Desktop이 실행 중인 상태에서 다음을 실행합니다. 백엔드가 시작되면 Alembic이 미적용 리비전을 적용합니다.

```bash
docker compose config --quiet
docker compose up -d --build backend
docker compose ps
```

새 터미널에서 저장소 루트로 이동한 뒤 프런트엔드를 설치하고 실행합니다.

```bash
cd frontend
npm ci --include=dev
npm run dev
```

`npm ci`는 락파일 기준으로 `frontend/node_modules`에 설치합니다. `--include=dev`는 개발 실행과 빌드에 필요한 Tailwind PostCSS·TypeScript를 포함합니다. Docker 백엔드의 Python 라이브러리는 컨테이너 이미지 안에 설치됩니다.

| 열기 | 예시 주소 |
| --- | --- |
| 사이트 | <http://localhost:3000> |
| 백엔드 Swagger 문서 | <http://localhost:8004/docs> |
| 백엔드 헬스 체크 | <http://localhost:8004/health> |

## 매일 개발하기

### 평소 실행

```bash
# 터미널 1 · 저장소 루트
docker compose up -d backend
```

```bash
# 터미널 2 · 저장소 루트에서 시작
cd frontend
npm run dev
```

### Git에서 코드를 받은 뒤

| 바뀐 항목 | 실행할 명령 |
| --- | --- |
| 백엔드 코드, Python 의존성, Alembic 파일 | 루트에서 `docker compose up -d --build backend` |
| 프런트엔드 의존성 또는 락파일 | 프런트엔드를 종료하고 `frontend/`에서 `npm ci --include=dev`, 이후 `npm run dev` |
| `frontend/.env.local` 또는 프런트엔드 설정 | 프런트엔드를 종료하고 `frontend/`에서 `npm run dev` |
| 프런트엔드 화면 코드 | 실행 중인 개발 서버에서 변경 확인 |

백엔드 로그는 루트에서 `docker compose logs -f backend`로 봅니다. 개발을 마치면 프런트엔드 터미널에서 **Ctrl+C**, 루트에서 `docker compose stop`을 사용합니다. MySQL 데이터는 `mysql_data` 볼륨에 남습니다. 기존 기록을 보존하려면 `docker compose down -v`를 사용하지 마세요.

## 테스트와 DB 마이그레이션

### Python 가상환경과 백엔드 테스트

아래 예시는 루트의 **`.venv`만** 사용합니다. `python3`로 가상환경을 만들고, 설치와 테스트는 가상환경의 Python 경로를 명시합니다. 패키지 설치 명령은 처음 실행하거나 `requirements.txt`가 바뀌었을 때 실행합니다.

```bash
# 저장소 루트
python3 -m venv .venv
./.venv/bin/python -m pip --require-virtualenv install -r backend/requirements.txt

# 같은 터미널에서
cd backend
../.venv/bin/python -m pytest -q
```

백엔드 면접 테스트는 기본적으로 모델 대신 테스트 응답을 사용합니다. Mac에서 실제 Ollama를 켜고 `qwen2.5:7b`를 준비했다면 `backend/`에서 별도로 검증합니다.

```bash
TEST_LOCAL_OLLAMA=1 ../.venv/bin/python -m pytest -q tests/test_jobs_evaluator.py -k real_ollama
```

### 프런트엔드 빌드

```bash
# frontend/
npm run build
```

빌드는 타입 검사도 수행합니다. 빌드한 화면을 열려면 같은 폴더에서 `npm run start`를 실행하세요. 기존 개발 서버가 실행 중이면 먼저 종료합니다.

### Alembic

```bash
# 저장소 루트 · 테스트 또는 개발 DB를 바라보는지 확인한 뒤 실행
docker compose exec backend python -m alembic current
docker compose exec backend python -m alembic upgrade head
docker compose exec backend python -m alembic check
```

DB 모델을 수정한 경우, 마이그레이션이 최신인 **개발 DB**에 연결한 상태에서 `backend/`에서 리비전을 생성하고 생성된 파일을 검토합니다. 가상환경의 Alembic은 이 터미널의 DB 연결 설정을 사용합니다. 기존 SQLite를 사용하려면 `WORKPLACE_DB_PATH`를, MySQL을 사용하려면 `DATABASE_URL` 또는 MySQL 환경변수를 지정하세요.

```bash
../.venv/bin/python -m alembic revision --autogenerate -m "describe schema change"
```

## Git 사용법

| 브랜치 | 용도 |
| --- | --- |
| `dahee` | 다희님 작업 |
| `codex` | Codex 작업과 리뷰 |
| `dev` | 리뷰를 마친 작업을 병합하는 통합 브랜치 |
| `main` | 검증 후 배포하는 브랜치 |

```bash
# 원격 작업 확인
git status --short
git fetch origin
git log --oneline HEAD..origin/codex

# codex 브랜치의 코드를 받을 때
git switch codex
git pull --ff-only origin codex
```

로컬에 해당 브랜치가 없으면 `git fetch origin` 후 `git switch --track origin/codex` 또는 `git switch --track origin/dahee`로 시작합니다. 작업 중인 변경이 있다면 브랜치를 전환하기 전에 `git status`로 확인하세요.

```bash
# 다희님 변경 확인과 커밋
git switch dahee
git status --short
git diff
git add -- README.md
git diff --cached
git commit -m "변경 내용 요약"
git push -u origin dahee
```

`git add`의 파일 경로는 실제 수정한 파일에 맞게 바꿉니다. 리뷰가 끝난 변경은 GitHub에서 대상 브랜치를 `dev`로 하여 PR을 열고, 배포 시 검증된 `dev`를 `main`으로 병합합니다. 기능 변경을 푸시할 때는 TechVlog 공개 노트를 `backend/app/modules/vlog/releases/`에 추가합니다. [브랜치 및 리뷰 규칙](AGENTS.md)

## 선택 설정과 문제 해결

### 로컬 Ollama와 직원 계정

Ollama가 이미 실행 중이면 모델 목록부터 확인합니다. 로컬 모델이 없을 때만 다운로드합니다.

```bash
ollama list
ollama pull qwen2.5:7b
```

Ollama 앱을 열거나, 앱이 닫혀 있다면 터미널에서 `OLLAMA_NO_CLOUD=1 ollama serve`를 실행합니다. Compose의 기본 모델 주소는 `http://host.docker.internal:11434`입니다. 루트 `.env`의 `INTERVIEW_OLLAMA_URL`과 `INTERVIEW_OLLAMA_MODEL`을 바꾸고 `docker compose up -d backend`로 반영할 수 있습니다. 현재 지원 모델은 `qwen2.5:7b`와 `qwen2.5:3b`입니다. LemonTalk는 `WORKPLACE_LLM_MODE=mock`으로 모의 답장을, `off`로 자동 답장 없는 채팅을 사용할 수 있습니다.

일반 계정은 사이트에서 회원가입하고 복구 코드를 보관합니다. DB에 시드된 관리자 계정을 처음 활성화하려면 아래를 실행합니다. 로그인 아이디는 `seoyun`이며, 같은 명령을 다시 실행하면 기존 비밀번호와 복구 코드가 교체됩니다.

```bash
docker compose exec backend python -m app.modules.auth.auth_seed LT-SYS-001
```

### Docker 백엔드 대신 Mac에서 Uvicorn 실행

기존 MySQL 기록을 계속 사용하려면 위의 Compose 실행을 사용하세요. SQLite로 따로 개발할 때는
가상환경을 준비하고, 기존 Docker 백엔드와 포트가 겹치지 않도록 합니다. SQLite 기본 파일은
`backend/.local/workplace.sqlite3`입니다.

```bash
# 루트에서 Redis만 실행합니다. 6383은 .env의 REDIS_PORT 예시입니다.
docker compose up -d redis
cd backend
export REDIS_URL=redis://127.0.0.1:6383/0
# 기존 WORKPLACE_JWT_SECRET이 없다면 생성한 값을 이 터미널에 지정합니다.
export WORKPLACE_JWT_SECRET=replace_with_generated_secret
../.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

이 방식으로 실행하는 동안은 `frontend/.env.local`의 `BACKEND_URL`을
`http://127.0.0.1:8000`으로 맞추고 프런트엔드를 다시 시작하세요.

### 자주 나오는 오류

| 증상 | 확인할 항목 |
| --- | --- |
| `@tailwindcss/postcss`를 찾을 수 없음 | `frontend/`에서 `npm ci --include=dev` 후 재시작 |
| 프런트엔드의 API 404 또는 로그인 세션 불일치 | `frontend/.env.local`의 `BACKEND_URL`을 Compose의 `BACK_PORT`와 일치시킨 뒤 Next.js 재시작 및 재로그인 |
| LemonTalk `/talk/rooms` 503 | 루트에서 `docker compose exec redis redis-cli ping` 및 백엔드 로그 확인 |
| DBeaver에서 테이블이 보이지 않음 | 호스트 `127.0.0.1`, `MYSQL_PORT`, `MYSQL_DATABASE`를 확인하고 `alembic current`와 테이블 새로고침 실행 |
| 기존 면접 기록이 보이지 않음 | 이전과 같은 로그인 계정, 백엔드 주소, DB 또는 MySQL 볼륨을 사용 중인지 확인 |

### SQLite 백업에서 기존 면접 기록 가져오기

SQLite에서 MySQL로 전환할 때는 기존 SQLite 백업과 대상 MySQL의 최신 마이그레이션이 필요합니다. 아래 명령은 읽기 전용으로 백업을 열고 계획만 표시합니다.

```bash
backup="$PWD/backend/.local/workplace-backup.sqlite3"
docker compose run --rm --no-deps -T \
  -v "$PWD/backend/tools/import_sqlite.py:/app/import_sqlite.py:ro" \
  -v "$backup:/tmp/source.sqlite3:ro" \
  backend python /app/import_sqlite.py /tmp/source.sqlite3
```

`backup`을 실제 백업 경로로 바꾸세요. 대상 DB도 백업한 뒤 백엔드를 잠시 멈추고, 계획을 검토한 명령의 끝에 `--apply`를 붙여 적용합니다. 적용 후 `docker compose up -d backend`로 다시 시작합니다. 백업에 남은 질문 원문·답변·평가를 가져올 수 있으며, 충돌이 있는 적용은 취소됩니다.

### Codex 업무 실행기

관리자가 승인한 개발 업무를 실제 실행하려면 Git과 Codex CLI가 설치된 Mac 또는 Linux의 별도 실행기 계정이 필요합니다. 실행기에는 GitHub 쓰기 자격 증명을 제공하지 않고, 전용 `CODEX_HOME`은 저장소 밖에 둡니다. 실행기 터미널에 백엔드와 동일한 DB의 연결 설정을 지정하세요. Mac에서 Compose MySQL에 붙는 경우 호스트는 `127.0.0.1`, 포트는 루트 `.env`의 `MYSQL_PORT`입니다.

```bash
# Python 가상환경 준비를 마친 뒤, 저장소 루트에서 시작
export CODEX_HOME="$HOME/.codex-lemontree-runner"
codex login
cd backend
LEMON_CODEX_REPO="$(git rev-parse --show-toplevel)" ../.venv/bin/python -m app.modules.work.work_runner
```

실행기가 현재 커밋을 작업별 복제본으로 만들고, **업무 → Codex 개발 작업**에서 진행 단계와 패치를 확인할 수 있습니다. 가상 예산은 작업당 500원이며 실제 청구는 Codex 인증 계정 또는 프로젝트 설정에서 관리합니다.
