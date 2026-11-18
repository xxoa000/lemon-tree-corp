const teams = [
  { name: '디자인팀', people: ['윤서진 과장 · PM / 팀장', '최나린 과장 · UI/UX'] },
  { name: '개발팀', people: ['강도윤 기술이사 · CTO / 팀장', '이준혁 과장 · Backend', '한유리 대리 · Frontend', '박현우 부장 · Database', '서지안 대리 · AI / LLM', '사용자 사원 · Junior Backend'] },
  { name: '인프라팀', people: ['정하은 차장 · QA / 팀장', '오태민 과장 · DevOps / Kubernetes'] },
];
export default function Home() {
  return <main style={{ maxWidth: 1050, margin: 'auto', padding: 32 }}>
    <header style={{ borderBottom: '1px solid #cad5ca', paddingBottom: 20 }}><h1>LemonTree Corp</h1><p>AI 스타트업 협업 플랫폼 · Phase 1 프로토타입</p></header>
    <section style={{ background: '#e5f0d8', borderRadius: 16, padding: 20, marginTop: 24 }}><h2>차민석 대표이사</h2><p>CEO · 경영 전략 / 사업 운영 / 의사결정</p></section>
    <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(250px,1fr))', gap: 16, marginTop: 20 }}>
      {teams.map(team => <article key={team.name} style={{ background: 'white', border: '1px solid #dbe3d8', borderRadius: 16, padding: 20 }}><h2>{team.name}</h2>{team.people.map(person => <p key={person}>{person}</p>)}</article>)}
    </section>
    <section style={{ background: '#fff5d2', borderRadius: 16, padding: 20, marginTop: 24 }}><h2>LemonTree Control Center</h2><p>백서윤 부장 · AI Organization Manager</p><p>회사 외부 관리자. “백서윤 부장님” 호출은 소유자의 설계 요청으로 분류한다.</p><small>현재는 UI 및 설정 스캐폴드. 실제 AI 실행과 변경 승인은 미구현.</small></section>
  </main>;
}
