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

대상 MySQL에 Alembic `0003`~`0006`가 적용돼 있어야 합니다. 이전 백엔드에서 저장한 SQLite
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
