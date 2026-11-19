import { type FormEvent, useEffect, useState } from 'react';

import { json, request } from '../../shared/api';

type Draft = { filename: string; content: string };
const endpoint = 'accounts/me/resume';

export function ResumeManager() {
  const [draft, setDraft] = useState<Draft | null>(null);
  const [content, setContent] = useState('');
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    let current = true;
    request<Draft | null>(endpoint)
      .then((data) => {
        if (current) {
          setDraft(data);
          setContent(data?.content ?? '');
        }
      })
      .catch((cause) => {
        if (current) setError(cause.message);
      })
      .finally(() => {
        if (current) setLoading(false);
      });
    return () => {
      current = false;
    };
  }, []);

  async function save(event: FormEvent<HTMLFormElement>, file = false) {
    event.preventDefault();
    setPending(true);
    setError('');
    setStatus('');
    const form = event.currentTarget;
    try {
      const data = await request<Draft>(
        file ? endpoint + '/file' : endpoint,
        file
          ? { method: 'PUT', body: new FormData(form) }
          : json('PATCH', { content }),
      );
      setDraft(data);
      setContent(data.content);
      if (file) form.reset();
      setStatus(
        file
          ? '파일을 읽었습니다. 추출된 내용을 확인해 주세요.'
          : '편집본을 저장했습니다.',
      );
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setPending(false);
    }
  }

  return (
    <section aria-label="이력서 관리">
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {status && <p role="status">{status}</p>}
      {loading ? (
        <p>이력서를 불러오는 중입니다.</p>
      ) : (
        <>
          <form className="login-form" onSubmit={(event) => save(event, true)}>
            <label>
              이력서 원본 (PDF·TXT, 최대 2MB)
              <input type="file" name="file" accept=".pdf,.txt" required />
            </label>
            {draft && (
              <p className="muted">
                새 파일을 올리면 현재 원본과 편집본을 교체합니다.
              </p>
            )}
            <button className="action" disabled={pending}>
              {draft ? '파일 교체' : '이력서 업로드'}
            </button>
          </form>
          {draft && (
            <>
              <p>
                <a href="/api/v1/accounts/me/resume/file" download>
                  {draft.filename} 원본 다운로드
                </a>
              </p>
              <form className="login-form" onSubmit={(event) => save(event)}>
                <label>
                  이력서 편집본
                  <textarea
                    value={content}
                    onChange={(event) => setContent(event.target.value)}
                    rows={12}
                    maxLength={24000}
                    required
                  />
                </label>
                <button className="action" disabled={pending}>
                  편집본 저장
                </button>
              </form>
            </>
          )}
        </>
      )}
    </section>
  );
}
