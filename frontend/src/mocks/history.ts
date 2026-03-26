export interface RunHistoryEntry {
  run_id: number
  started_at: string
  status: 'success' | 'failed'
  description: string
  duration_minutes: number
  llm_calls: number
}

export const mockHistory: RunHistoryEntry[] = [
  {
    run_id: 3,
    started_at: '2026-03-26T14:30:00+09:00',
    status: 'success',
    description: 'User CRUD API 구현 (현재 실행)',
    duration_minutes: 75,
    llm_calls: 47,
  },
  {
    run_id: 2,
    started_at: '2026-03-25T10:00:00+09:00',
    status: 'success',
    description: 'Auth 모듈 JWT 인증 구현',
    duration_minutes: 42,
    llm_calls: 31,
  },
  {
    run_id: 1,
    started_at: '2026-03-24T16:00:00+09:00',
    status: 'failed',
    description: 'DB 마이그레이션 스크립트 생성 (타임아웃)',
    duration_minutes: 30,
    llm_calls: 18,
  },
]
