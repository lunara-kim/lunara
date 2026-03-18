# AgentCrew

멀티 에이전트 PRM(Process Reward Model) 오케스트레이터.

## 구조

```
src/agentcrew/
├── __init__.py
├── schemas/         # Pydantic 스키마 (progress, task, config)
├── prm/             # PRM 오케스트레이터
├── agents/          # Agent 1~4 구현
└── utils/           # 공통 유틸리티

.agentcrew/          # 런타임 데이터
├── config.yaml
├── tasks.yaml
├── progress.json
├── prompts/
└── logs/

tests/               # 테스트
```

## 설치

```bash
pip install -e ".[dev]"
```

## 테스트

```bash
pytest
```
