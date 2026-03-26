import type { AgentConfigType } from '../mocks/agents'

export default function AgentConfig({ agents, currentAgent }: { agents: AgentConfigType[]; currentAgent: string | null }) {
  return (
    <div className="bg-card rounded-xl border border-border p-4 space-y-3">
      <h2 className="text-lg font-bold text-white">⚙️ Agent 설정</h2>
      <div className="grid grid-cols-2 gap-3">
        {agents.map(a => {
          const isActive = a.id === currentAgent
          return (
            <div
              key={a.id}
              className={`p-3 rounded-lg border-2 transition-all ${
                isActive ? 'border-running bg-running/10 shadow-lg shadow-running/20' : 'border-border bg-bg-primary'
              }`}
            >
              <div className="flex items-center gap-2 mb-2">
                <span className={`w-2 h-2 rounded-full ${isActive ? 'bg-running animate-pulse' : 'bg-inactive'}`} />
                <span className="text-sm font-bold text-white">{a.name}</span>
              </div>
              <div className="text-xs text-gray-400 space-y-1">
                <div>{a.description}</div>
                <div className="font-mono text-[10px] text-gray-500">{a.model.model}</div>
                <div>재시도: {a.max_retries} · 타임아웃: {a.timeout_minutes}m</div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
