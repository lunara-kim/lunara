export type PipelineStatus = 'idle' | 'running' | 'success' | 'failed'

export interface Progress {
  pipeline_status: PipelineStatus
  current_agent: string | null
  started_at: string | null
  updated_at: string | null
  error: { agent: string; message: string; timestamp: string; retry_count: number } | null
}

export const mockProgress: Progress = {
  pipeline_status: 'running',
  current_agent: 'agent3',
  started_at: '2026-03-26T14:30:00+09:00',
  updated_at: '2026-03-26T15:45:00+09:00',
  error: {
    agent: 'agent3',
    message: './gradlew: No such file or directory',
    timestamp: '2026-03-26T15:42:10+09:00',
    retry_count: 2,
  },
}
