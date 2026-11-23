import { type FormEvent, useEffect, useRef, useState } from 'react';

import { Avatar } from '../org/org';

import * as api from './talk-api';
import styles from './talk.module.css';

export function useTalk(account?: string) {
  const [snapshot, setSnapshot] = useState<{
    account: string;
    rooms: api.Room[];
  }>();
  const [live, setLive] = useState(false);

  useEffect(() => {
    if (!account?.startsWith('acct:')) return;
    const source = new EventSource('/api/v1/talk/events');
    const replace = (rooms: api.Room[]) => setSnapshot({ account, rooms });
    source.onmessage = (event) => {
      replace(JSON.parse(event.data) as api.Room[]);
      setLive(true);
    };
    source.onerror = () => setLive(false);
    return () => {
      source.close();
      setLive(false);
    };
  }, [account]);

  async function refresh() {
    if (account) setSnapshot({ account, rooms: await api.rooms() });
  }

  return {
    rooms: snapshot && snapshot.account === account ? snapshot.rooms : [],
    live,
    refresh,
  };
}

function ContactAvatar({ contact }: { contact: api.Contact }) {
  const [failedUrl, setFailedUrl] = useState<string>();
  if (contact.avatar_url && contact.avatar_url !== failedUrl) {
    const url = contact.avatar_url;
    return (
      <img
        className={styles.contactPhoto}
        src={url}
        alt=""
        onError={() => setFailedUrl(url)}
      />
    );
  }
  return (
    <Avatar employee={{ id: contact.employee_id ?? '', name: contact.name }} />
  );
}

function resizeMessage(field: HTMLTextAreaElement) {
  if (CSS.supports('field-sizing', 'content')) return;
  field.style.height = 'auto';
  field.style.height = `${field.scrollHeight + field.offsetHeight - field.clientHeight}px`;
}

export function Talk({
  rooms,
  live,
  refresh,
}: {
  rooms: api.Room[];
  live: boolean;
  refresh: () => Promise<void>;
}) {
  const [contacts, setContacts] = useState<api.Contact[]>([]);
  const [selected, setSelected] = useState<number>();
  const [detail, setDetail] = useState<{
    id: number;
    data: api.Conversation;
  }>();
  const [pending, setPending] = useState(false);
  const [sending, setSending] = useState(false);
  const messageField = useRef<HTMLTextAreaElement>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);
  const [contactId, setContactId] = useState('');
  const room = rooms.find((item) => item.id === selected);
  const roomId = room?.id;
  const latest = room?.latest;
  const earliest = room?.earliest ?? 0;
  const participants = room?.participants;
  const current = detail?.id === roomId ? detail?.data : undefined;

  useEffect(() => {
    api
      .contacts()
      .then(setContacts)
      .catch((cause) => setError(cause.message));
  }, []);

  useEffect(() => {
    if (!roomId) return;
    let active = true;

    async function load(id: number) {
      try {
        const data = await api.conversation(id);
        if (!active) return;
        setDetail((previous) => {
          if (previous?.id !== id || data.messages.length === 0)
            return { id, data };
          const oldest = data.messages[0].id;
          const old = previous.data.messages.filter(
            (message) => message.id < oldest && message.id >= earliest,
          );
          return {
            id,
            data: {
              ...data,
              messages: [...old, ...data.messages],
              has_more: old.length ? previous.data.has_more : data.has_more,
            },
          };
        });
      } catch (cause) {
        if (active) setError((cause as Error).message);
      }
    }

    void load(roomId);
    return () => {
      active = false;
    };
  }, [roomId, latest, earliest, participants, refreshKey]);

  const last = current?.messages.at(-1)?.id;
  const unread = room?.unread ?? 0;
  useEffect(() => {
    if (!roomId || !last || !unread) return;
    function mark() {
      if (!document.hidden && roomId && last) {
        void api
          .markRead(roomId, last)
          .catch((cause) => setError(cause.message));
      }
    }
    mark();
    document.addEventListener('visibilitychange', mark);
    return () => document.removeEventListener('visibilitychange', mark);
  }, [roomId, last, unread]);

  function choose(id: number) {
    setSelected(id);
    setContactId('');
    setNotice('');
    setError('');
  }

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

  function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    void run(async () => {
      const { id } = await api.createGroup(
        Object.fromEntries(new FormData(form)),
      );
      await refresh();
      choose(id);
      form.reset();
    });
  }

  function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const field = messageField.current;
    if (!room || pending || !field || !field.value.trim()) return;
    setNotice('');
    void run(async () => {
      setSending(true);
      try {
        const result = await api.sendMessage(room.id, field.value);
        field.value = '';
        resizeMessage(field);
        const notices: Record<string, string> = {
          ai_unavailable:
            '메시지는 전송됐습니다. Ollama 답장을 받지 못했습니다. 로컬 Ollama의 실행 상태를 확인해 주세요.',
          ai_busy: '메시지는 전송됐습니다. Ollama가 다른 답장을 처리 중입니다.',
          budget_exhausted:
            '메시지는 전송됐습니다. 이 직원의 답장에 필요한 남은 예산이 부족합니다.',
          disabled: '메시지는 전송됐습니다. 자동 답장은 꺼져 있습니다.',
          unavailable:
            '메시지는 전송됐습니다. 모의 답장을 저장하지 못했습니다.',
        };
        setNotice(notices[result.mock] ?? '');
        await refresh();
      } finally {
        setSending(false);
      }
    });
  }

  return (
    <>
      <h2 id="dialog-heading">LemonTalk</h2>
      <p className="muted" role="status">
        {live ? '실시간 연결됨' : '연결 중'}
      </p>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="muted">
          {notice}
        </p>
      )}
      <div className={styles.talk}>
        <aside className={styles.sidebar}>
          <h3>채팅</h3>
          {rooms.map((item) => (
            <button
              key={item.id}
              className={styles.room}
              aria-pressed={item.id === roomId}
              disabled={pending}
              onClick={() => choose(item.id)}
            >
              {item.name}
              {item.unread > 0 && <b>{item.unread}</b>}
            </button>
          ))}
          <details>
            <summary>연락처</summary>
            {contacts.map((contact) => (
              <button
                key={contact.id}
                className={`${styles.room} ${styles.contact}`}
                disabled={pending}
                onClick={() =>
                  void run(async () => {
                    const { id } = await api.openDm(contact.id);
                    await refresh();
                    choose(id);
                  })
                }
              >
                <ContactAvatar contact={contact} />
                <span>{contact.name}</span>
              </button>
            ))}
          </details>
          <details>
            <summary>팀 대화방 만들기</summary>
            <form onSubmit={create} className="login-form">
              <label>
                방 이름
                <input name="name" required maxLength={80} />
              </label>
              <label>
                팀
                <select name="team">
                  <option>디자인팀</option>
                  <option>개발팀</option>
                  <option>인프라팀</option>
                </select>
              </label>
              <button className="action" disabled={pending}>
                방 만들기
              </button>
            </form>
          </details>
        </aside>
        {room && current ? (
          <section className={styles.conversation} aria-label={room.name}>
            <h3>{room.name}</h3>
            {room.team && (
              <details>
                <summary>참여자 {current.members.length}명</summary>
                <ul>
                  {current.members.map((person) => (
                    <li key={person.id}>
                      {person.name}
                      {room.owner && person.id !== current.me && (
                        <button
                          disabled={pending}
                          onClick={() =>
                            void run(async () => {
                              await api.changeMember(room.id, person.id, true);
                              setRefreshKey((key) => key + 1);
                            })
                          }
                        >
                          내보내기
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
                {room.owner && (
                  <div className={styles.invite}>
                    <select
                      aria-label="초대할 연락처"
                      value={contactId}
                      onChange={(event) => setContactId(event.target.value)}
                    >
                      <option value="">연락처 선택</option>
                      {contacts
                        .filter(
                          (contact) =>
                            !current.members.some(
                              (member) => member.id === contact.id,
                            ),
                        )
                        .map((contact) => (
                          <option key={contact.id} value={contact.id}>
                            {contact.name}
                          </option>
                        ))}
                    </select>
                    <button
                      className="action"
                      disabled={pending || !contactId}
                      onClick={() =>
                        void run(async () => {
                          await api.changeMember(
                            room.id,
                            Number(contactId),
                            false,
                          );
                          setContactId('');
                          setRefreshKey((key) => key + 1);
                        })
                      }
                    >
                      초대
                    </button>
                  </div>
                )}
              </details>
            )}
            {current.has_more && (
              <button
                disabled={pending}
                onClick={() =>
                  void run(async () => {
                    const id = room.id;
                    const old = await api.conversation(
                      id,
                      current.messages[0]?.id,
                    );
                    setDetail((previous) =>
                      previous?.id === id
                        ? {
                            id,
                            data: {
                              ...previous.data,
                              messages: [
                                ...old.messages,
                                ...previous.data.messages,
                              ],
                              has_more: old.has_more,
                            },
                          }
                        : previous,
                    );
                  })
                }
              >
                이전 메시지
              </button>
            )}
            <ol className={styles.messages} aria-label="메시지" role="log">
              {current.messages.map((message) => (
                <li key={message.id} data-mine={message.sender === current.me}>
                  <small>
                    {message.name}
                    {message.ai
                      ? ' · Ollama AI'
                      : message.simulated
                        ? ' · 모의 응답'
                        : ''}
                    {' · '}
                    {new Date(message.sent_at).toLocaleTimeString('ko-KR', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </small>
                  <p>{message.body}</p>
                </li>
              ))}
            </ol>
            <form key={room.id} className={styles.send} onSubmit={send}>
              <textarea
                ref={messageField}
                name="body"
                aria-label="메시지"
                rows={1}
                required
                maxLength={3000}
                readOnly={sending}
                onInput={(event) => resizeMessage(event.currentTarget)}
              />
              <button className="action" disabled={pending}>
                {sending ? '보내는 중…' : '보내기'}
              </button>
            </form>
          </section>
        ) : (
          <p className="muted">대화방이나 연락처를 선택하세요.</p>
        )}
      </div>
    </>
  );
}
