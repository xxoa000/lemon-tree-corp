import { Person } from '../org/org';
import type { Employee } from '../org/org-api';
import { statuses, type Status, type Task } from './task-api';

export function Board({
  tasks,
  people,
  employeeId,
  mine,
  busy,
  onMine,
  onStatus,
  onSelect,
}: {
  tasks: Task[];
  people: Map<string, Employee>;
  employeeId?: string;
  mine: boolean;
  busy: boolean;
  onMine: (mine: boolean) => void;
  onStatus: (task: Task, status: Status) => void;
  onSelect: (employee: Employee) => void;
}) {
  return (
    <>
      <div className="board-toolbar">
        <p className="muted">
          {employeeId
            ? '본인 업무의 상태를 변경할 수 있습니다.'
            : '내 업무 상태를 변경하려면 로그인하세요.'}
        </p>
        {employeeId && (
          <label>
            <input
              type="checkbox"
              checked={mine}
              onChange={(event) => onMine(event.target.checked)}
            />{' '}
            내 업무만
          </label>
        )}
      </div>
      <div className="board">
        {(Object.keys(statuses) as Status[]).map((status) => {
          const column = tasks.filter(
            (task) =>
              task.status === status &&
              (!mine || task.assignee_id === employeeId),
          );
          return (
            <section className="column" key={status} data-status={status}>
              <h2>
                {statuses[status]} <span>{column.length}</span>
              </h2>
              {column.length === 0 && <p className="muted">업무 없음</p>}
              {column.map((task) => {
                const employee = people.get(task.assignee_id);
                return (
                  <article className="card ticket" key={task.id}>
                    <small>{task.id}</small>
                    <h3>{task.title}</h3>
                    <p>{task.description}</p>
                    {employee ? (
                      <Person employee={employee} onSelect={onSelect} />
                    ) : (
                      <p>미배정</p>
                    )}
                    {task.assignee_id === employeeId && (
                      <select
                        aria-label={task.title + ' 상태'}
                        disabled={busy}
                        value={task.status}
                        onChange={(event) =>
                          onStatus(task, event.target.value as Status)
                        }
                      >
                        {Object.entries(statuses).map(([value, label]) => (
                          <option key={value} value={value}>
                            {label}
                          </option>
                        ))}
                      </select>
                    )}
                  </article>
                );
              })}
            </section>
          );
        })}
      </div>
    </>
  );
}
