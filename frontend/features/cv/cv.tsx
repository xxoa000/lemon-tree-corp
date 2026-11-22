import { type FormEvent, useEffect, useState } from 'react';

import { json, request } from '../../shared/api';
import { ResumeSheet, resumeSections } from '../org/org';

const blank = {
  address: '',
  website: '',
  education: '',
  experience: '',
  certificates: '',
  awards: '',
  skills: '',
};
type Sections = typeof blank;
type Draft = { filename: string; content: string; sections: Sections | null };
const endpoint = 'accounts/me/resume';

export function ResumeManager({
  name,
  email,
  phone,
  avatar,
}: {
  name: string;
  email?: string;
  phone?: string;
  avatar?: string;
}) {
  const [draft, setDraft] = useState<Draft | null>(null);
  const [sections, setSections] = useState<Sections>(blank);
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
          setSections(data?.sections ?? blank);
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
          : json('PATCH', { content, sections }),
      );
      setDraft(data);
      setContent(data.content);
      if (!file) setSections(data.sections ?? blank);
      if (file) form.reset();
      setStatus(
        file
          ? '파일을 읽었습니다. 추출 텍스트에서 필요한 내용을 양식에 옮겨 주세요.'
          : '이력서를 저장했습니다.',
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
          <ResumeSheet
            name={name}
            portrait={avatar && <img src={avatar} alt="내 프로필 사진" />}
            contact={[
              email ?? '',
              phone ?? '',
              sections.address,
              sections.website,
            ]}
            sections={sections}
            skills={[
              ...new Set(
                sections.skills
                  .split(/[\n·]/)
                  .map((value) => value.trim())
                  .filter(Boolean),
              ),
            ]}
          />
          <details>
            <summary>이력서 내용 편집</summary>
            <form className="login-form" onSubmit={(event) => save(event)}>
              <p className="muted">
                이름·이메일·연락처는 회원정보를 사용합니다. 파일 없이 직접
                작성할 수 있습니다.
              </p>
              <label>
                주소
                <input
                  maxLength={240}
                  value={sections.address}
                  onChange={(event) =>
                    setSections({ ...sections, address: event.target.value })
                  }
                />
              </label>
              <label>
                홈페이지
                <input
                  maxLength={240}
                  value={sections.website}
                  onChange={(event) =>
                    setSections({ ...sections, website: event.target.value })
                  }
                />
              </label>
              {resumeSections.map(([key, label]) => (
                <label key={key}>
                  {label}
                  <textarea
                    value={sections[key]}
                    rows={3}
                    maxLength={key === 'experience' ? 6000 : 2000}
                    onChange={(event) =>
                      setSections({ ...sections, [key]: event.target.value })
                    }
                  />
                </label>
              ))}
              <label>
                업무 스킬 (한 줄씩)
                <textarea
                  value={sections.skills}
                  rows={3}
                  maxLength={2000}
                  onChange={(event) =>
                    setSections({ ...sections, skills: event.target.value })
                  }
                />
              </label>
              {draft?.filename && (
                <label>
                  원본에서 추출한 텍스트
                  <textarea
                    rows={7}
                    value={content}
                    maxLength={24000}
                    onChange={(event) => setContent(event.target.value)}
                  />
                </label>
              )}
              <button className="action" disabled={pending}>
                이력서 저장
              </button>
            </form>
          </details>
          <details>
            <summary>원본 파일 관리</summary>
            {draft?.filename && (
              <p>
                <a href="/api/v1/accounts/me/resume/file" download>
                  {draft.filename} 원본 다운로드
                </a>
              </p>
            )}
            <form
              className="login-form"
              onSubmit={(event) => save(event, true)}
            >
              <label>
                이력서 원본 (PDF·TXT, 최대 2MB)
                <input type="file" name="file" accept=".pdf,.txt" required />
              </label>
              <button className="action" disabled={pending}>
                {draft?.filename ? '파일 교체' : '이력서 업로드'}
              </button>
            </form>
          </details>
        </>
      )}
    </section>
  );
}
