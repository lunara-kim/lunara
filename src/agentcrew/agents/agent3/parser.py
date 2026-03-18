"""LLM 응답 파서.

===FILE: path===...===END_FILE=== 형식의 응답을 파싱하여 파일 딕셔너리로 변환한다.
"""

from __future__ import annotations

import re


def parse_file_blocks(response: str) -> dict[str, str]:
    """LLM 응답에서 파일 블록을 파싱한다.

    Args:
        response: LLM 응답 텍스트.

    Returns:
        {파일경로: 파일내용} 딕셔너리.
    """
    pattern = r"===FILE:\s*(.+?)\s*===\n(.*?)===END_FILE==="
    matches = re.findall(pattern, response, re.DOTALL)
    result: dict[str, str] = {}
    for path, content in matches:
        result[path.strip()] = content.rstrip("\n") + "\n"
    return result
