"""텍스트 입력 파싱 로직.

회의록, 채팅 로그, 자유 텍스트를 구조화된 ParsedInput으로 변환.
"""

from __future__ import annotations

import re

from agentcrew.agents.agent1.models import InputType, ParsedInput


def detect_input_type(text: str) -> InputType:
    """텍스트 유형을 자동 감지한다.

    Args:
        text: 원본 입력 텍스트.

    Returns:
        감지된 입력 유형.
    """
    # 채팅 로그 패턴: "이름: 메시지" 또는 "[시간] 이름: 메시지"
    chat_pattern = re.compile(
        r"^(\[[\d:/ -]+\]\s*)?\w+[\s]*:\s*.+", re.MULTILINE
    )
    chat_matches = chat_pattern.findall(text)

    # 회의록 패턴: 날짜, 참석자, 안건 등의 키워드
    meeting_keywords = ["회의록", "참석자", "안건", "결정사항", "회의", "일시", "장소", "minutes", "attendees", "agenda"]
    has_meeting_keywords = any(kw in text.lower() for kw in meeting_keywords)

    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]

    if has_meeting_keywords:
        return InputType.MEETING_NOTES

    # 채팅 로그: 절반 이상의 줄이 "이름: 내용" 패턴
    if lines:
        colon_lines = sum(1 for ln in lines if re.match(r"^(\[[\d:/ -]+\]\s*)?\w+\s*:\s*.+", ln))
        if colon_lines / len(lines) > 0.4:
            return InputType.CHAT_LOG

    return InputType.FREE_TEXT


def extract_speakers(text: str, input_type: InputType) -> list[str]:
    """발화자 목록을 추출한다.

    Args:
        text: 원본 텍스트.
        input_type: 입력 유형.

    Returns:
        고유 발화자 이름 리스트.
    """
    speakers: list[str] = []

    if input_type in (InputType.CHAT_LOG, InputType.MEETING_NOTES):
        pattern = re.compile(r"^(?:\[[\d:/ -]+\]\s*)?(\w+)\s*:\s*.+", re.MULTILINE)
        for match in pattern.finditer(text):
            name = match.group(1)
            if name not in speakers:
                speakers.append(name)

    return speakers


def extract_key_points(text: str) -> list[str]:
    """핵심 포인트를 추출한다.

    문장 중 요구사항성 키워드가 포함된 문장을 핵심 포인트로 간주.

    Args:
        text: 원본 텍스트.

    Returns:
        핵심 포인트 문장 리스트.
    """
    keywords = [
        "필요", "해야", "해야 한다", "원한다", "추가", "기능", "구현",
        "수정", "변경", "삭제", "필수", "중요", "요구", "지원",
        "must", "should", "need", "require", "want", "implement",
    ]

    key_points: list[str] = []

    # 문장 단위 분리
    sentences = re.split(r"[.!?\n]+", text)
    for sentence in sentences:
        stripped = sentence.strip()
        if not stripped or len(stripped) < 5:
            continue
        if any(kw in stripped.lower() for kw in keywords):
            if stripped not in key_points:
                key_points.append(stripped)

    return key_points


def parse_input(text: str) -> ParsedInput:
    """텍스트를 구조화된 ParsedInput으로 변환한다.

    Args:
        text: 원본 입력 텍스트.

    Returns:
        파싱된 입력 데이터.

    Raises:
        ValueError: 빈 텍스트가 입력된 경우.
    """
    if not text or not text.strip():
        raise ValueError("입력 텍스트가 비어 있습니다.")

    input_type = detect_input_type(text)
    speakers = extract_speakers(text, input_type)
    key_points = extract_key_points(text)

    return ParsedInput(
        raw_text=text,
        input_type=input_type,
        speakers=speakers,
        key_points=key_points,
    )
