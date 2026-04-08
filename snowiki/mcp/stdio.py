from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from typing import BinaryIO

from .server import ReadOnlyMCPServer


def read_message(stream: BinaryIO) -> dict[str, object] | None:
    headers: dict[str, str] = {}
    line = stream.readline()
    while line in (b"\n", b"\r\n"):
        line = stream.readline()
    if not line:
        return None

    while line and line not in (b"\n", b"\r\n"):
        decoded = line.decode("utf-8").strip()
        key, _, value = decoded.partition(":")
        if not _:
            raise ValueError(f"Malformed MCP header: {decoded}")
        headers[key.casefold()] = value.strip()
        line = stream.readline()

    content_length = int(headers["content-length"])
    body = stream.read(content_length)
    if len(body) != content_length:
        raise ValueError("Unexpected EOF while reading MCP message body.")
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("MCP payload must decode to an object.")
    return payload


def write_message(stream: BinaryIO, payload: Mapping[str, object]) -> None:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    _ = stream.write(header)
    _ = stream.write(body)
    stream.flush()


def serve_stdio(
    server: ReadOnlyMCPServer,
    *,
    input_stream: BinaryIO | None = None,
    output_stream: BinaryIO | None = None,
) -> None:
    reader = input_stream or sys.stdin.buffer
    writer = output_stream or sys.stdout.buffer

    while True:
        message = read_message(reader)
        if message is None:
            return
        response = server.handle_message(message)
        if response is not None:
            write_message(writer, response)
