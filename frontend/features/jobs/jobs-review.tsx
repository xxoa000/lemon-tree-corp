import { useEffect, useState } from 'react';

import { Avatar } from '../org/org';
import type { Employee } from '../org/org-api';

import {
  getApplications,
  getPostings,
  interviewHistory,
  stages,
  type Application,
  type Evaluation,
  type History,
  type Posting,
} from './jobs-api';
import styles from './jobs.module.css';

// Results store the question ID. The display uses the assigned interviewer for that slot.
const interviewers: Record<string, string> = {
  'tech-api': 'LT-004',
  'tech-db': 'LT-006',
  'cult-feedback': 'LT-003',
  'cult-deadline': 'LT-004',
  'front-ui': 'LT-005',
  'front-a11y': 'LT-005',
  'full-contract': 'LT-005',
  'full-write': 'LT-004',
  'ai-rag': 'LT-010',
  'ai-eval': 'LT-010',
};

type Tip = {
  from: number;
  to: number;
  kind: 'right' | 'wrong';
  message: string;
};

function getTips(answer: string, evaluation: Evaluation): Tip[] {
  const quotes = [
    ...evaluation.criteria.flatMap((item, index) =>
      item.met && item.evidence
        ? [
            {
              text: item.evidence,
              kind: 'right' as const,
              message: evaluation.labels[index],
            },
          ]
        : [],
    ),
    ...evaluation.corrections.map((item) => ({
      text: item.quote,
      kind: 'wrong' as const,
      message: item.correction,
    })),
  ];
  return quotes.flatMap(({ text, kind, message }) => {
    const from = text ? answer.indexOf(text) : -1;
    return from >= 0 ? [{ from, to: from + text.length, kind, message }] : [];
  });
}

function markedLine(answer: string, from: number, to: number, tips: Tip[]) {
  const boundaries = [
    ...new Set([
      from,
      to,
      ...tips.flatMap((tip) => [
        Math.max(from, tip.from),
        Math.min(to, tip.to),
      ]),
    ]),
  ].sort((a, b) => a - b);

  return boundaries.slice(0, -1).map((start, index) => {
    const end = boundaries[index + 1];
    const value = answer.slice(start, end);
    const covering = tips.filter((tip) => tip.from <= start && tip.to >= end);
    const kind = covering.some((tip) => tip.kind === 'wrong')
      ? 'wrong'
      : covering[0]?.kind;
    return kind ? (
      <mark className={styles[kind]} key={start}>
        {value}
      </mark>
    ) : (
      <span key={start}>{value}</span>
    );
  });
}

function AnnotatedAnswer({
  answer,
  evaluation,
}: {
  answer: string;
  evaluation: Evaluation;
}) {
  const tips = getTips(answer, evaluation);
  const lines: { from: number; to: number }[] = [];
  let from = 0;
  for (const separator of answer.matchAll(/\r?\n|(?<=[.!?。！？])[ \t]+/g)) {
    lines.push({ from, to: separator.index });
    from = separator.index + separator[0].length;
  }
  lines.push({ from, to: answer.length });

  return (
    <div className={styles.answerLines} aria-label="평가 표시가 있는 답변">
      {lines.map(({ from, to }) => {
        const covered = tips.filter((tip) => tip.from < to && tip.to > from);
        const inline = covered.filter((tip) => tip.from >= from);
        return (
          <div key={from}>
            <p className={styles.prompt}>
              {markedLine(answer, from, to, covered)}
            </p>
            {inline.length > 0 && (
              <ul className={styles.inlineTips}>
                {inline.map((tip, index) => (
                  <li key={index} data-kind={tip.kind}>
                    <strong>
                      {tip.kind === 'right' ? '잘한 점' : '수정할 점'}
                    </strong>
                    <span>{tip.message}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        );
      })}
    </div>
  );
}

export function AnswerReview({
  answer,
  evaluation,
  people,
}: {
  answer: string;
  evaluation: Evaluation | null;
  people: ReadonlyMap<string, Employee>;
}) {
  const assignment = evaluation
    ? interviewers[evaluation.question_id]
    : undefined;
  const interviewer = assignment ? people.get(assignment) : undefined;
  const assessments = [
    '기초 개념 보완 필요',
    '일부 기준 충족',
    '대부분의 기준 충족',
    '모든 기준 충족',
  ];
  return (
    <div className={styles.review}>
      {evaluation ? (
        <>
          <AnnotatedAnswer answer={answer} evaluation={evaluation} />
          <section className={styles.interviewer} aria-label="면접관 피드백">
            {interviewer && <Avatar employee={interviewer} />}
            <div className={styles.interviewerBody}>
              <header>
                <strong>
                  {interviewer
                    ? `${interviewer.name} ${interviewer.rank}`
                    : '담당 면접관'}
                </strong>
                {interviewer && <small>{interviewer.job_title}</small>}
              </header>
              <div className={styles.feedbackBubble}>
                <p>{evaluation.feedback}</p>
                <h4>이 답변에 대한 평가</h4>
                <p>
                  {assessments[evaluation.score] ?? '평가 결과'} ·{' '}
                  {evaluation.score}/3점
                </p>
                <ul>
                  {evaluation.criteria.map((item, index) => (
                    <li key={index}>
                      {item.met ? '충족' : '보완 필요'} ·{' '}
                      {evaluation.labels[index]}
                    </li>
                  ))}
                </ul>
                {evaluation.model_answer && (
                  <>
                    <h4>모범답변</h4>
                    <p className={styles.prompt}>{evaluation.model_answer}</p>
                  </>
                )}
              </div>
            </div>
          </section>
        </>
      ) : (
        <>
          <p className={styles.prompt}>{answer}</p>
          <p className="muted">
            이 답변에는 AI 평가 근거가 저장되어 있지 않습니다.
          </p>
        </>
      )}
    </div>
  );
}

export function InterviewRecords({
  people,
}: {
  people: ReadonlyMap<string, Employee>;
}) {
  const [applications, setApplications] = useState<Application[]>();
  const [postings, setPostings] = useState<Posting[]>([]);
  const [selected, setSelected] = useState<number>();
  const [detail, setDetail] = useState<History>();
  const [listError, setListError] = useState('');
  const [detailError, setDetailError] = useState('');
  const error = listError || detailError;
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    setListError('');
    getPostings()
      .then((roles) => {
        if (active) setPostings(roles);
      })
      .catch(() => {});
    getApplications()
      .then((rows) => {
        if (active) {
          setApplications(rows);
          setSelected((previous) =>
            rows.some((row) => row.id === previous) ? previous : rows[0]?.id,
          );
        }
      })
      .catch((cause) => {
        if (active) setListError(cause.message);
      });
    return () => {
      active = false;
    };
  }, [reload]);

  useEffect(() => {
    if (!selected) return;
    let active = true;
    setDetail(undefined);
    setDetailError('');
    interviewHistory(selected)
      .then((data) => {
        if (active) setDetail(data);
      })
      .catch((cause) => {
        if (active) setDetailError(cause.message);
      });
    return () => {
      active = false;
    };
  }, [selected, reload]);

  return (
    <section aria-label="내 모의면접 기록">
      {error && (
        <div role="alert">
          <p className="error">{error}</p>
          <button
            type="button"
            className="action"
            onClick={() => setReload((value) => value + 1)}
          >
            기록 다시 불러오기
          </button>
        </div>
      )}
      {!applications && !error && (
        <p role="status">면접 기록을 불러오는 중입니다.</p>
      )}
      {applications?.length === 0 && <p>아직 진행한 모의면접이 없습니다.</p>}
      {applications && applications.length > 0 && (
        <label>
          면접 선택{' '}
          <select
            value={selected}
            onChange={(event) => setSelected(Number(event.target.value))}
          >
            {applications.map((row) => (
              <option value={row.id} key={row.id}>
                #{row.id} ·{' '}
                {postings.find((role) => role.role === row.role)?.title ??
                  row.role}{' '}
                · {stages[row.stage] ?? row.stage} ·{' '}
                {row.created_at.slice(0, 10)}
              </option>
            ))}
          </select>
        </label>
      )}
      {selected && !detail && !error && (
        <p role="status">선택한 면접을 불러오는 중입니다.</p>
      )}
      {detail?.application.id === selected && detail && (
        <>
          <h3>{stages[detail.application.stage]}</h3>
          <p>{detail.application.feedback}</p>
          {detail.application.question && (
            <details>
              <summary>저장된 미응답 질문</summary>
              <p className={styles.prompt}>
                {detail.application.question.prompt}
              </p>
            </details>
          )}
          {detail.answers.length === 0 && <p>제출한 답변이 없습니다.</p>}
          {detail.answers.map((row) => (
            <details key={row.question_id}>
              <summary>
                {row.prompt} · {row.score}/3점
              </summary>
              {row.original_question_saved === false && (
                <p className="muted">
                  저장된 원문이 없어 기본 문항 또는 문항 ID를 표시합니다.
                </p>
              )}
              <AnswerReview
                answer={row.answer}
                evaluation={row.evaluation}
                people={people}
              />
            </details>
          ))}
        </>
      )}
    </section>
  );
}
