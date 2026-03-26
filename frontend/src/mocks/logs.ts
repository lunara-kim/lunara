export interface LogEntry {
  timestamp: string
  agent: string
  level: 'info' | 'warn' | 'error' | 'debug'
  message: string
}

export const mockLogs: LogEntry[] = [
  { timestamp: '15:30:01', agent: 'agent1', level: 'info', message: '요구사항 분석 시작' },
  { timestamp: '15:31:15', agent: 'agent1', level: 'info', message: '요구사항 6개 태스크로 분해 완료' },
  { timestamp: '15:31:20', agent: 'agent2', level: 'info', message: '작업 목록 생성 시작' },
  { timestamp: '15:33:45', agent: 'agent2', level: 'info', message: 'tasks.yaml 생성 완료 (6 tasks)' },
  { timestamp: '15:34:00', agent: 'agent3', level: 'info', message: '코드 구현 시작 - TASK-001' },
  { timestamp: '15:36:22', agent: 'agent3', level: 'info', message: 'TASK-001 완료: User.java, BaseEntity.java 생성' },
  { timestamp: '15:36:30', agent: 'agent3', level: 'info', message: 'TASK-002 시작' },
  { timestamp: '15:37:10', agent: 'agent3', level: 'info', message: 'TASK-002 완료: UserRepository.java 생성' },
  { timestamp: '15:37:15', agent: 'agent3', level: 'info', message: 'TASK-003 시작' },
  { timestamp: '15:40:30', agent: 'agent3', level: 'info', message: 'TASK-003 완료: UserService.java, UserDto.java 생성' },
  { timestamp: '15:40:35', agent: 'agent3', level: 'info', message: 'TASK-004 시작' },
  { timestamp: '15:42:00', agent: 'agent3', level: 'info', message: 'TASK-004 완료: UserController.java 생성' },
  { timestamp: '15:42:05', agent: 'agent3', level: 'info', message: 'TASK-005 시작 - 빌드 검증 실행' },
  { timestamp: '15:42:10', agent: 'agent3', level: 'error', message: './gradlew: No such file or directory' },
  { timestamp: '15:42:15', agent: 'agent3', level: 'warn', message: 'Retry 1/5 - gradlew wrapper 재생성 시도' },
  { timestamp: '15:42:30', agent: 'agent3', level: 'error', message: './gradlew: Permission denied' },
  { timestamp: '15:42:35', agent: 'agent3', level: 'warn', message: 'Retry 2/5 - chmod +x 적용 후 재시도' },
  { timestamp: '15:43:00', agent: 'agent3', level: 'info', message: 'gradlew 실행 성공 - 테스트 코드 작성 중' },
]
