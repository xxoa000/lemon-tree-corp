import type { FormEvent } from 'react';

export function Login({
  login,
  error,
  busy,
}: {
  login: (event: FormEvent<HTMLFormElement>) => void;
  error: string;
  busy: boolean;
}) {
  return (
    <>
      <h2 id="dialog-heading">로그인</h2>
      <form className="login-form" onSubmit={login}>
        <label>
          아이디
          <input
            name="username"
            autoComplete="username"
            required
            maxLength={128}
          />
        </label>
        <label>
          비밀번호
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            required
            maxLength={256}
          />
        </label>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <button className="action" disabled={busy}>
          로그인
        </button>
      </form>
    </>
  );
}
