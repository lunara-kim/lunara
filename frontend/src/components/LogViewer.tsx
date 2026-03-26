import type { LogEntry } from '../mocks/logs'

const levelColors: Record<string, string> = {
  info: 'text-blue-400',
  warn: 'text-running',
  error: 'text-failed',
  debug: 'text-gray-500',
}

const agentColors: Record<string, string> = {
  agent1: 'text-purple-400',
  agent2: 'text-cyan-400',
  agent3: 'text-emerald-400',
  agent4: 'text-amber-400',
}

export default function LogViewer({ logs }: { logs: LogEntry[] }) {
  return (
    <div className="bg-card rounded-xl border border-border p-4 space-y-3">
      <h2 className="text-lg font-bold text-white">📜 실행 로그</h2>
      <div className="bg-bg-primary rounded-lg p-3 h-64 overflow-y-auto scrollbar-thin font-mono text-xs space-y-1">
        {logs.map((log, i) => (
          <div key={i} className="flex gap-2">
            <span className="text-gray-500 shrink-0">{log.timestamp}</span>
            <span className={`shrink-0 w-16 ${agentColors[log.agent] ?? 'text-gray-400'}`}>[{log.agent}]</span>
            <span className={`shrink-0 w-12 uppercase font-bold ${levelColors[log.level]}`}>{log.level}</span>
            <span className={`${log.level === 'error' ? 'text-failed' : 'text-gray-300'}`}>{log.message}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
