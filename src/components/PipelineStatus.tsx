import { useState, useEffect } from 'react'
import type { Progress } from '../mocks/progress'
import type { AgentConfigType } from '../mocks/agents'

const statusColors: Record<string, string> = {
  idle: 'bg-inactive text-white',
  running: 'bg-running text-black',
  success: 'bg-success text-black',
  failed: 'bg-failed text-white',
}

function getAgentState(agentId: string, currentAgent: string | null, pipelineStatus: string): 'done' | 'running' | 'waiting' {
  const order = ['agent1', 'agent2', 'agent3', 'agent4']
  const currentIdx = currentAgent ? order.indexOf(currentAgent) : -1
  const thisIdx = order.indexOf(agentId)
  if (pipelineStatus === 'success') return 'done'
  if (thisIdx < currentIdx) return 'done'
  if (thisIdx === currentIdx) return 'running'
  return 'waiting'
}

const stateIcon: Record<string, string> = { done: '✅', running: '⏳', waiting: '⏸' }
const stateBorder: Record<string, string> = {
  done: 'border-success',
  running: 'border-running animate-pulse',
  waiting: 'border-border',
}

export default function PipelineStatus({ progress, agents }: { progress: Progress; agents: AgentConfigType[] }) {
  const [elapsed, setElapsed] = useState('')

  useEffect(() => {
    if (!progress.started_at || progress.pipeline_status !== 'running') return
    const start = new Date(progress.started_at).getTime()
    const tick = () => {
      const diff = Math.floor((Date.now() - start) / 1000)
      const h = Math.floor(diff / 3600)
      const m = Math.floor((diff % 3600) / 60)
      const s = diff % 60
      setElapsed(`${h}h ${m}m ${s}s`)
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [progress.started_at, progress.pipeline_status])

  return (
    <div className="mx-6 mt-4 p-4 bg-card rounded-xl border border-border flex flex-col lg:flex-row items-center gap-4">
      {/* Status badge */}
      <span className={`px-4 py-1.5 rounded-full font-bold text-sm uppercase ${statusColors[progress.pipeline_status]}`}>
        {progress.pipeline_status}
      </span>

      {/* Agent flow */}
      <div className="flex items-center gap-1 flex-1 justify-center">
        {agents.map((a, i) => {
          const state = getAgentState(a.id, progress.current_agent, progress.pipeline_status)
          return (
            <div key={a.id} className="flex items-center gap-1">
              <div className={`flex flex-col items-center px-3 py-2 rounded-lg border-2 ${stateBorder[state]} bg-bg-primary min-w-[80px]`}>
                <span className="text-lg">{stateIcon[state]}</span>
                <span className="text-xs text-gray-300 font-medium">{a.name}</span>
                <span className="text-[10px] text-inactive">{a.description}</span>
              </div>
              {i < agents.length - 1 && <span className="text-inactive text-lg">→</span>}
            </div>
          )
        })}
      </div>

      {/* Stats */}
      <div className="text-right text-sm text-gray-300 space-y-1 min-w-[160px]">
        <div>시작: {progress.started_at ? new Date(progress.started_at).toLocaleTimeString('ko-KR') : '-'}</div>
        <div>경과: <span className="text-running font-mono">{elapsed || '-'}</span></div>
        <div>LLM 호출: <span className="text-white font-bold">47</span></div>
      </div>
    </div>
  )
}
