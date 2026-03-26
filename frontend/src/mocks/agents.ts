export interface AgentConfigType {
  id: string
  name: string
  description: string
  enabled: boolean
  model: { provider: string; model: string; temperature: number; max_tokens: number }
  max_retries: number
  timeout_minutes: number
}

export const mockAgents: AgentConfigType[] = [
  {
    id: 'agent1',
    name: 'Agent 1',
    description: '요구사항 구체화',
    enabled: true,
    model: { provider: 'anthropic', model: 'claude-sonnet-4-20250514', temperature: 0.3, max_tokens: 8192 },
    max_retries: 3,
    timeout_minutes: 10,
  },
  {
    id: 'agent2',
    name: 'Agent 2',
    description: '작업 목록 생성',
    enabled: true,
    model: { provider: 'anthropic', model: 'claude-sonnet-4-20250514', temperature: 0.2, max_tokens: 8192 },
    max_retries: 3,
    timeout_minutes: 15,
  },
  {
    id: 'agent3',
    name: 'Agent 3',
    description: '코드 구현',
    enabled: true,
    model: { provider: 'openai', model: 'gpt-4o', temperature: 0.1, max_tokens: 16384 },
    max_retries: 5,
    timeout_minutes: 30,
  },
  {
    id: 'agent4',
    name: 'Agent 4',
    description: 'QA 검증',
    enabled: true,
    model: { provider: 'anthropic', model: 'claude-sonnet-4-20250514', temperature: 0.1, max_tokens: 8192 },
    max_retries: 3,
    timeout_minutes: 20,
  },
]
