"""requirements.md 파싱 → Epic/Task 분해 로직.

requirements.md 텍스트를 읽어 구조화된 섹션으로 분리한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class RequirementSection:
    """requirements.md에서 추출한 단일 요구사항 섹션."""

    id: str
    """요구사항 ID (예: FR-001, NFR-001)."""

    title: str
    """요구사항 제목."""

    body: str
    """섹션 본문 (마크다운)."""

    section_type: str
    """섹션 유형: 'functional' | 'non_functional' | 'unresolved'."""


@dataclass
class ParsedRequirements:
    """파싱된 requirements.md 전체 구조."""

    summary: str = ""
    """프로젝트 요약."""

    sections: list[RequirementSection] = field(default_factory=list)
    """요구사항 섹션 목록."""

    raw_text: str = ""
    """원본 텍스트."""


def parse_requirements_md(text: str) -> ParsedRequirements:
    """requirements.md 텍스트를 파싱하여 구조화된 데이터를 반환한다.

    Args:
        text: requirements.md 파일 내용.

    Returns:
        파싱된 요구사항 구조.

    Raises:
        ValueError: 빈 텍스트 입력 시.
    """
    if not text or not text.strip():
        raise ValueError("requirements.md 내용이 비어 있습니다.")

    result = ParsedRequirements(raw_text=text)

    # 프로젝트 요약 추출
    summary_match = re.search(
        r"##\s*프로젝트\s*요약\s*\n+(.*?)(?=\n##|\Z)",
        text,
        re.DOTALL,
    )
    if summary_match:
        result.summary = summary_match.group(1).strip()

    # 현재 섹션 유형 추적
    current_type = ""
    type_map = {
        "기능 요구사항": "functional",
        "비기능 요구사항": "non_functional",
        "미결 사항": "unresolved",
    }

    # H2 섹션으로 유형 감지
    for line in text.splitlines():
        h2_match = re.match(r"^##\s+(.+)$", line)
        if h2_match:
            heading = h2_match.group(1).strip()
            if heading in type_map:
                current_type = type_map[heading]

    # H3 섹션으로 개별 요구사항 추출
    h3_pattern = re.compile(r"^###\s+(.+)$", re.MULTILINE)
    h3_positions: list[tuple[int, str]] = []
    for m in h3_pattern.finditer(text):
        h3_positions.append((m.start(), m.group(1).strip()))

    for i, (pos, heading) in enumerate(h3_positions):
        end = h3_positions[i + 1][0] if i + 1 < len(h3_positions) else len(text)
        body = text[pos:end].strip()

        # ID와 제목 분리 (예: "FR-001: 사용자 회원가입")
        id_match = re.match(r"^((?:FR|NFR|UR)-\d+)\s*:\s*(.+)$", heading)
        if id_match:
            req_id = id_match.group(1)
            title = id_match.group(2).strip()
        else:
            req_id = heading
            title = heading

        # 섹션 유형 결정
        section_type = _detect_section_type(req_id, text, pos)

        result.sections.append(
            RequirementSection(
                id=req_id,
                title=title,
                body=body,
                section_type=section_type,
            )
        )

    return result


def _detect_section_type(req_id: str, text: str, position: int) -> str:
    """요구사항 ID와 위치를 기반으로 섹션 유형을 감지한다.

    Args:
        req_id: 요구사항 ID.
        text: 전체 텍스트.
        position: 해당 섹션의 시작 위치.

    Returns:
        섹션 유형 문자열.
    """
    if req_id.startswith("FR-"):
        return "functional"
    if req_id.startswith("NFR-"):
        return "non_functional"
    if req_id.startswith("UR-"):
        return "unresolved"

    # H2 헤딩 기반으로 판단
    preceding = text[:position]
    type_map = {
        "기능 요구사항": "functional",
        "비기능 요구사항": "non_functional",
        "미결 사항": "unresolved",
    }
    last_type = "functional"
    for heading, stype in type_map.items():
        if f"## {heading}" in preceding:
            last_type = stype

    return last_type
