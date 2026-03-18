"""requirements.md 생성 로직.

RequirementsDocument 모델을 마크다운 문서로 렌더링.
"""

from __future__ import annotations

from agentcrew.agents.agent1.models import RequirementsDocument


def render_requirements_md(doc: RequirementsDocument) -> str:
    """RequirementsDocument를 requirements.md 마크다운으로 렌더링한다.

    Args:
        doc: 요구사항 문서 모델.

    Returns:
        마크다운 형식의 문자열.
    """
    lines: list[str] = []

    # 제목
    lines.append(f"# {doc.title}")
    lines.append("")

    # 요약
    if doc.summary:
        lines.append("## 프로젝트 요약")
        lines.append("")
        lines.append(doc.summary)
        lines.append("")

    # 기능 요구사항
    if doc.functional:
        lines.append("## 기능 요구사항")
        lines.append("")

        for fr in doc.functional:
            lines.append(f"### {fr.id}: {fr.title}")
            lines.append("")
            if fr.description:
                lines.append(f"- **설명:** {fr.description}")

            if fr.scenarios:
                lines.append("- **시나리오:**")
                for s in fr.scenarios:
                    lines.append(f"  - {s}")

            if fr.edge_cases:
                lines.append("- **엣지 케이스:**")
                for e in fr.edge_cases:
                    lines.append(f"  - {e}")

            if fr.exceptions:
                lines.append("- **예외 처리:**")
                for ex in fr.exceptions:
                    lines.append(f"  - {ex}")

            lines.append("")

    # 비기능 요구사항
    if doc.non_functional:
        lines.append("## 비기능 요구사항")
        lines.append("")

        for nfr in doc.non_functional:
            lines.append(f"### {nfr.id}: {nfr.category}")
            lines.append("")
            lines.append(f"- **설명:** {nfr.description}")
            if nfr.acceptance_criteria:
                lines.append(f"- **수용 기준:** {nfr.acceptance_criteria}")
            lines.append("")

    # 미결 사항
    if doc.unresolved:
        lines.append("## 미결 사항")
        lines.append("")

        for ur in doc.unresolved:
            lines.append(f"### {ur.id}")
            lines.append("")
            lines.append(f"- **질문:** {ur.question}")
            if ur.context:
                lines.append(f"- **맥락:** {ur.context}")
            if ur.reason:
                lines.append(f"- **사유:** {ur.reason}")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"
