'use client';

import { type FormEvent, useEffect, useState } from 'react';
import { Login } from '../features/auth/auth';
import {
  createSession,
  deleteSession,
  getSession,
  type Session,
} from '../features/auth/auth-api';
import { CodePractice } from '../features/code/code';
import { MyPage } from '../features/mypg/mypg';
import { Jobs } from '../features/jobs/jobs';
import { Org, Profile } from '../features/org/org';
import {
  getEmployees,
  getManager,
  getTeams,
  type Employee,
  type Team,
} from '../features/org/org-api';
import { Talk, useTalk } from '../features/talk/talk';
import { Vlog } from '../features/vlog/vlog';
import { Plan } from '../features/plan/plan';
import { Board } from '../features/task/task';
import {
  getTasks,
  updateTask,
  type Status,
  type Task,
} from '../features/task/task-api';

const sections = ['회사', '일정', '업무', '공고', 'TechVlog'] as const;
type Section = (typeof sections)[number] | '코딩 테스트';
const symbols = { 회사: '▦', 일정: '◫', 업무: '☷', 공고: '◇', TechVlog: '✎' };

export default function Workspace() {
  const [section, setSection] = useState<Section>('회사');
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [manager, setManager] = useState<Employee | null>(null);
  const [teams, setTeams] = useState<Team[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [session, setSession] = useState<Session | null>(null);
  const [profile, setProfile] = useState<Employee | null>(null);
  const [talkOpen, setTalkOpen] = useState(false);
  const talk = useTalk(session?.employee_id);
  const unread = talk.rooms.reduce((sum, room) => sum + room.unread, 0);
  const [myPageOpen, setMyPageOpen] = useState(false);
  const [loginOpen, setLoginOpen] = useState(false);
  const [startOpen, setStartOpen] = useState(false);
  const [mine, setMine] = useState(false);
  const [time, setTime] = useState<Date | null>(null);
  const [dataError, setDataError] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const tick = () => setTime(new Date());
    tick();
    const timer = window.setInterval(tick, 1000);
    Promise.all([getEmployees(), getTeams(), getTasks()])
      .then(([people, groups, work]) => {
        setEmployees(people);
        setTeams(groups);
        setTasks(work);
      })
      .catch((error) => setDataError(error.message))
      .finally(() => setLoading(false));
    getManager()
      .then((person) =>
        setManager({
          ...person,
          team: '외부 관리자',
          specialty: '조직 설계 · 업무 프로세스 · 시스템 운영',
        }),
      )
      .catch(() => {});
    getSession()
      .then(setSession)
      .catch(() => {});
    return () => window.clearInterval(timer);
  }, []);

  const people = new Map(employees.map((person) => [person.id, person]));

  function go(target: Section, onlyMine = false) {
    setSection(target);
    setMine(onlyMine);
    setProfile(null);
    setLoginOpen(false);
    setMyPageOpen(false);
    setTalkOpen(false);
    setStartOpen(false);
    setError('');
  }

  function openTalk() {
    setStartOpen(false);
    setProfile(null);
    setMyPageOpen(false);
    setError('');
    if (session?.employee_id.startsWith('acct:')) setTalkOpen(true);
    else setLoginOpen(true);
  }

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError('');
    try {
      setSession(await createSession(Object.fromEntries(form)));
      setLoginOpen(false);
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    setError('');
    try {
      await deleteSession();
      setSession(null);
      setMyPageOpen(false);
      setTalkOpen(false);
      setMine(false);
      setProfile(null);
    } catch (error) {
      setError((error as Error).message);
    }
  }

  async function changeStatus(task: Task, status: Status) {
    setBusy(true);
    setError('');
    try {
      const updated = await updateTask(task, status);
      setTasks((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="workspace">
      <aside className="sidebar">
        <button className="brand" onClick={() => go('회사')}>
          <span className="brand-mark" aria-hidden="true" />
          <span>
            LemonTree<small>Corp</small>
          </span>
        </button>
        <nav aria-label="주요 메뉴">
          {sections.map((item) => (
            <button
              key={item}
              aria-current={section === item ? 'page' : undefined}
              className={section === item ? 'selected' : ''}
              onClick={() => go(item)}
            >
              <span aria-hidden="true">{symbols[item]}</span>
              {item}
            </button>
          ))}
        </nav>
      </aside>
      <main>
        <header className="topbar">
          <span>
            워크스페이스 <span className="slash">/</span> {section}
          </span>
          <div className="account">
            <button
              className="talk"
              type="button"
              aria-label={
                unread ? `LemonTalk, 읽지 않은 메시지 ${unread}개` : 'LemonTalk'
              }
              onClick={openTalk}
            >
              <span className="brand-mark" aria-hidden="true" />
              {unread > 0 && (
                <span className="talk-unread" aria-hidden="true">
                  {unread > 99 ? '99+' : unread}
                </span>
              )}
            </button>
            {session ? (
              <>
                {session.employee_id.startsWith('acct:') ? (
                  <button onClick={() => setMyPageOpen(true)}>
                    마이페이지
                  </button>
                ) : (
                  people.has(session.employee_id) && (
                    <button
                      onClick={() => {
                        const person = people.get(session.employee_id);
                        if (person) setProfile(person);
                      }}
                    >
                      마이페이지
                    </button>
                  )
                )}
                <button onClick={logout}>로그아웃</button>
              </>
            ) : (
              <button
                onClick={() => {
                  setProfile(null);
                  setError('');
                  setLoginOpen(true);
                }}
              >
                로그인
              </button>
            )}
          </div>
        </header>
        <div className="content">
          <h1>{section}</h1>
          {dataError && (
            <p role="alert" className="error">
              {dataError}
            </p>
          )}
          {error && !loginOpen && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          {loading && <p role="status">워크스페이스를 불러오는 중입니다.</p>}
          {!loading && section === '회사' && (
            <Org
              people={people}
              teams={teams}
              manager={manager}
              onSelect={setProfile}
            />
          )}
          {!loading && section === '일정' && (
            <Plan time={time} onTasks={() => go('업무')} />
          )}
          {!loading && section === '업무' && (
            <Board
              tasks={tasks}
              people={people}
              employeeId={session?.org_employee_id ?? undefined}
              mine={mine}
              busy={busy}
              onMine={setMine}
              onStatus={changeStatus}
              onSelect={setProfile}
            />
          )}
          {section === '코딩 테스트' && (
            <CodePractice
              key={session?.employee_id ?? 'guest'}
              signedIn={Boolean(session?.employee_id.startsWith('acct:'))}
            />
          )}
          {section === 'TechVlog' && <Vlog session={session} />}
          {section === '공고' && (
            <Jobs
              people={people}
              key={session?.employee_id ?? 'guest'}
              employeeId={session?.employee_id}
              onLogin={() => {
                setError('');
                setLoginOpen(true);
              }}
            />
          )}
        </div>
      </main>
      <footer className="taskbar">
        <button
          className="start"
          aria-expanded={startOpen}
          onClick={() => setStartOpen(!startOpen)}
        >
          <span className="brand-mark" /> 시작
        </button>
        {startOpen && (
          <nav className="launcher" aria-label="시작 메뉴">
            <button onClick={() => go('일정')}>오늘 일정</button>
            <button
              onClick={() => {
                go('업무', Boolean(session));
                if (!session) setLoginOpen(true);
              }}
            >
              내 업무
            </button>
            <button onClick={openTalk}>LemonTalk</button>
            <button onClick={() => go('코딩 테스트')}>코딩 테스트</button>
          </nav>
        )}
        <time>
          {time?.toLocaleTimeString('ko-KR', {
            hour: 'numeric',
            minute: '2-digit',
          })}
        </time>
      </footer>
      {(profile || loginOpen || myPageOpen || talkOpen) && (
        <dialog
          className={
            talkOpen ? 'talk-dialog' : profile ? 'resume-dialog' : undefined
          }
          ref={(element) => {
            if (element && !element.open) element.showModal();
          }}
          onClose={() => {
            setTalkOpen(false);
            setMyPageOpen(false);
            setProfile(null);
            setLoginOpen(false);
          }}
          aria-labelledby="dialog-heading"
        >
          <form method="dialog" className="close-form">
            <button aria-label="닫기">×</button>
          </form>
          {loginOpen ? (
            <Login login={login} error={error} busy={busy} />
          ) : talkOpen ? (
            <Talk {...talk} />
          ) : myPageOpen ? (
            <MyPage people={people} />
          ) : (
            profile && <Profile profile={profile} />
          )}
        </dialog>
      )}
    </div>
  );
}
