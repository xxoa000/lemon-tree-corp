import { type FormEvent, useEffect, useState } from 'react';

import { json, request } from '../../shared/api';
import styles from './code.module.css';

const practice = {
  'sum-pairs': {
    title: '목표 합을 만드는 쌍',
    description:
      '정수 배열과 목표 합이 주어집니다. 서로 다른 위치의 두 수를 더해 목표 합이 되는 쌍의 개수를 구하세요. 순서는 구분하지 않습니다.',
    example: '배열 [1, 3, 2, 2], 목표 4 → 2',
  },
  'first-duplicate': {
    title: '처음으로 다시 나온 수',
    description:
      '정수 배열을 왼쪽부터 읽으며 두 번째로 등장하는 첫 번째 수를 반환하세요. 중복이 없으면 -1을 반환합니다.',
    example: '배열 [2, 7, 1, 7, 2] → 7',
  },
};
const providers = [
  ['프로그래머스', 'https://school.programmers.co.kr/learn/challenges'],
  ['백준', 'https://www.acmicpc.net/problemset'],
  ['LeetCode', 'https://leetcode.com/problemset/'],
  ['AtCoder', 'https://atcoder.jp/contests/'],
];
const hosts = new Set([
  'school.programmers.co.kr',
  'www.acmicpc.net',
  'leetcode.com',
  'atcoder.jp',
]);
const languages = ['python', 'javascript', 'java', 'cpp'] as const;
type Draft = { language: (typeof languages)[number]; code: string };

export function CodePractice({ signedIn }: { signedIn: boolean }) {
  const [problem, setProblem] = useState('sum-pairs');
  const [url, setUrl] = useState('');
  const [draft, setDraft] = useState<Draft>({ language: 'python', code: '' });
  const [saved, setSaved] = useState<string[]>([]);
  const [ready, setReady] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const local = practice[problem as keyof typeof practice];
  const path = 'practice/draft?problem=' + encodeURIComponent(problem);

  useEffect(() => {
    if (!signedIn) return;
    let current = true;
    request<string[]>('practice/drafts')
      .then((items) => {
        if (current) setSaved(items);
      })
      .catch((cause) => {
        if (current) setError(cause.message);
      });
    return () => {
      current = false;
    };
  }, [signedIn]);

  useEffect(() => {
    let current = true;
    setDraft({ language: 'python', code: '' });
    setReady(!signedIn);
    setStatus('');
    if (!signedIn) return;
    request<Draft | null>(path)
      .then((data) => {
        if (current) {
          if (data) setDraft(data);
          setReady(true);
        }
      })
      .catch((cause) => {
        if (current) setError(cause.message);
      });
    return () => {
      current = false;
    };
  }, [path, signedIn]);

  async function openProblem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const parsed = new URL(url);
      if (
        parsed.protocol !== 'https:' ||
        !hosts.has(parsed.hostname) ||
        parsed.username ||
        parsed.password ||
        (parsed.port && parsed.port !== '443')
      )
        throw new Error('지원하는 HTTPS 문제 주소를 입력해 주세요.');
      const next = parsed.origin + parsed.pathname.replace(/\/$/, '');
      if (next.length > 255) throw new Error('문제 주소가 너무 깁니다.');
      setError('');
      setProblem(next);
    } catch (cause) {
      setError((cause as Error).message);
    }
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError('');
    setStatus('');
    try {
      await request<Draft>(path, json('PUT', draft));
      setStatus('풀이를 저장했습니다.');
      setSaved(await request<string[]>('practice/drafts'));
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className={styles.practice}>
      <section className="card">
        <h2>연습 문제</h2>
        <nav aria-label="연습 문제">
          {Object.entries(practice).map(([key, item]) => (
            <button
              key={key}
              type="button"
              aria-pressed={problem === key}
              disabled={pending}
              onClick={() => {
                setError('');
                setProblem(key);
              }}
            >
              {item.title}
            </button>
          ))}
        </nav>
        <h3>외부 문제 사이트</h3>
        <ul>
          {providers.map(([name, target]) => (
            <li key={name}>
              <a href={target} target="_blank" rel="noreferrer">
                {name}
              </a>
            </li>
          ))}
        </ul>
        <form className="login-form" onSubmit={openProblem}>
          <label>
            외부 문제 주소
            <input
              type="url"
              value={url}
              maxLength={255}
              required
              onChange={(event) => setUrl(event.target.value)}
            />
          </label>
          <button className="action" disabled={pending}>
            문제 연결
          </button>
        </form>
        {saved.some((key) => key.startsWith('https://')) && (
          <>
            <h3>저장한 외부 문제</h3>
            <ul>
              {saved
                .filter((key) => key.startsWith('https://'))
                .map((key) => (
                  <li key={key}>
                    <button
                      disabled={pending}
                      onClick={() => {
                        setError('');
                        setProblem(key);
                      }}
                    >
                      {key}
                    </button>
                  </li>
                ))}
            </ul>
          </>
        )}
      </section>
      <section className="card">
        <h2>{local?.title ?? '외부 문제 풀이'}</h2>
        {local ? (
          <>
            <p>{local.description}</p>
            <p className="muted">{local.example}</p>
          </>
        ) : (
          <p>
            <a href={problem} target="_blank" rel="noreferrer">
              공식 문제 열기
            </a>
          </p>
        )}
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        {status && <p role="status">{status}</p>}
        <form className="login-form" onSubmit={save}>
          <label>
            언어
            <select
              value={draft.language}
              disabled={pending}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  language: event.target.value as Draft['language'],
                })
              }
            >
              {languages.map((language) => (
                <option key={language}>{language}</option>
              ))}
            </select>
          </label>
          <label>
            내 풀이
            <textarea
              className={styles.editor}
              value={draft.code}
              maxLength={15000}
              rows={14}
              spellCheck={false}
              disabled={!ready || pending}
              onChange={(event) =>
                setDraft({ ...draft, code: event.target.value })
              }
            />
          </label>
          <button className="action" disabled={!ready || !signedIn || pending}>
            풀이 저장
          </button>
        </form>
        {!signedIn && (
          <p className="muted">로그인하면 풀이를 계정에 저장할 수 있습니다.</p>
        )}
        <p className="muted">
          외부 문제 본문과 채점은 공식 사이트에서 이용할 수 있습니다.
        </p>
      </section>
    </div>
  );
}
