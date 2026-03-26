import { useState, useEffect, useRef } from 'react'
import type { Progress } from '../mocks/progress'
import type { Task } from '../mocks/tasks'
import type { AgentConfigType } from '../mocks/agents'
import type { LogEntry } from '../mocks/logs'
import type { RunHistoryEntry } from '../mocks/history'
import { mockProgress } from '../mocks/progress'
import { mockTasks } from '../mocks/tasks'
import { mockAgents } from '../mocks/agents'
import { mockLogs } from '../mocks/logs'
import { mockHistory } from '../mocks/history'
import {
  fetchProgress,
  fetchTasks,
  fetchConfig,
  fetchLogs,
  fetchHistory,
  connectProgressWS,
  triggerPipeline as apiTrigger,
  cancelPipeline as apiCancel,
  getPipelineStatus,
} from '../api/client'

export function useDashboard() {
  const [progress, setProgress] = useState<Progress>(mockProgress)
  const [tasks, setTasks] = useState<Task[]>(mockTasks)
  const [agents, setAgents] = useState<AgentConfigType[]>(mockAgents)
  const [logs, setLogs] = useState<LogEntry[]>(mockLogs)
  const [history, setHistory] = useState<RunHistoryEntry[]>(mockHistory)
  const [isLive, setIsLive] = useState(false)
  const [isPipelineRunning, setIsPipelineRunning] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    let cancelled = false

    async function loadAll() {
      try {
        const [p, t, a, l, h] = await Promise.all([
          fetchProgress(),
          fetchTasks(),
          fetchConfig(),
          fetchLogs(),
          fetchHistory(),
        ])
        if (cancelled) return
        setProgress(p)
        setTasks(t)
        if (a.length > 0) setAgents(a)
        setLogs(l)
        setHistory(h)
        setIsLive(true)

        // Connect WebSocket for live progress
        wsRef.current = connectProgressWS((update) => {
          setProgress(update)
        })
        wsRef.current.onclose = () => setIsLive(false)
        wsRef.current.onerror = () => setIsLive(false)
      } catch {
        // API unavailable — keep mock data
        setIsLive(false)
      }
    }

    loadAll()

    return () => {
      cancelled = true
      wsRef.current?.close()
    }
  }, [])

  // Poll pipeline status when live
  useEffect(() => {
    if (!isLive) return
    const id = setInterval(async () => {
      try {
        const { is_running } = await getPipelineStatus()
        setIsPipelineRunning(is_running)
      } catch { /* ignore */ }
    }, 3000)
    return () => clearInterval(id)
  }, [isLive])

  async function triggerPipeline(inputText: string) {
    const res = await apiTrigger(inputText)
    if (res.status === 'started') setIsPipelineRunning(true)
    return res
  }

  async function cancelPipeline() {
    const res = await apiCancel()
    if (res.status === 'cancelled') setIsPipelineRunning(false)
    return res
  }

  return { progress, tasks, agents, logs, history, isLive, isPipelineRunning, triggerPipeline, cancelPipeline }
}
