import { type FormEvent, useState } from 'react';

import { findUsername, register, resetPassword } from './auth-api';

const labels = {
  login: '로그인',
  signup: '회원가입',
  find: '아이디 찾기',
  reset: '비밀번호 재설정',
} as const;
type Mode = keyof typeof labels;

export function Login({
  login,
  error,
  busy,
}: {
  login: (event: FormEvent<HTMLFormElement>) => void;
  error: string;
  busy: boolean;
}) {
  const [mode, setMode] = useState<Mode>('login');
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState('');
  const [result, setResult] = useState<{
    username?: string;
    recovery_code?: string;
  }>();
  const [showLoginError, setShowLoginError] = useState(true);

  function changeMode(next: Mode) {
    setMode(next);
    setResult(undefined);
    setFailure('');
    setShowLoginError(false);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    if (mode === 'login') {
      setShowLoginError(true);
      login(event);
      return;
    }
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    setPending(true);
    setFailure('');
    try {
      const action = {
        signup: register,
        find: findUsername,
        reset: resetPassword,
      }[mode];
      setResult(await action(data));
    } catch (cause) {
      setFailure((cause as Error).message);
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      <h2 id="dialog-heading">{labels[mode]}</h2>
      {result ? (
        <div role="status">
          {result.username ? (
            <p>
              회원님의 로그인 아이디는 <strong>{result.username}</strong>입니다.
            </p>
          ) : (
            <>
              <p>
                {mode === 'signup'
                  ? '가입이 완료되었습니다.'
                  : '새 비밀번호가 설정되었습니다.'}
              </p>
              <p>
                아래 복구 코드는 이 화면을 닫기 전에 안전한 곳에 보관하세요.
                아이디 찾기와 비밀번호 재설정에 필요합니다.
              </p>
              <p className="recovery-code">
                <code>{result.recovery_code}</code>
              </p>
            </>
          )}
          <button className="action" onClick={() => changeMode('login')}>
            로그인으로 돌아가기
          </button>
        </div>
      ) : (
        <>
          <form className="login-form" key={mode} onSubmit={submit}>
            {mode !== 'login' && (
              <label>
                가입 이메일
                <input
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  maxLength={254}
                />
              </label>
            )}
            {(mode === 'login' || mode === 'signup') && (
              <label>
                아이디
                <input
                  name="username"
                  autoComplete="username"
                  required
                  pattern={
                    mode === 'signup' ? '[A-Za-z0-9_.\\-]{3,40}' : undefined
                  }
                  maxLength={mode === 'signup' ? 40 : 128}
                />
                {mode === 'signup' && (
                  <small>영문, 숫자, 밑줄, 마침표, 하이픈으로 3~40자</small>
                )}
              </label>
            )}
            {(mode === 'find' || mode === 'reset') && (
              <label>
                복구 코드
                <input
                  name="recovery_code"
                  autoComplete="off"
                  required
                  minLength={20}
                  maxLength={100}
                />
              </label>
            )}
            {mode !== 'find' && (
              <label>
                {mode === 'reset' ? '새 비밀번호' : '비밀번호'}
                <input
                  name="password"
                  type="password"
                  autoComplete={
                    mode === 'login' ? 'current-password' : 'new-password'
                  }
                  required
                  minLength={mode === 'login' ? undefined : 10}
                  maxLength={256}
                />
                {mode !== 'login' && <small>10자 이상</small>}
              </label>
            )}
            {(mode === 'login' ? showLoginError && error : failure) && (
              <p role="alert" className="error">
                {mode === 'login' ? error : failure}
              </p>
            )}
            <button className="action" disabled={pending || busy}>
              {labels[mode]}
            </button>
          </form>
          <nav className="auth-links" aria-label="계정 메뉴">
            {(Object.keys(labels) as Mode[])
              .filter((next) => next !== mode)
              .map((next) => (
                <button
                  key={next}
                  type="button"
                  disabled={pending || busy}
                  onClick={() => changeMode(next)}
                >
                  {labels[next]}
                </button>
              ))}
          </nav>
        </>
      )}
    </>
  );
}
