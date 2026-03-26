"""python -m agentcrew.dashboard 로 대시보드 API 서버 실행."""

import uvicorn


def main() -> None:
    uvicorn.run(
        "agentcrew.dashboard.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
