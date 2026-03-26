export type TaskLayer = 'entity' | 'repository' | 'service' | 'controller' | 'config' | 'test' | 'infra'
export type TaskPriority = 'high' | 'medium' | 'low'
export type TaskStatus = 'new' | 'in_progress' | 'resolved' | 'qa_pass' | 'qa_fail'

export interface Task {
  id: string
  title: string
  description: string
  layer: TaskLayer
  priority: TaskPriority
  estimated_hours: number
  status: TaskStatus
  files_changed: string[]
  qa_task_id: string | null
  depends_on: string[]
}

export const mockTasks: Task[] = [
  {
    id: 'TASK-001',
    title: 'User 엔티티 생성',
    description: 'User JPA 엔티티 클래스 및 BaseEntity 구현',
    layer: 'entity',
    priority: 'high',
    estimated_hours: 2,
    status: 'resolved',
    files_changed: ['src/main/java/com/app/entity/User.java', 'src/main/java/com/app/entity/BaseEntity.java'],
    qa_task_id: 'TASK-005',
    depends_on: [],
  },
  {
    id: 'TASK-002',
    title: 'UserRepository 구현',
    description: 'Spring Data JPA Repository 인터페이스 생성',
    layer: 'repository',
    priority: 'high',
    estimated_hours: 1,
    status: 'resolved',
    files_changed: ['src/main/java/com/app/repository/UserRepository.java'],
    qa_task_id: null,
    depends_on: ['TASK-001'],
  },
  {
    id: 'TASK-003',
    title: 'UserService CRUD 구현',
    description: '사용자 생성/조회/수정/삭제 비즈니스 로직',
    layer: 'service',
    priority: 'high',
    estimated_hours: 3,
    status: 'resolved',
    files_changed: ['src/main/java/com/app/service/UserService.java', 'src/main/java/com/app/dto/UserDto.java'],
    qa_task_id: 'TASK-006',
    depends_on: ['TASK-002'],
  },
  {
    id: 'TASK-004',
    title: 'UserController REST API',
    description: 'CRUD REST 엔드포인트 구현',
    layer: 'controller',
    priority: 'medium',
    estimated_hours: 2,
    status: 'resolved',
    files_changed: ['src/main/java/com/app/controller/UserController.java'],
    qa_task_id: null,
    depends_on: ['TASK-003'],
  },
  {
    id: 'TASK-005',
    title: 'User 엔티티 단위 테스트',
    description: 'User 엔티티 유효성 검증 테스트',
    layer: 'test',
    priority: 'medium',
    estimated_hours: 1.5,
    status: 'in_progress',
    files_changed: [],
    qa_task_id: null,
    depends_on: ['TASK-001'],
  },
  {
    id: 'TASK-006',
    title: 'UserService 통합 테스트',
    description: 'UserService CRUD 통합 테스트 작성',
    layer: 'test',
    priority: 'low',
    estimated_hours: 2,
    status: 'new',
    files_changed: [],
    qa_task_id: null,
    depends_on: ['TASK-003', 'TASK-005'],
  },
]
