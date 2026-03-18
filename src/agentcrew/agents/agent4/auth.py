"""인증 엔드포인트 토큰 발급 + curl 헤더 주입.

인증이 필요한 엔드포인트 테스트 시 토큰을 자동 발급하고
curl 시나리오에 Authorization 헤더를 주입한다.
"""

from __future__ import annotations

import json

from agentcrew.agents.agent3.executor import CommandRunner


def fetch_auth_token(
    runner: CommandRunner,
    cwd: str,
    *,
    auth_url: str = "http://localhost:8080/api/auth/login",
    username: str = "admin",
    password: str = "admin",
) -> str | None:
    """인증 엔드포인트에서 토큰을 발급받는다.

    Args:
        runner: 명령 실행기.
        cwd: 작업 디렉토리.
        auth_url: 인증 엔드포인트 URL.
        username: 사용자명.
        password: 비밀번호.

    Returns:
        Bearer 토큰 문자열. 실패 시 None.
    """
    body = json.dumps({"username": username, "password": password})
    args = [
        "curl", "-s",
        "-X", "POST",
        "-H", "Content-Type: application/json",
        "-d", body,
        auth_url,
    ]

    try:
        result = runner.run(args, cwd)
    except Exception:
        return None

    if not result.success and result.returncode != 0:
        # curl은 HTTP 에러에도 returncode 0이지만 연결 실패시 비 0
        pass

    # JSON 응답에서 토큰 추출 시도
    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return None

    # 일반적인 토큰 필드명 시도
    for key in ("token", "access_token", "accessToken", "jwt"):
        if key in data and isinstance(data[key], str):
            return data[key]

    return None
