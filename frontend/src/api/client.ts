import type { Progress } from '../mocks/progress'
import type { Task } from '../mocks/tasks'
import type { AgentConfigType } from '../mocks/agents'
import type { LogEntry } from '../mocks/logs'
import type { RunHistoryEntry } from '../mocks/history'

const API_BASE = 'http://localhost:8000'

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) throw new Error(`API ${path}: ${res.status}`)
  return res.json()
}

export async function fetchProgress(): Promise<Progress> {
  return fetchJSON('/api/progress')
}

export async function fetchTasks(): Promise<Task[]> {
  const data = await fetchJSON<{ tasks: Task[] }>('/api/tasks')
  return data.tasks
}

export async function fetchConfig(): Promise<AgentConfigType[]> {
  const data = await fetchJSON<{ agents?: Record<string, any> }>('/api/config')
  if (!data.agents) return []
  return Object.entries(data.agents).map(([id, cfg]: [string, any]) => ({
    id,
    name: id.charAt(0).toUpperCase() + id.slice(1).replace(/(\d)/, ' $1'),
    description: '',
    enabled: cfg.enabled ?? true,
    model: cfg.model ?? { provider: 'openai', model: 'gpt-4o', temperature: 0.3, max_tokens: 4096 },
    max_retries: cfg.max_retries ?? 3,
    timeout_minutes: cfg.timeout_minutes ?? 10,
  }))
}

export async function fetchLogs(): Promise<LogEntry[]> {
  return fetchJSON('/api/logs')
}

export async function fetchHistory(): Promise<RunHistoryEntry[]> {
  return fetchJSON('/api/history')
}

export function connectProgressWS(onUpdate: (p: Progress) => void): WebSocket {
  const ws = new WebSocket('ws://localhost:8000/ws/progress')
  ws.onmessage = (e) => {
    try {
      onUpdate(JSON.parse(e.data))
    } catch {}
  }
  return ws
}
