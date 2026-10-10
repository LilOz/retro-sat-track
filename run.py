"""Launch the PC terminal: uv run run.py [--host 0.0.0.0] [--port 8000]."""

import argparse
import sys
import threading
import webbrowser
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Launch the retro satellite terminal")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).parent / "backend"))
    import uvicorn

    if not args.no_browser:
        url = (
            f"http://{'127.0.0.1' if args.host == '0.0.0.0' else args.host}:{args.port}"
        )
        threading.Timer(1.5, webbrowser.open, args=(url,)).start()
    uvicorn.run("app.main:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
