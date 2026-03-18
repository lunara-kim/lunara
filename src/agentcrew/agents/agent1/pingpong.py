"""핑퐁 질문 로직.

최대 3회 질문, 무응답 타임아웃 10분 처리.
"""

from __future__ import annotations

import asyncio
from typing import Callable, Awaitable, Optional

import yaml

from agentcrew.agents.agent1.llm import LLMProvider
from agentcrew.agents.agent1.models import PingPongState, UnresolvedItem
from agentcrew.agents.agent1.prompts.templates import (
    GENERATE_QUESTIONS_PROMPT,
    SYSTEM_PROMPT,
)


async def generate_questions(
    llm: LLMProvider,
    current_requirements_yaml: str,
    state: PingPongState,
    max_questions: int = 3,
) -> list[str]:
    """LLM을 사용하여 명확화 질문을 생성한다.

    Args:
        llm: LLM 프로바이더.
        current_requirements_yaml: 현재 요구사항 YAML 문자열.
        state: 핑퐁 상태.
        max_questions: 생성할 최대 질문 수.

    Returns:
        질문 문자열 리스트.
    """
    # QA 히스토리 구성
    qa_pairs: list[str] = []
    for i, q in enumerate(state.questions_asked):
        answer = state.answers_received[i] if i < len(state.answers_received) else "답변 없음"
        qa_pairs.append(f"Q: {q}\nA: {answer or '답변 없음'}")

    qa_history = "\n\n".join(qa_pairs) if qa_pairs else "없음"

    prompt = GENERATE_QUESTIONS_PROMPT.format(
        current_requirements=current_requirements_yaml,
        qa_history=qa_history,
        max_questions=max_questions,
    )

    response = await llm.generate(prompt, system=SYSTEM_PROMPT)

    # YAML 파싱
    try:
        # ```yaml ... ``` 블록 추출
        if "```yaml" in response:
            yaml_block = response.split("```yaml")[1].split("```")[0]
        elif "```" in response:
            yaml_block = response.split("```")[1].split("```")[0]
        else:
            yaml_block = response

        data = yaml.safe_load(yaml_block)
        if isinstance(data, dict) and "questions" in data:
            questions = data["questions"]
            if isinstance(questions, list):
                return [str(q) for q in questions if q]
        return []
    except (yaml.YAMLError, IndexError):
        return []


async def run_pingpong(
    llm: LLMProvider,
    current_requirements_yaml: str,
    ask_user: Callable[[str], Awaitable[Optional[str]]],
    state: Optional[PingPongState] = None,
    timeout_seconds: int = 600,
) -> PingPongState:
    """핑퐁 질문-답변 루프를 실행한다.

    Args:
        llm: LLM 프로바이더.
        current_requirements_yaml: 현재 요구사항 YAML.
        ask_user: 사용자에게 질문하고 답변을 받는 콜백. 타임아웃 시 None 반환.
        state: 기존 상태 (없으면 새로 생성).
        timeout_seconds: 무응답 타임아웃 (초). 기본 600초(10분).

    Returns:
        업데이트된 핑퐁 상태.
    """
    if state is None:
        state = PingPongState()

    while state.current_round < state.max_rounds:
        # 질문 생성
        questions = await generate_questions(
            llm, current_requirements_yaml, state
        )

        if not questions:
            # 더 이상 질문이 없으면 완료
            state.completed = True
            break

        # 질문을 하나의 메시지로 합쳐서 전달
        combined_question = "\n".join(
            f"{i + 1}. {q}" for i, q in enumerate(questions)
        )

        state.questions_asked.append(combined_question)
        state.current_round += 1

        # 사용자에게 질문 (타임아웃 적용)
        try:
            answer = await asyncio.wait_for(
                ask_user(combined_question),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            answer = None
            state.timed_out = True

        state.answers_received.append(answer)

        if state.timed_out:
            break

    state.completed = True
    return state


def collect_unresolved_items(state: PingPongState) -> list[UnresolvedItem]:
    """핑퐁 상태에서 미결 사항을 수집한다.

    3회 초과 또는 타임아웃으로 해결되지 않은 질문을 UnresolvedItem으로 변환.

    Args:
        state: 핑퐁 상태.

    Returns:
        미결 사항 리스트.
    """
    items: list[UnresolvedItem] = []
    idx = 1

    for i, question in enumerate(state.questions_asked):
        answer = state.answers_received[i] if i < len(state.answers_received) else None

        if answer is None:
            reason = "타임아웃으로 답변 미수신" if state.timed_out else "답변 없음"
            items.append(
                UnresolvedItem(
                    id=f"UR-{idx:03d}",
                    question=question,
                    context=f"핑퐁 라운드 {i + 1}",
                    reason=reason,
                )
            )
            idx += 1

    # 질문 횟수 초과로 남은 불명확한 사항이 있을 수 있음
    if state.current_round >= state.max_rounds and not state.timed_out:
        # 마지막 라운드에서도 질문이 생성되었지만 더 이상 질문 불가
        if not items:
            items.append(
                UnresolvedItem(
                    id=f"UR-{idx:03d}",
                    question="추가 명확화가 필요할 수 있는 사항이 존재",
                    context="핑퐁 최대 라운드 도달",
                    reason="최대 질문 횟수(3회) 초과",
                )
            )

    return items
