# LemonTree Corp — Phase 1 Scaffold

11-person fictional company: 10 AI employees + 1 human junior engineer. External manager: 백서윤 부장 (LT-SYS-001).

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
