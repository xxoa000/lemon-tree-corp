import type { ReactNode } from 'react';
import type { Employee, Team } from './org-api';
import styles from './org.module.css';

export function Avatar({
  employee,
}: {
  employee: Pick<Employee, 'id' | 'name'>;
}) {
  const index =
    employee.id === 'LT-SYS-001' ? 11 : Number(employee.id.slice(3)) - 1;
  if (!Number.isInteger(index) || index < 0 || index > 11) {
    return (
      <span className={styles.avatar} aria-hidden="true">
        {employee.name.slice(-2)}
      </span>
    );
  }
  return (
    <span
      className={`${styles.avatar} ${styles.portrait}`}
      data-index={index}
      aria-hidden="true"
    />
  );
}

export function Person({
  employee,
  onSelect,
}: {
  employee: Employee;
  onSelect: (employee: Employee) => void;
}) {
  return (
    <button className={styles.person} onClick={() => onSelect(employee)}>
      <Avatar employee={employee} />
      <span>
        <strong>
          {employee.name} {employee.rank}
        </strong>
        <small>{employee.job_title}</small>
      </span>
    </button>
  );
}

export function Org({
  people,
  teams,
  manager,
  onSelect,
}: {
  people: Map<string, Employee>;
  teams: Team[];
  manager: Employee | null;
  onSelect: (employee: Employee) => void;
}) {
  const ceo = [...people.values()].find((person) => person.team === '경영진');
  return (
    <>
      {ceo && (
        <div className={styles.root}>
          <Person employee={ceo} onSelect={onSelect} />
        </div>
      )}
      <div className={styles.tree}>
        {teams.map((team) => (
          <section className={styles.branch} key={team.name}>
            <header className={styles.team}>
              <h2>{team.name}</h2>
              <span>{team.member_ids.length}명</span>
            </header>
            <ul className={styles.staff}>
              {team.member_ids.map((id) => {
                const person = people.get(id);
                if (!person) return null;
                return (
                  <li key={id}>
                    <Person employee={person} onSelect={onSelect} />
                    {id === team.leader_id && <small>팀장</small>}
                  </li>
                );
              })}
            </ul>
          </section>
        ))}
      </div>
      {manager && (
        <section className={`card ${styles.history}`}>
          <h2>외부 시스템 관리자</h2>
          <Person employee={manager} onSelect={onSelect} />
        </section>
      )}
      <section className={`card ${styles.history}`}>
        <h2>회사 연혁</h2>
        <p>
          <strong>Phase 1</strong> · 프로젝트 초기 구조 구성
        </p>
      </section>
    </>
  );
}

const contactFields = ['이메일', '연락처', '주소', '홈페이지'];
export const resumeSections = [
  ['education', '학력사항', '등록된 학력이 없습니다.'],
  ['experience', '경력사항', '등록된 프로젝트 경력이 없습니다.'],
  ['certificates', '자격증', '등록된 자격증이 없습니다.'],
  ['awards', '수상', '등록된 수상 이력이 없습니다.'],
] as const;

export function Profile({ profile }: { profile: Employee }) {
  return (
    <ResumeSheet
      name={profile.name}
      headingId="dialog-heading"
      role={`${profile.team} · ${profile.rank} · ${profile.job_title}`}
      portrait={<Avatar employee={profile} />}
      skills={profile.specialty
        .split('·')
        .map((skill) => skill.trim())
        .filter(Boolean)}
    />
  );
}

export function ResumeSheet({
  name,
  role,
  portrait,
  contact = [],
  sections,
  skills,
  headingId,
}: {
  name: string;
  role?: string;
  portrait?: ReactNode;
  contact?: string[];
  sections?: Partial<Record<(typeof resumeSections)[number][0], string>>;
  skills: string[];
  headingId?: string;
}) {
  return (
    <article className={styles.resume}>
      <p className={styles.resumeTitle} lang="en">
        RESUME
      </p>
      <header className={styles.resumeHeader}>
        <div className={styles.resumePortrait}>
          {portrait ?? (
            <span className={styles.initials} aria-hidden="true">
              {name.slice(-2)}
            </span>
          )}
        </div>
        <div className={styles.resumeIdentity}>
          <h2 id={headingId}>{name}</h2>
          {role && <p className={styles.resumeRole}>{role}</p>}
          <dl className={styles.resumeContacts}>
            {contactFields.map((field, index) => (
              <div key={field}>
                <dt>{field}</dt>
                <dd>
                  {contact[index] || (
                    <>
                      <span aria-hidden="true">—</span>
                      <span className="sr-only">등록된 정보 없음</span>
                    </>
                  )}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      </header>
      {resumeSections.map(([key, heading, message]) => (
        <section className={styles.resumeSection} key={heading}>
          <h3>{heading}</h3>
          <p
            className={
              sections?.[key] ? styles.resumeValue : styles.resumeEmpty
            }
          >
            {sections?.[key] || message}
          </p>
        </section>
      ))}
      <section className={styles.resumeSection}>
        <h3>업무 스킬</h3>
        {skills.length > 0 ? (
          <ul className={styles.resumeSkills}>
            {skills.map((skill) => (
              <li key={skill}>
                <span>{skill}</span>
                <span
                  className={styles.resumeSkillTrack}
                  title="숙련도 미등록"
                  aria-hidden="true"
                />
                <span className="sr-only">숙련도 미등록</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className={styles.resumeEmpty}>등록된 업무 스킬이 없습니다.</p>
        )}
      </section>
    </article>
  );
}
