"""Agent 2 사람 검수 CLI 인터페이스.

tasks.yaml 생성 후 사용자에게 Y/N 검수를 요청하는 CLI.
"""

from __future__ import annotations

import sys


def review_tasks_cli(tasks_yaml: str) -> bool:
    """tasks.yaml 내용을 표시하고 사용자에게 승인/거부를 요청한다.

    Args:
        tasks_yaml: 생성된 tasks.yaml 내용 (YAML 문자열).

    Returns:
        True면 승인, False면 거부.
    """
    print("=" * 60)
    print("📋 생성된 작업 목록 (tasks.yaml)")
    print("=" * 60)
    print(tasks_yaml)
    print("=" * 60)

    while True:
        try:
            answer = input("승인하시겠습니까? (Y/N): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n취소되었습니다.")
            return False

        if answer in ("y", "yes"):
            print("✅ 승인되었습니다.")
            return True
        if answer in ("n", "no"):
            print("❌ 거부되었습니다.")
            return False

        print("Y 또는 N을 입력해주세요.")
