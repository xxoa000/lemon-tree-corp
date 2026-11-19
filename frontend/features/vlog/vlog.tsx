import { type FormEvent, useEffect, useState } from 'react';
import Markdown from 'react-markdown';

import type { Session } from '../auth/auth-api';
import { json, request } from '../../shared/api';
import styles from './vlog.module.css';

type Article = {
  id: string;
  author_id: number | null;
  author: string;
  title: string;
  body: string;
  created_at: string;
};

export function Vlog({ session }: { session: Session | null }) {
  const [posts, setPosts] = useState<Article[]>([]);
  const [selected, setSelected] = useState<string>();
  const [editing, setEditing] = useState<Article | 'new'>();
  const [pending, setPending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const account = session?.employee_id.startsWith('acct:')
    ? Number(session.employee_id.slice(5))
    : undefined;
  const post = posts.find((entry) => entry.id === selected) ?? posts[0];
  const canEdit =
    post &&
    account !== undefined &&
    post.author_id !== null &&
    (post.author_id === account || session?.role === 'admin');

  useEffect(() => {
    let current = true;
    request<Article[]>('vlog')
      .then((entries) => {
        if (current) setPosts(entries);
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

  async function run(action: () => Promise<void>) {
    setPending(true);
    setError('');
    try {
      await action();
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setPending(false);
    }
  }

  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editing) return;
    const data = Object.fromEntries(new FormData(event.currentTarget));
    void run(async () => {
      const saved = await request<Article>(
        editing === 'new' ? 'vlog' : 'vlog/' + editing.id,
        json(editing === 'new' ? 'POST' : 'PATCH', data),
      );
      setPosts((current) =>
        editing === 'new'
          ? [saved, ...current]
          : current.map((entry) => (entry.id === saved.id ? saved : entry)),
      );
      setSelected(saved.id);
      setEditing(undefined);
    });
  }

  return (
    <div className={styles.vlog}>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <div className={styles.columns}>
        <aside className="card">
          {account !== undefined && (
            <button
              className="action"
              disabled={loading || pending}
              onClick={() => setEditing('new')}
            >
              새 글 작성
            </button>
          )}
          <nav aria-label="TechVlog 게시글">
            {posts.map((entry) => (
              <button
                type="button"
                key={entry.id}
                className={styles.entry}
                aria-current={
                  entry.id === post?.id && !editing ? 'page' : undefined
                }
                onClick={() => {
                  setSelected(entry.id);
                  setEditing(undefined);
                }}
              >
                {entry.title}
                <small>
                  {entry.created_at.slice(0, 10)} · {entry.author}
                </small>
              </button>
            ))}
          </nav>
        </aside>
        <section className="card">
          {editing ? (
            <form
              className="login-form"
              onSubmit={save}
              key={editing === 'new' ? 'new' : editing.id}
            >
              <label>
                제목
                <input
                  name="title"
                  required
                  maxLength={120}
                  defaultValue={editing === 'new' ? '' : editing.title}
                />
              </label>
              <label>
                본문 (Markdown)
                <textarea
                  name="body"
                  rows={12}
                  maxLength={12000}
                  required
                  defaultValue={editing === 'new' ? '' : editing.body}
                />
              </label>
              <div className={styles.actions}>
                <button className="action" disabled={pending}>
                  게시글 저장
                </button>
                <button
                  type="button"
                  disabled={pending}
                  onClick={() => setEditing(undefined)}
                >
                  취소
                </button>
              </div>
            </form>
          ) : post ? (
            <article className={styles.article}>
              <h2>{post.title}</h2>
              <p className="muted">
                {post.author} · {post.created_at.slice(0, 10)}
              </p>
              <Markdown skipHtml disallowedElements={['img']}>
                {post.body}
              </Markdown>
              {canEdit && (
                <div className={styles.actions}>
                  <button
                    className="action"
                    disabled={pending}
                    onClick={() => setEditing(post)}
                  >
                    수정
                  </button>
                  <button
                    disabled={pending}
                    onClick={() => {
                      if (window.confirm('이 게시글을 삭제할까요?')) {
                        void run(async () => {
                          await request('vlog/' + post.id, {
                            method: 'DELETE',
                          });
                          setPosts((current) =>
                            current.filter((entry) => entry.id !== post.id),
                          );
                          setSelected(undefined);
                        });
                      }
                    }}
                  >
                    삭제
                  </button>
                </div>
              )}
            </article>
          ) : (
            <p>
              {loading
                ? '게시글을 불러오는 중입니다.'
                : '등록된 게시글이 없습니다.'}
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
