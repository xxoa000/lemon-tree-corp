export function Plan({
  time,
  onTasks,
}: {
  time: Date | null;
  onTasks: () => void;
}) {
  return (
    <div className="schedule-grid">
      <section className="card">
        <h2>오늘의 일정</h2>
        <p className="muted">
          {time?.toLocaleDateString('ko-KR', { dateStyle: 'full' })}
        </p>
        <p>등록된 일정이 없습니다.</p>
      </section>
      <section className="card">
        <h2>진행 중인 프로젝트</h2>
        <details>
          <summary>LemonTree 워크스페이스</summary>
          <p>담당자 · 윤서진 과장</p>
          <p>다음 마감일 · 미정</p>
          <button className="action" onClick={onTasks}>
            업무 보기
          </button>
        </details>
      </section>
    </div>
  );
}
