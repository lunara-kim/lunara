"""Selective Context 수집기.

build.gradle 내용, 디렉토리 트리, files_changed 기반으로
LLM 프롬프트에 필요한 컨텍스트를 수집한다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class FileSystemProvider(Protocol):
    """파일 시스템 추상화 프로토콜."""

    def read_file(self, path: str) -> str:
        """파일 내용을 읽는다."""
        ...

    def write_file(self, path: str, content: str) -> None:
        """파일에 내용을 쓴다."""
        ...

    def list_tree(self, root: str, max_depth: int = 3) -> str:
        """디렉토리 트리를 문자열로 반환한다."""
        ...

    def exists(self, path: str) -> bool:
        """경로 존재 여부를 반환한다."""
        ...


class LocalFileSystem:
    """로컬 파일 시스템 구현체."""

    def read_file(self, path: str) -> str:
        return Path(path).read_text(encoding="utf-8")

    def write_file(self, path: str, content: str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def list_tree(self, root: str, max_depth: int = 3) -> str:
        lines: list[str] = []
        self._walk(Path(root), "", 0, max_depth, lines)
        return "\n".join(lines)

    def _walk(
        self,
        path: Path,
        prefix: str,
        depth: int,
        max_depth: int,
        lines: list[str],
    ) -> None:
        if depth > max_depth:
            return
        skip = {".git", "__pycache__", "node_modules", ".gradle", "build"}
        try:
            entries = sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name))
        except PermissionError:
            return
        for entry in entries:
            if entry.name in skip:
                continue
            lines.append(f"{prefix}{entry.name}")
            if entry.is_dir():
                self._walk(entry, prefix + "  ", depth + 1, max_depth, lines)

    def exists(self, path: str) -> bool:
        return Path(path).exists()


def collect_context(
    fs: FileSystemProvider,
    project_root: str,
    files_changed: list[str],
) -> dict[str, str]:
    """Task 구현에 필요한 컨텍스트를 수집한다.

    Args:
        fs: 파일 시스템 프로바이더.
        project_root: 프로젝트 루트 경로.
        files_changed: 변경 대상 파일 경로 목록.

    Returns:
        build_gradle, directory_tree, current_files 키를 가진 딕셔너리.
    """
    # build.gradle 읽기
    build_gradle = ""
    for name in ("build.gradle", "build.gradle.kts"):
        gradle_path = f"{project_root}/{name}"
        if fs.exists(gradle_path):
            build_gradle = fs.read_file(gradle_path)
            break

    # 디렉토리 트리
    directory_tree = fs.list_tree(project_root)

    # 기존 파일 내용 수집
    current_files_parts: list[str] = []
    for fpath in files_changed:
        full_path = f"{project_root}/{fpath}"
        if fs.exists(full_path):
            content = fs.read_file(full_path)
            current_files_parts.append(f"===FILE: {fpath}===\n{content}\n===END_FILE===")

    return {
        "build_gradle": build_gradle,
        "directory_tree": directory_tree,
        "current_files": "\n\n".join(current_files_parts),
    }
