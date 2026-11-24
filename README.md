# LemonTree Corp

AI 직원으로 구성된 가상 회사를 운영하고, 개발 업무와 모의면접을 경험하는 협업 워크스페이스입니다. 프런트엔드는 **Next.js·React·TypeScript·Tailwind CSS**, 백엔드는 **FastAPI·SQLAlchemy·Alembic**을 사용합니다.

처음 내려받았거나 개발 서버를 다시 열려면 [SETUP.md](SETUP.md)를 참고하세요.

## 주요 기능

| 기능 | 역할 |
| --- | --- |
| 회사·일정·업무 | 조직도와 직원 이력서형 프로필, 일정 화면, 업무 상태를 확인합니다. |
| 공고·모의면접 | 백엔드·프런트엔드·풀스택·AI 직무를 연습합니다. 이력서는 선택이며 로컬 Ollama가 질문을 생성하고 평가합니다. |
| 마이페이지 | 회원정보, 프로필 사진, 개인 이력서를 관리하고 저장된 면접 질문·답변·피드백을 다시 봅니다. |
| LemonTalk | 1:1 및 팀 대화, 읽지 않은 메시지, 로컬 Ollama 직원 답장을 지원합니다. |
| 코딩 테스트 | 자체 연습 문제와 외부 공식 문제 링크를 사용하고, 문제별 풀이를 저장합니다. 외부 채점은 공식 사이트에서 진행합니다. |
| TechVlog | 게시글과 배포된 백엔드에 포함된 Markdown 릴리스 노트를 읽습니다. |
| Codex 개발 작업 | 관리자가 업무 화면에서 직원별 요청과 이미지를 등록하고 실행을 승인합니다. 별도 실행기가 작업하고 검토용 변경 내역을 반환합니다. |

## 폴더 구조

```text
lemon-tree-corp/
├── backend/
│   ├── app/
│   │   ├── main.py            FastAPI 진입점, 라우터 등록
│   │   ├── database.py        DB 연결과 Alembic 실행
│   │   └── modules/           기능별 API, 처리 로직, DB 모델
│   ├── migrations/            Alembic 설정과 versions/ 리비전
│   ├── tests/                 API, 저장소, 마이그레이션 테스트
│   ├── tools/                 SQLite 백업 가져오기 등 관리 도구
│   ├── Dockerfile             백엔드 컨테이너 이미지 정의
│   └── requirements.txt       Python 의존성
├── frontend/
│   ├── app/                   Next.js 경로, 레이아웃, 전역 스타일
│   ├── desk/                  워크스페이스 화면과 공통 메뉴
│   ├── features/              기능별 화면, 타입, API 요청, 스타일
│   ├── shared/                공통 API 클라이언트와 기본 스타일
│   ├── public/                직원 프로필 이미지 등 정적 파일
│   └── package.json           프런트엔드 의존성과 실행 스크립트
├── compose.yaml               백엔드, MySQL, Redis 로컬 실행 구성
├── AGENTS.md                  코드리뷰, 브랜치, 릴리스 노트 규칙
└── SETUP.md                   설치, 실행, 테스트, Git 명령
```

### 기능별 디렉터리

| 이름 | 담당 기능 |
| --- | --- |
| `org`, `plan`, `task` | 조직도 및 직원 프로필, 일정 화면, 업무 보드 |
| `auth`, `mypg`, `cv` | 인증·복구, 마이페이지, 개인 이력서 |
| `jobs`, `code` | 공고·모의면접, 코딩 테스트 풀이 |
| `talk`, `llm` | LemonTalk, 로컬 Ollama 호출 및 직원별 가상 예산 |
| `work`, `vlog` | Codex 개발 작업과 실행기, TechVlog 게시글·릴리스 노트 |

백엔드의 새 기능은 `app/modules/<기능>/`에 둡니다. API·요청 응답·처리 로직·DB 모델 파일은 각각 `<기능>_router.py`, `<기능>_schemas.py`, `<기능>_service.py`, `<기능>_model.py` 형식을 사용합니다. 파일과 함수의 역할은 docstring에, 모델 컬럼은 `comment=`에 적습니다. DB 변경은 Alembic 리비전으로 관리합니다.

프런트엔드에서는 `features/<기능>/`에서 관련 화면과 코드를 관리합니다. 기능명은 의미가 분명한 3~4글자를 우선하고, 스타일은 별도 CSS 파일 또는 CSS Modules에 Tailwind CSS와 함께 작성합니다.

## 데이터가 저장되는 곳

- **MySQL**은 Compose의 업무 DB입니다. 계정, 이력서, 면접 기록, 업무, 채팅방·멤버십, Codex 작업 및 첨부 이미지를 저장합니다. Uvicorn을 단독으로 실행하고 DB 연결을 설정하지 않으면 로컬 SQLite를 사용합니다.
- **Redis**는 LemonTalk 메시지와 읽음 상태를 보관합니다. 기본 Compose 설정은 디스크에 기록하지 않으며, 보관 한도와 만료 시간이 적용됩니다.
- **Ollama**는 면접과 LemonTalk의 응답을 생성합니다. 완료된 모의면접 기록은 업무 DB에서 조회합니다.
- **Codex**는 별도 실행기에서 승인된 업무를 처리합니다. 사이트의 가상 예산과 실제 제공자 청구는 별도로 관리됩니다.
