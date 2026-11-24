'use client';

import Link from 'next/link';
import { type FormEvent, useEffect, useState } from 'react';

import { RequestError } from '../../shared/api';
import { Login } from '../auth/auth';
import {
  createSession,
  deleteSession,
  getSession,
  type Session,
} from '../auth/auth-api';
import { getEmployees, type Employee } from '../org/org-api';
import { MyPage } from './mypg';
import styles from './mypg.module.css';

export function MyPageScreen() {
  const [session, setSession] = useState<Session | null>();
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [error, setError] = useState('');
  const [sessionError, setSessionError] = useState('');
  const [busy, setBusy] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    getSession()
      .then((data) => {
        if (active) setSession(data);
      })
      .catch((cause: unknown) => {
        if (!active) return;
        if (cause instanceof RequestError && cause.status === 401) {
          setSession(null);
        } else {
          setSessionError(
            '로그인 상태를 확인할 수 없습니다. 잠시 뒤 다시 시도해 주세요.',
          );
        }
      });
    return () => {
      active = false;
    };
  }, [attempt]);

  useEffect(() => {
    if (!session) return;
    let active = true;
    getEmployees()
      .then((data) => {
        if (active) setEmployees(data);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [session]);

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const credentials = Object.fromEntries(new FormData(event.currentTarget));
    setError('');
    setBusy(true);
    try {
      setSession(await createSession(credentials));
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    setError('');
    setBusy(true);
    try {
      await deleteSession();
      setSession(null);
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={styles.screen}>
      <header className={styles.screenHeader}>
        <Link href="/" className={styles.workspaceLink}>
          ← 워크스페이스
        </Link>
        {session && (
          <button
            type="button"
            className="action"
            disabled={busy}
            onClick={logout}
          >
            로그아웃
          </button>
        )}
      </header>
      <main className={styles.screenMain}>
        <h1>마이페이지</h1>
        {sessionError ? (
          <>
            <p role="alert" className="error">
              {sessionError}
            </p>
            <button
              className="action"
              type="button"
              onClick={() => {
                setSessionError('');
                setAttempt((current) => current + 1);
              }}
            >
              다시 시도
            </button>
          </>
        ) : session === undefined ? (
          <p role="status">로그인 상태를 확인하는 중입니다.</p>
        ) : session ? (
          <>
            {error && (
              <p role="alert" className="error">
                {error}
              </p>
            )}
            <MyPage
              key={session.employee_id}
              people={new Map(employees.map((person) => [person.id, person]))}
              hasAccount={session.employee_id.startsWith('acct:')}
            />
          </>
        ) : (
          <section className={styles.signIn} aria-label="마이페이지 로그인">
            <p>회원정보와 모의면접 기록을 확인하려면 로그인해 주세요.</p>
            <Login login={login} error={error} busy={busy} />
          </section>
        )}
      </main>
    </div>
  );
}
