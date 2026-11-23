import {
  type ClipboardEvent,
  type FormEvent,
  useEffect,
  useState,
} from 'react';

import { json, request } from '../../shared/api';
import styles from './work.module.css';

type Staff = { id: string; name: string; salary: number; remaining: number };
type Work = {
  id: number;
  employee_id: string;
  title: string;
  prompt: string;
  state: string;
  progress: string;
  summary: string;
  tokens: number | null;
  has_patch: boolean;
  images?: { position: number; name: string }[];
};
type Dashboard = { staff: Staff[]; jobs: Work[]; charge: number };
const endpoint = 'codex-work';
const money = new Intl.NumberFormat('ko-KR');
const imageTypes = ['image/png', 'image/jpeg', 'image/webp'];
const maxMiB = 1024 * 1024;

function PendingImage({ file }: { file: File }) {
  const [preview, setPreview] = useState('');
  useEffect(() => {
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  return preview ? <img src={preview} alt="" /> : null;
}

export function CodexWork() {
  const [dashboard, setDashboard] = useState<Dashboard>();
  const [employee, setEmployee] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [syncError, setSyncError] = useState('');
  const [attachmentError, setAttachmentError] = useState('');
  const [images, setImages] = useState<File[]>([]);
  const staff = dashboard?.staff.find((person) => person.id === employee);

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function refresh() {
      try {
        setDashboard(
          await request<Dashboard>(endpoint, { signal: controller.signal }),
        );
        setSyncError('');
      } catch (cause) {
        if (!controller.signal.aborted) setSyncError((cause as Error).message);
      } finally {
        if (!controller.signal.aborted) timer = setTimeout(refresh, 2500);
      }
    }
    void refresh();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, []);

  async function change(path: string, options: RequestInit) {
    setError('');
    setPending(true);
    try {
      const work = await request<Work>(path, options);
      setDashboard(
        (current) =>
          current && {
            ...current,
            jobs: [work, ...current.jobs.filter((job) => job.id !== work.id)],
          },
      );
      return true;
    } catch (cause) {
      setError((cause as Error).message);
      return false;
    } finally {
      setPending(false);
    }
  }

  function attach(files: File[]) {
    setAttachmentError('');
    if (!files.length || pending) return;
    const next = [...images, ...files];
    if (next.length > 4) {
      setAttachmentError('이미지는 최대 4장까지 첨부할 수 있습니다.');
    } else if (files.some((file) => !imageTypes.includes(file.type))) {
      setAttachmentError('PNG, JPEG 또는 WebP 이미지를 첨부해 주세요.');
    } else if (
      next.some((file) => file.size > 5 * maxMiB) ||
      next.reduce((total, file) => total + file.size, 0) > 8 * maxMiB
    ) {
      setAttachmentError(
        '이미지는 한 장당 5MB, 합계 8MB까지 첨부할 수 있습니다.',
      );
    } else {
      setImages(next);
    }
  }

  function paste(event: ClipboardEvent<HTMLFormElement>) {
    const clipboard = event.clipboardData;
    const files = Array.from(clipboard.files).filter((file) =>
      file.type.startsWith('image/'),
    );
    if (!files.length) {
      for (const item of clipboard.items) {
        if (!item.type.startsWith('image/')) continue;
        const file = item.getAsFile();
        if (file) files.push(file);
      }
    }
    if (!files.length) return;
    if (!event.clipboardData.getData('text/plain')) event.preventDefault();
    attach(files);
  }

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const body = new FormData(form);
    for (const file of images) body.append('images', file);
    if (
      await change(
        images.length ? endpoint + '/with-images' : endpoint,
        images.length
          ? { method: 'POST', body }
          : json('POST', Object.fromEntries(body)),
      )
    ) {
      form.reset();
      setEmployee('');
      setImages([]);
      setAttachmentError('');
    }
  }

  return (
    <section className={styles.panel} aria-labelledby="codex-work-heading">
      <h2 id="codex-work-heading">Codex 개발 작업</h2>
      <p>
        직원별로 요청을 등록하고 실행을 승인하세요. 서로 독립적인 작업은
        병행됩니다.
      </p>
      {(error || syncError) && (
        <p role="alert" className="error">
          {error || syncError}
        </p>
      )}
      {dashboard && (
        <>
          <form className={styles.form} onSubmit={create} onPaste={paste}>
            <label>
              담당 직원
              <select
                name="employee_id"
                value={employee}
                onChange={(event) => setEmployee(event.target.value)}
                required
              >
                <option value="">직원을 선택하세요</option>
                {dashboard.staff.map((person) => (
                  <option key={person.id} value={person.id}>
                    {person.name}
                  </option>
                ))}
              </select>
            </label>
            {staff && (
              <p>
                가상 연봉 {money.format(staff.salary)}원 · 이번 달 잔액{' '}
                {money.format(staff.remaining)}원
              </p>
            )}
            <label>
              제목
              <input name="title" required maxLength={120} />
            </label>
            <label>
              개발 요청
              <textarea name="prompt" required maxLength={6000} rows={4} />
            </label>
            <fieldset className={styles.attachments} disabled={pending}>
              <legend>참고 이미지</legend>
              <label>
                이미지 파일 선택
                <input
                  type="file"
                  multiple
                  accept={imageTypes.join(',')}
                  aria-describedby="work-image-help"
                  onChange={(event) => {
                    attach(Array.from(event.currentTarget.files ?? []));
                    event.currentTarget.value = '';
                  }}
                />
              </label>
              <p id="work-image-help" className="muted">
                개발 요청 입력란에서 이미지를 붙여넣을 수도 있어요. 최대 4장 ·
                장당 5MB · 합계 8MB
              </p>
              {attachmentError && (
                <p role="alert" className="error">
                  {attachmentError}
                </p>
              )}
              {images.length > 0 && (
                <ul className={styles.previews} aria-label="첨부할 이미지">
                  {images.map((file, index) => (
                    <li key={index}>
                      <PendingImage file={file} />
                      <span title={file.name}>{file.name}</span>
                      <button
                        type="button"
                        aria-label={`${file.name} 제거`}
                        onClick={() => {
                          setImages((current) =>
                            current.filter((_, position) => position !== index),
                          );
                          setAttachmentError('');
                        }}
                      >
                        제거
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </fieldset>
            <button type="submit" className="action" disabled={pending}>
              요청 등록
            </button>
          </form>
          <p className="muted">
            승인 시 작업당 가상 예산 {money.format(dashboard.charge)}원을
            예약합니다. 실제 API 요금은 별도로 청구될 수 있습니다.
          </p>
          {dashboard.jobs.length === 0 && <p>등록된 개발 요청이 없습니다.</p>}
          <ul className={styles.jobs}>
            {dashboard.jobs.map((job) => (
              <li key={job.id}>
                <div className={styles.heading}>
                  <strong>{job.title}</strong>
                  <span>
                    {dashboard.staff.find(
                      (person) => person.id === job.employee_id,
                    )?.name ?? job.employee_id}
                  </span>
                </div>
                <p>
                  {job.progress}
                  {job.tokens !== null &&
                    ` · 토큰 ${money.format(job.tokens)}개`}
                </p>
                <details>
                  <summary>개발 요청 보기</summary>
                  <p className={styles.text}>{job.prompt}</p>
                  {!!job.images?.length && (
                    <ul className={styles.previews} aria-label="첨부 이미지">
                      {job.images.map((image) => {
                        const url = `/api/v1/${endpoint}/${job.id}/images/${image.position}`;
                        return (
                          <li key={image.position}>
                            <a href={url} target="_blank" rel="noreferrer">
                              <img src={url} alt={image.name} loading="lazy" />
                              <span title={image.name}>{image.name}</span>
                            </a>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </details>
                {job.summary && <p className={styles.text}>{job.summary}</p>}
                {job.state === 'draft' && (
                  <button
                    className="action"
                    type="button"
                    disabled={pending}
                    onClick={() =>
                      void change(`${endpoint}/${job.id}/approve`, {
                        method: 'POST',
                      })
                    }
                  >
                    실행 승인
                  </button>
                )}
                {job.has_patch && (
                  <a
                    href={`/api/v1/${endpoint}/${job.id}/patch`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    변경된 코드 보기
                  </a>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
