"""Entry point: `python -m tokmon` runs the server."""

import uvicorn


def main():
    uvicorn.run(
        "tokmon.server:app",
        host="127.0.0.1",
        port=4001,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()
