"""Agent 1 프롬프트 템플릿 정의.

요구사항 추출, 핑퐁 질문 생성, requirements.md 생성에 사용되는 프롬프트.
"""

SYSTEM_PROMPT = """\
당신은 소프트웨어 요구사항 분석 전문가입니다.
주어진 텍스트(회의록, 채팅 로그 등)에서 기능 요구사항, 비기능 요구사항,
엣지 케이스를 체계적으로 추출합니다.
응답은 반드시 지정된 형식(YAML)으로 작성합니다.
"""

EXTRACT_REQUIREMENTS_PROMPT = """\
다음 텍스트에서 소프트웨어 요구사항을 추출하세요.

## 입력 텍스트
{input_text}

## 추출 형식 (YAML)
```yaml
summary: "프로젝트 한 줄 요약"
functional:
  - id: "FR-001"
    title: "기능 제목"
    description: "상세 설명"
    scenarios:
      - "사용 시나리오 1"
    edge_cases:
      - "엣지 케이스 1"
    exceptions:
      - "예외 처리 1"
non_functional:
  - id: "NFR-001"
    category: "성능|보안|확장성|가용성|유지보수성"
    description: "상세 설명"
    acceptance_criteria: "수용 기준"
```

## 규칙
1. 기능 요구사항은 구체적인 사용자 행동 단위로 분리
2. 각 기능에 최소 1개의 시나리오와 엣지 케이스 포함
3. 비기능 요구사항은 카테고리별로 분류
4. 불명확한 부분은 추출하되 별도 표시
"""

GENERATE_QUESTIONS_PROMPT = """\
다음은 현재까지 추출한 요구사항입니다.

## 현재 요구사항
{current_requirements}

## 기존 질문과 답변
{qa_history}

## 지시
불명확하거나 누락된 부분에 대해 명확화 질문을 생성하세요.
최대 {max_questions}개의 질문을 YAML 리스트로 작성하세요.

```yaml
questions:
  - "질문 1"
  - "질문 2"
```

질문은 구체적이고 답변 가능한 형태로 작성하세요.
이미 답변된 내용은 다시 질문하지 마세요.
추가 질문이 필요 없으면 빈 리스트를 반환하세요.
"""

REFINE_REQUIREMENTS_PROMPT = """\
기존 요구사항에 새로운 답변을 반영하여 요구사항을 보강하세요.

## 기존 요구사항
{current_requirements}

## 새로운 답변
질문: {question}
답변: {answer}

## 규칙
1. 기존 요구사항을 유지하면서 새 정보를 반영
2. 동일한 YAML 형식으로 출력
3. 변경/추가된 부분이 있으면 해당 항목을 갱신
"""

REQUIREMENTS_MD_PROMPT = """\
다음 요구사항 데이터를 기반으로 requirements.md 마크다운 문서를 생성하세요.

## 데이터
{requirements_yaml}

## 미결 사항
{unresolved_yaml}

## 문서 형식
# {title}

## 프로젝트 요약
(summary)

## 기능 요구사항
### FR-001: 제목
- **설명:** ...
- **시나리오:**
  - ...
- **엣지 케이스:**
  - ...
- **예외 처리:**
  - ...

## 비기능 요구사항
### NFR-001: 카테고리
- **설명:** ...
- **수용 기준:** ...

## 미결 사항
(핑퐁 3회 초과 또는 타임아웃으로 해결되지 않은 항목)
### UR-001
- **질문:** ...
- **맥락:** ...
- **사유:** ...
"""
