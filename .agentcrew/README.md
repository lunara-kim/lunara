# `.agentcrew/` 디렉토리 구조

AgentCrew 런타임 데이터가 저장되는 디렉토리입니다.

```
.agentcrew/
├── config.yaml          # 프로젝트 설정 (repo, stack, agent, model 등)
├── tasks.yaml           # 작업 목록 (Agent 2가 생성, Agent 3/4가 갱신)
├── progress.json        # 파이프라인 실행 상태
├── prompts/             # Agent별 프롬프트 템플릿
│   ├── agent1.md
│   ├── agent2.md
│   ├── agent3.md
│   └── agent4.md
└── logs/                # 실행 로그
    └── {timestamp}.log
```
