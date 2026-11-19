import { type FormEvent, useEffect, useState } from 'react';

import {
  getProfile,
  getStaff,
  type Profile,
  saveProfile,
  uploadAvatar,
} from './mypg-api';
import { Budgets } from '../llm/llm';
import { ResumeManager } from '../cv/cv';
import styles from './mypg.module.css';

export function MyPage() {
  const [tab, setTab] = useState<'profile' | 'resume'>('profile');
  const [profile, setProfile] = useState<Profile>();
  const [avatarVersion, setAvatarVersion] = useState(0);
  const [budgetsOpen, setBudgetsOpen] = useState(false);
  const [staff, setStaff] = useState<Awaited<ReturnType<typeof getStaff>>>();
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const [pending, setPending] = useState(false);

  useEffect(() => {
    let active = true;
    getProfile()
      .then((data) => {
        if (active) setProfile(data);
      })
      .catch((cause) => {
        if (active) setError(cause.message);
      });
    return () => {
      active = false;
    };
  }, []);

  async function perform(action: () => Promise<void>) {
    setError('');
    setStatus('');
    setPending(true);
    try {
      await action();
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setPending(false);
    }
  }

  function submitProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    void perform(async () => {
      setProfile(await saveProfile(data));
      setStatus('회원정보를 저장했습니다.');
    });
  }

  function submitAvatar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    void perform(async () => {
      await uploadAvatar(data);
      setProfile((current) => current && { ...current, has_avatar: true });
      setAvatarVersion((current) => current + 1);
      form.reset();
      setStatus('프로필 사진을 저장했습니다.');
    });
  }

  return (
    <>
      <h2 id="dialog-heading">마이페이지</h2>
      <nav aria-label="마이페이지 메뉴" className={styles.tabs}>
        <button
          className="action"
          aria-pressed={tab === 'profile'}
          onClick={() => setTab('profile')}
        >
          회원정보
        </button>
        <button
          className="action"
          aria-pressed={tab === 'resume'}
          onClick={() => setTab('resume')}
        >
          이력서 관리
        </button>
      </nav>
      {tab === 'resume' && <ResumeManager />}
      <div hidden={tab !== 'profile'}>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        {status && <p role="status">{status}</p>}
        {profile ? (
          <>
            {profile.has_avatar && (
              <img
                className={styles.avatar}
                src={`/api/v1/accounts/me/avatar?v=${avatarVersion}`}
                alt="내 프로필 사진"
              />
            )}
            <p>
              아이디 <strong>{profile.username}</strong> ·{' '}
              {profile.role === 'admin' ? '관리자' : '사원'}
            </p>
            <form className="login-form" onSubmit={submitProfile}>
              <label>
                이름
                <input
                  name="display_name"
                  defaultValue={profile.display_name}
                  required
                  maxLength={80}
                />
              </label>
              <label>
                이메일
                <input
                  name="email"
                  type="email"
                  defaultValue={profile.email}
                  required
                  maxLength={254}
                />
              </label>
              <label>
                전화번호
                <input
                  name="phone"
                  type="tel"
                  defaultValue={profile.phone}
                  maxLength={32}
                />
              </label>
              <label>
                자기소개
                <textarea
                  className={styles.bio}
                  name="bio"
                  rows={3}
                  maxLength={1000}
                  defaultValue={profile.bio}
                />
              </label>
              <button className="action" disabled={pending}>
                회원정보 저장
              </button>
            </form>
            <form className={styles.photoForm} onSubmit={submitAvatar}>
              <label>
                프로필 사진 (JPEG, PNG, WebP · 최대 5MB)
                <input
                  name="image"
                  type="file"
                  required
                  accept="image/jpeg,image/png,image/webp"
                />
              </label>
              <button className="action" disabled={pending}>
                사진 저장
              </button>
            </form>
            {profile.role === 'admin' && (
              <section className={styles.staff}>
                <button
                  className="action"
                  aria-expanded={budgetsOpen}
                  onClick={() => setBudgetsOpen((current) => !current)}
                >
                  모의 LLM 예산
                </button>
                {budgetsOpen && <Budgets />}

                <button
                  className="action"
                  disabled={pending}
                  onClick={() =>
                    void perform(async () => {
                      setStaff(await getStaff());
                    })
                  }
                >
                  직원 계정 보기
                </button>
                {staff && (
                  <ul>
                    {staff.map((row) => (
                      <li key={row.employee_id}>
                        {row.display_name} · {row.employee_id} ·{' '}
                        {row.role === 'admin' ? '관리자' : '사원'} ·{' '}
                        {row.enabled ? '활성' : '비활성'}
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            )}
          </>
        ) : (
          !error && <p role="status">회원정보를 불러오는 중입니다.</p>
        )}
      </div>
    </>
  );
}
