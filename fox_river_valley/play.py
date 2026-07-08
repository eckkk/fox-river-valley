from __future__ import annotations

import http.server
import os
import shlex
import threading
import webbrowser

from . import cmd, new_game
from .runtime import DEFAULT_SERVER_URL, RUNTIME_ENV_VAR, observer_dir, runtime_root
from scripts.run_observer_server import make_handler

DEFAULT_PORT = 8765


def _start_observer_server(port: int = DEFAULT_PORT) -> http.server.ThreadingHTTPServer:
    directory = observer_dir()
    directory.mkdir(parents=True, exist_ok=True)
    handler = make_handler(directory)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _run_line(line: str) -> str | None:
    try:
        parts = shlex.split(line)
    except ValueError as exc:
        return f"输入解析失败：{exc}"
    if not parts:
        return None
    head = parts[0].lower()
    if head in {"quit", "exit"}:
        return "__quit__"
    if head == "new_game":
        seed = parts[1] if len(parts) > 1 else None
        return new_game(seed)
    if head == "cmd":
        return cmd(" ".join(parts[1:]))
    return cmd(line)


def main() -> None:
    root = runtime_root()
    os.environ.setdefault(RUNTIME_ENV_VAR, str(root))
    print(f"Fox River Valley runtime root: {runtime_root()}")
    print("Starting observer server from scripts/run_observer_server.py behavior.")
    server = _start_observer_server()
    print(DEFAULT_SERVER_URL)
    webbrowser.open(DEFAULT_SERVER_URL)
    print("FRV> new_game 12071008")
    print("FRV> cmd gather")
    print("FRV> cmd options")
    print("Type quit to stop.")
    try:
        while True:
            line = input("FRV> ").strip()
            result = _run_line(line)
            if result == "__quit__":
                break
            if result:
                print(result)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
