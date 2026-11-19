import { type FormEvent, useEffect, useState } from 'react';

import {
  type Application,
  type Posting,
  answerQuestion,
  apply,
  getApplications,
  getPostings,
} from './jobs-api';
import styles from './jobs.module.css';

const stages: Record<string, string> = {
  screen_failed: '서류 불합격',
  technical: '1차 기술 면접',
  technical_failed: '기술 면접 불합격',
  behavioral: '2차 인성 면접',
  behavioral_failed: '인성 면접 불합격',
  hired: '최종 합격',
};

export function Jobs({
  employeeId,
  onLogin,
}: {
  employeeId?: string;
  onLogin: () => void;
}) {
  const [postings, setPostings] = useState<Posting[]>([]);
  const [role, setRole] = useState('backend');
  const [applications, setApplications] = useState<Application[]>([]);
  const [selected, setSelected] = useState<number>();
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);

  useEffect(() => {
    let current = true;
    getPostings()
      .then((row) => {
        if (current) setPostings(row);
      })
      .catch((cause) => {
        if (current) setError(cause.message);
      });
    if (employeeId) {
      getApplications()
        .then((rows) => {
          if (current) {
            setApplications((existing) => [
              ...existing,
              ...rows.filter(
                (row) => !existing.some((item) => item.id === row.id),
              ),
            ]);
          }
        })
        .catch((cause) => {
          if (current) setError(cause.message);
        });
    }
    return () => {
      current = false;
    };
  }, [employeeId]);

  const posting = postings.find((item) => item.role === role);
  const active =
    applications.find((row) => row.id === selected) ?? applications[0];

  async function submitApplication(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    setPending(true);
    setError('');
    try {
      const data = new FormData(form);
      data.set('role', role);
      const file = data.get('resume');
      if (file instanceof File && !file.name) data.delete('resume');
      const row = await apply(data);
      setApplications((current) => [row, ...current]);
      setSelected(row.id);
      form.reset();
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setPending(false);
    }
  }

  async function submitAnswer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!active?.question) return;
    const answer = String(
      new FormData(event.currentTarget).get('answer') ?? '',
    );
    setPending(true);
    setError('');
    try {
      const updated = await answerQuestion(
        active.id,
        active.question.id,
        answer,
      );
      setApplications((current) =>
        current.map((row) => (row.id === updated.id ? updated : row)),
      );
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className={styles.jobs}>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {postings.length > 0 && (
        <nav className={styles.roles} aria-label="채용 직무">
          {postings.map((item) => (
            <button
              type="button"
              className="action"
              key={item.role}
              disabled={pending}
              aria-pressed={item.role === role}
              onClick={() => setRole(item.role)}
            >
              {item.title}
            </button>
          ))}
        </nav>
      )}
      {posting ? (
        <section className="card">
          <p className="muted">{posting.team}</p>
          <h2>{posting.title}</h2>
          <ul>
            {posting.duties.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <p>{posting.format}</p>
          <p className="muted">
            텍스트 모의면접입니다. 직원 역할별 질문과 공개된 연습용 기준을
            사용합니다. 이력서 없이 연습을 시작할 수 있습니다.
          </p>
          <details>
            <summary>모의 전형 기준</summary>
            <p>
              이력서를 올리면 60자 이상의 본인 개발 경험을 확인합니다. 파일을
              생략하면 기술 면접부터 시작합니다. 기술 면접은 {posting.criteria}
              을 평가하고, 인성 면접은 협업·행동과 결과·마감 대응을 확인합니다.
            </p>
            <p>
              면접은 질문마다 25자 이상의 구체적인 답변을 평가합니다. 질문당 세
              항목 중 하나 이상, 전형당 총 4/6점 이상이면 통과합니다.
            </p>
          </details>
          {employeeId ? (
            <form
              key={role}
              className={styles.form}
              onSubmit={submitApplication}
            >
              <label>
                이력서 파일 (선택 · 텍스트 기반 PDF 또는 TXT, 최대 2MB)
                <input name="resume" type="file" accept=".pdf,.txt" />
              </label>
              <button className="action" disabled={pending}>
                모의면접 시작
              </button>
            </form>
          ) : (
            <button className="action" onClick={onLogin}>
              로그인 후 지원
            </button>
          )}
        </section>
      ) : (
        !error && <p role="status">공고를 불러오는 중입니다.</p>
      )}
      {employeeId && active && (
        <section className="card">
          <h2>내 지원 및 면접</h2>
          <label className={styles.history}>
            지원 내역
            <select
              value={active.id}
              disabled={pending}
              onChange={(event) => setSelected(Number(event.target.value))}
            >
              {applications.map((row) => (
                <option key={row.id} value={row.id}>
                  #{row.id} ·{' '}
                  {postings.find((item) => item.role === row.role)?.title ??
                    row.role}{' '}
                  · {row.filename || '이력서 없이 연습'} · {stages[row.stage]}
                </option>
              ))}
            </select>
          </label>
          <h3>{stages[active.stage]}</h3>
          <p role="status">{active.feedback}</p>
          {active.question && (
            <form
              className={styles.form}
              key={`${active.id}-${active.question.id}`}
              onSubmit={submitAnswer}
            >
              <strong>{active.question.interviewer}</strong>
              <p className={styles.prompt}>{active.question.prompt}</p>
              <label>
                면접 답변
                <textarea name="answer" rows={5} required maxLength={3000} />
              </label>
              <button className="action" disabled={pending}>
                답변 제출
              </button>
            </form>
          )}
        </section>
      )}
    </div>
  );
}
