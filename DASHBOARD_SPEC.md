# AgentCrew Dashboard — 프론트엔드 구현 스펙

## 개요
PRM Agent 오케스트레이터의 상태를 실시간으로 보여주는 대시보드 웹앱.

## 기술 스택
- **Vite + React + TypeScript**
- **Tailwind CSS** (다크테마)
- 프론트엔드 디렉토리: `frontend/`

## 디자인 참고
- `dashboard-wireframe.png` — 와이어프레임 이미지 참고
- 다크 배경 (#0f0f23 → #1a1a2e 그라데이션)
- 카드 배경: #1e1e3a
- 색상: 성공=#2ecc71, 실행중=#f39c12, 실패=#ef4444, 비활성=#888

## 데이터 소스 (JSON 파일 기반, 나중에 API 연동)
현재는 mock 데이터로 구현. 나중에 FastAPI 백엔드 연결 예정.

### 1. Pipeline Status (progress.json 스키마)
```python
class PipelineStatus: IDLE/RUNNING/SUCCESS/FAILED
class Progress:
    pipeline_status: PipelineStatus
    current_agent: Optional[str]  # "agent1"~"agent4"
    started_at: Optional[datetime]
    updated_at: Optional[datetime]
    error: Optional[{agent, message, timestamp, retry_count}]
```

### 2. Tasks (tasks.yaml 스키마)
```python
class TaskLayer: entity/repository/service/controller/config/test/infra
class TaskPriority: high/medium/low
class TaskStatus: new/in_progress/resolved/qa_pass/qa_fail
class Task:
    id: str  # "TASK-001"
    title: str
    description: str
    layer: TaskLayer
    priority: TaskPriority
    estimated_hours: float
    status: TaskStatus
    files_changed: list[str]
    qa_task_id: Optional[str]
    depends_on: list[str]
```

### 3. Agent Config (config.yaml 스키마)
```python
class AgentConfig:
    enabled: bool
    model: {provider, model, temperature, max_tokens}
    max_retries: int
    timeout_minutes: int
# Agent 1: 요구사항 구체화
# Agent 2: 작업 목록 생성
# Agent 3: 코드 구현
# Agent 4: QA 검증
```

## 대시보드 섹션 (위→아래)

### 1. 헤더
- 로고 + "AgentCrew Dashboard" 타이틀
- 마지막 업데이트 시간

### 2. 파이프라인 상태 바
- 왼쪽: 상태 배지 (IDLE/RUNNING/SUCCESS/FAILED, 색상 코딩)
- 가운데: Agent 1→2→3→4 순차 플로우 (각각 완료/실행중/대기 상태 표시, 화살표 연결)
- 오른쪽: 시작 시간, 경과 시간, LLM 호출 횟수

### 3. 메인 영역 (2컬럼)
**왼쪽 (넓음): Tasks 테이블**
- 컬럼: ID, Title, Layer(배지), Priority(배지), Status(배지)
- 하단: 진행률 바 (resolved/total)
- 하단: 의존성 관계 텍스트

**오른쪽 (좁음): Agent 설정 + 실행 로그**
- Agent 설정: 2x2 그리드, 각 에이전트 카드 (모델명, 재시도, 타임아웃)
- 실행 로그: 모노스페이스, 시간 + 에이전트 + 레벨 + 메시지, 색상 코딩

### 4. 통계 바
- 총 LLM 호출, 생성 파일 수, 총 코드 크기, 소요 시간, Retry 횟수, 알림 채널

### 5. 실행 히스토리
- 최근 실행 목록: 번호, 시간, 상태 배지, 설명, 소요시간/LLM호출

## Mock 데이터
와이어프레임에 보이는 데이터를 그대로 mock으로 구현할 것.

## 구현 완료 후
- `cd frontend && npm run dev`로 실행 가능해야 함
- 반응형 (1200px 기준, 모바일은 1컬럼)

When completely finished, run this command to notify me:
openclaw gateway wake --text "Done: AgentCrew 대시보드 프론트엔드 구현 완료" --mode now
