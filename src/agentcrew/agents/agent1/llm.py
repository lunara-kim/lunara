"""LLM 추상화 인터페이스.

실제 LLM API 호출 없이 테스트 가능하도록 Protocol 기반으로 정의.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """LLM 호출 추상화 프로토콜.

    모든 LLM 연동은 이 프로토콜을 구현해야 한다.
    """

    async def generate(self, prompt: str, *, system: str = "") -> str:
        """프롬프트를 전달하고 LLM 응답 텍스트를 반환한다.

        Args:
            prompt: 사용자 프롬프트.
            system: 시스템 프롬프트 (선택).

        Returns:
            LLM 응답 텍스트.
        """
        ...
