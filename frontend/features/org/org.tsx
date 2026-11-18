import type { Employee, Team } from './org-api';
import careers from './careers.json';
import styles from './org.module.css';

const careerHistory: Record<string, string[]> = careers;

function Avatar({ employee }: { employee: Employee }) {
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
        <section className={styles.hero}>
          <div>
            <p className={styles.eyebrow}>조직도</p>
            <h2>LemonTree Corp</h2>
            <p>디자인 · 개발 · 인프라</p>
          </div>
          <Person employee={ceo} onSelect={onSelect} />
        </section>
      )}
      <div className={styles['team-grid']}>
        {teams.map((team) => (
          <section className="card" key={team.name}>
            <h2>{team.name}</h2>
            <p className="muted">구성원 {team.member_ids.length}명</p>
            {team.member_ids.map((id) => {
              const person = people.get(id);
              return (
                person && (
                  <Person key={id} employee={person} onSelect={onSelect} />
                )
              );
            })}
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

export function Profile({ profile }: { profile: Employee }) {
  return (
    <>
      <Avatar employee={profile} />
      <h2 id="dialog-heading">
        {profile.name} {profile.rank}
      </h2>
      <p>
        {profile.team} · {profile.job_title}
      </p>
      <p>{profile.specialty}</p>
      <h3>주요 이력</h3>
      {careerHistory[profile.id] ? (
        <ol>
          {careerHistory[profile.id].map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ol>
      ) : (
        <p>등록된 이력이 없습니다.</p>
      )}
    </>
  );
}
