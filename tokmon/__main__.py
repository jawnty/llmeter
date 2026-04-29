"""Entry point: `python -m tokmon` runs the server."""

import uvicorn
from . import config


def main():
    uvicorn.run(
        "tokmon.server:app",
        host=config.host(),
        port=config.port(),
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()
