const stats = [
  { label: 'LLM 호출', value: '47', icon: '🧠' },
  { label: '생성 파일', value: '8', icon: '📁' },
  { label: '코드 크기', value: '12.4 KB', icon: '📦' },
  { label: '소요 시간', value: '75분', icon: '⏱' },
  { label: 'Retry', value: '2', icon: '🔄' },
  { label: '알림 채널', value: 'Discord', icon: '🔔' },
]

export default function StatsBar() {
  return (
    <div className="mx-6 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      {stats.map(s => (
        <div key={s.label} className="bg-card rounded-xl border border-border p-3 text-center">
          <div className="text-xl">{s.icon}</div>
          <div className="text-lg font-bold text-white">{s.value}</div>
          <div className="text-xs text-inactive">{s.label}</div>
        </div>
      ))}
    </div>
  )
}
