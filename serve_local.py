#!/usr/bin/env python3
"""Serve this static website from the local machine.

This script starts a small HTTP server rooted at the repository directory so
`index.html`, `style.css`, and other static assets can be previewed in a browser
without installing project dependencies. The script is intended for local
development only.

Examples:
    python3 serve_local.py
    python3 serve_local.py --port 8080 --no-browser
"""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from typing import Callable, Sequence
import webbrowser

_DEFAULT_HOST: str = "127.0.0.1"
_DEFAULT_PORT: int = 8000
_PORT_ATTEMPTS: int = 50


class _LocalRequestHandler(SimpleHTTPRequestHandler):
    """HTTP request handler that avoids stale browser cache during local preview."""

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Preview this static website with a local HTTP server.",
    )
    parser.add_argument(
        "--host",
        default=_DEFAULT_HOST,
        help=f"Host address to bind. Default: {_DEFAULT_HOST}",
    )
    parser.add_argument(
        "--port",
        default=_DEFAULT_PORT,
        type=int,
        help=f"Port to bind. Default: {_DEFAULT_PORT}",
    )
    parser.add_argument(
        "--strict-port",
        action="store_true",
        help="Fail instead of trying the next port when the requested port is busy.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Start the server without opening the browser automatically.",
    )
    return parser.parse_args(argv)


def _create_server(
    host: str,
    port: int,
    directory: Path,
    strict_port: bool,
) -> ThreadingHTTPServer:
    request_handler: Callable[..., _LocalRequestHandler] = partial(
        _LocalRequestHandler,
        directory=str(directory),
    )
    attempts: int = 1 if strict_port else _PORT_ATTEMPTS
    last_error: OSError | None = None

    for offset in range(attempts):
        candidate_port: int = port + offset
        try:
            server: ThreadingHTTPServer = ThreadingHTTPServer(
                (host, candidate_port),
                request_handler,
            )
        except OSError as error:
            last_error = error
            continue
        return server

    message: str = f"Unable to bind {host}:{port}"
    if not strict_port:
        message = f"{message} or the next {attempts - 1} ports"
    if last_error is not None:
        message = f"{message}: {last_error}"
    raise RuntimeError(message) from last_error


def _main(argv: Sequence[str]) -> int:
    args: argparse.Namespace = _parse_args(argv)
    site_root: Path = Path(__file__).resolve().parent

    try:
        server: ThreadingHTTPServer = _create_server(
            host=args.host,
            port=args.port,
            directory=site_root,
            strict_port=args.strict_port,
        )
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    host: str
    bound_port: int
    host, bound_port = server.server_address[:2]
    url: str = f"http://{host}:{bound_port}/"

    print(f"Serving {site_root} at {url}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)

    if not args.no_browser:
        webbrowser.open(url, new=2)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.", flush=True)
    finally:
        server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
