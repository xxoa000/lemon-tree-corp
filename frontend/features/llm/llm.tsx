import { type FormEvent, useEffect, useState } from 'react';

import { json, request } from '../../shared/api';

type Budget = {
  employee_id: string;
  name: string;
  salary: number;
  monthly_limit: number;
  used: number;
  month: string;
};

export function Budgets() {
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [selected, setSelected] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const allocated = budgets.reduce((sum, row) => sum + row.monthly_limit, 0);
  const budget = budgets.find((row) => row.employee_id === selected);

  useEffect(() => {
    let current = true;
    request<Budget[]>('llm/budgets')
      .then((rows) => {
        if (current) setBudgets(rows);
      })
      .catch((cause) => {
        if (current) setError(cause.message);
      });
    return () => {
      current = false;
    };
  }, []);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!budget) return;
    setError('');
    setSaved(false);
    setPending(true);
    const fields = new FormData(event.currentTarget);
    const values = {
      salary: Number(fields.get('salary')),
      monthly_limit: Number(fields.get('monthly_limit')),
    };
    try {
      await request(`llm/budgets/${budget.employee_id}`, json('PATCH', values));
      setBudgets(await request<Budget[]>('llm/budgets'));
      setSaved(true);
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setPending(false);
    }
  }

  return (
    <section aria-label="모의 LLM 예산">
      <p className="muted">가상 금액이며 실제 모델 API는 호출하지 않습니다.</p>
      {budgets.length > 0 && (
        <p>
          전체 월 배정액 · {allocated.toLocaleString('ko-KR')} / 50,000 가상 원
        </p>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {saved && <p role="status">모의 예산을 저장했습니다.</p>}
      <label>
        직원{' '}
        <select
          value={selected}
          disabled={pending}
          onChange={(event) => {
            setSelected(event.target.value);
            setSaved(false);
          }}
        >
          <option value="">직원 선택</option>
          {budgets.map((row) => (
            <option key={row.employee_id} value={row.employee_id}>
              {row.name}
            </option>
          ))}
        </select>
      </label>
      {budget && (
        <form className="login-form" key={budget.employee_id} onSubmit={save}>
          <p>
            {budget.month} 사용액 · {budget.used.toLocaleString('ko-KR')} 가상
            원
          </p>
          <label>
            가상 연봉(원)
            <input
              name="salary"
              type="number"
              required
              min={0}
              max={2000000000}
              defaultValue={budget.salary}
            />
          </label>
          <label>
            월간 모의 한도(원)
            <input
              name="monthly_limit"
              type="number"
              required
              min={0}
              max={2000000000}
              defaultValue={budget.monthly_limit}
            />
          </label>
          <button className="action" disabled={pending}>
            모의 예산 저장
          </button>
        </form>
      )}
    </section>
  );
}
