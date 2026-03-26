import type { Task } from '../mocks/tasks'

const layerColors: Record<string, string> = {
  entity: 'bg-blue-600',
  repository: 'bg-purple-600',
  service: 'bg-emerald-600',
  controller: 'bg-amber-600',
  config: 'bg-gray-600',
  test: 'bg-cyan-600',
  infra: 'bg-rose-600',
}

const priorityColors: Record<string, string> = {
  high: 'bg-failed/80 text-white',
  medium: 'bg-running/80 text-black',
  low: 'bg-inactive/60 text-white',
}

const statusConfig: Record<string, { icon: string; color: string }> = {
  new: { icon: '📋', color: 'text-inactive' },
  in_progress: { icon: '🔨', color: 'text-running' },
  resolved: { icon: '✅', color: 'text-success' },
  qa_pass: { icon: '🏆', color: 'text-success' },
  qa_fail: { icon: '❌', color: 'text-failed' },
}

export default function TaskTable({ tasks }: { tasks: Task[] }) {
  const completed = tasks.filter(t => t.status === 'resolved' || t.status === 'qa_pass').length
  const pct = Math.round((completed / tasks.length) * 100)

  return (
    <div className="bg-card rounded-xl border border-border p-4 space-y-4">
      <h2 className="text-lg font-bold text-white">📋 Tasks</h2>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-inactive border-b border-border">
              <th className="py-2 px-2">ID</th>
              <th className="py-2 px-2">Title</th>
              <th className="py-2 px-2">Layer</th>
              <th className="py-2 px-2">Priority</th>
              <th className="py-2 px-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map(t => {
              const sc = statusConfig[t.status]
              return (
                <tr key={t.id} className="border-b border-border/50 hover:bg-card-hover transition-colors">
                  <td className="py-2.5 px-2 font-mono text-gray-300">{t.id}</td>
                  <td className="py-2.5 px-2 text-white">{t.title}</td>
                  <td className="py-2.5 px-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium text-white ${layerColors[t.layer]}`}>{t.layer}</span>
                  </td>
                  <td className="py-2.5 px-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${priorityColors[t.priority]}`}>{t.priority}</span>
                  </td>
                  <td className="py-2.5 px-2">
                    <span className={`${sc.color} font-medium`}>{sc.icon} {t.status.replace('_', ' ')}</span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-300">진행률</span>
          <span className="text-success font-bold">{completed}/{tasks.length} ({pct}%)</span>
        </div>
        <div className="w-full bg-bg-primary rounded-full h-3">
          <div className="bg-success h-3 rounded-full transition-all" style={{ width: `${pct}%` }} />
        </div>
      </div>

      {/* Dependencies */}
      <div className="space-y-1">
        <h3 className="text-sm font-medium text-gray-400">의존성 관계</h3>
        <div className="flex flex-wrap gap-2 text-xs">
          {tasks.filter(t => t.depends_on.length > 0).map(t => (
            <span key={t.id} className="bg-bg-primary px-2 py-1 rounded text-gray-400">
              {t.depends_on.join(', ')} → {t.id}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
