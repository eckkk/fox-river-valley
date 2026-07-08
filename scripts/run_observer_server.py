from __future__ import annotations

import argparse
import http.server
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fox_river_valley.runtime import DEFAULT_SERVER_URL, observer_dir, observer_paths, runtime_root, save_path
from fox_river_valley.state import load_state
from fox_river_valley.observer import render_start_screen_html, write_observer_files

DEFAULT_PORT = 8765
DEFAULT_URL = "http://127.0.0.1:8765/observer.html"
assert DEFAULT_URL == DEFAULT_SERVER_URL


def server_url(port: int) -> str:
    return DEFAULT_URL if port == DEFAULT_PORT else f"http://127.0.0.1:{port}/observer.html"


def handle_command(command: str) -> dict[str, str]:
    from fox_river_valley import cmd

    clean = str(command or "").strip()
    output = cmd(clean)
    return {"last_command": clean or "(empty)", "output": output}


def handle_new_game(payload: dict[str, object]) -> dict[str, str]:
    from fox_river_valley import new_game

    mode = str(payload.get("mode") or "solo").strip().lower()
    seed = str(payload.get("seed") or "12071008").strip() or "12071008"
    death_mode = str(payload.get("death_mode") or "cozy").strip().lower()
    family_species_value = payload.get("family_species")
    family_species = str(family_species_value).strip() if family_species_value else None

    companion_name: str | None = None
    companion_profile = "default"
    if mode in {"custom_family", "custom family", "family"}:
        companion_name = str(payload.get("companion_name") or "Alex").strip()
        companion_profile = str(payload.get("companion_profile") or "default").strip() or "default"
    elif mode in {"silas_yaya", "silas/yaya", "silas_yaya_demo", "demo"}:
        seed = seed or "12071008"
        companion_name = "Yaya"
        companion_profile = "silas_yaya"
        family_species = family_species or "silicon_fox"

    output = new_game(
        seed,
        companion_name=companion_name,
        companion_profile=companion_profile,
        family_species=family_species,
        death_mode=death_mode,
    )
    return {"last_command": "new_game", "output": output}


def initialize_observer_files(directory: Path | None = None) -> None:
    paths = observer_paths()
    target_dir = Path(directory) if directory is not None else paths["dir"]
    target_dir.mkdir(parents=True, exist_ok=True)
    target_html = target_dir / "observer.html"
    target_state = target_dir / "observer_state.json"

    if save_path().exists():
        state = load_state(save_path())
        write_observer_files(state, last_command="load", output="已载入现有存档。", reset_turn=True)
        if target_html != paths["html"]:
            target_html.write_text(paths["html"].read_text(encoding="utf-8"), encoding="utf-8")
        return

    target_html.write_text(render_start_screen_html(), encoding="utf-8")
    target_state.unlink(missing_ok=True)


def make_handler(directory: Path):
    class ObserverHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *handler_args, **handler_kwargs):
            super().__init__(*handler_args, directory=str(directory), **handler_kwargs)

        def do_POST(self) -> None:  # noqa: N802
            endpoint = self.path.rstrip("/")
            if endpoint not in {"/cmd", "/new_game"}:
                self.send_error(404, "Not Found")
                return
            length = int(self.headers.get("Content-Length", "0") or "0")
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
                if endpoint == "/new_game":
                    result = handle_new_game(payload if isinstance(payload, dict) else {})
                else:
                    result = handle_command(str(payload.get("command", "")))
                body = json.dumps(result, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as exc:  # pragma: no cover - defensive server boundary
                body = json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

    return ObserverHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve Fox River Valley observer/ with Python stdlib.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--directory", default=None)
    args = parser.parse_args()

    directory = Path(args.directory).resolve() if args.directory else observer_dir()
    directory.mkdir(parents=True, exist_ok=True)
    initialize_observer_files(directory)
    handler = make_handler(directory)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    url = server_url(args.port)
    print(url)
    print(f"Runtime root: {runtime_root()}")
    print(f"Serving {directory}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nObserver server stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
