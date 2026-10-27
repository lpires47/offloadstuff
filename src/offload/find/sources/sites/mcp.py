"""A minimal client for remote MCP servers over streamable HTTP (JSON-RPC 2.0).

Some sites now publish an official agent interface (1stDibs: https://www.1stdibs.com/soa/mcp/).
That is the sanctioned way in, so we use it instead of reading their web pages.
"""

from __future__ import annotations

import itertools
import json

import httpx

from ..base import USER_AGENT

PROTOCOL = "2025-06-18"


class MCPError(Exception):
    pass


class _Resp:
    def __init__(self, status: int, headers: dict, text: str) -> None:
        self.status_code, self.headers, self.text = status, headers, text

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise MCPError(f"HTTP {self.status_code}")


async def _curl_post(url: str, body: dict, headers: dict, timeout: float) -> _Resp:
    """POST with the system curl. Some sites' firewalls stall Python HTTP clients' TLS handshakes;
    curl is a standard client, sending our real User-Agent, so this is not disguising anything."""
    import asyncio

    args = ["curl", "-sS", "-m", str(int(timeout)), "-D", "-", "-X", "POST", url, "--data-binary", "@-"]
    for k, v in headers.items():
        args += ["-H", f"{k}: {v}"]
    proc = await asyncio.create_subprocess_exec(*args, stdin=asyncio.subprocess.PIPE,
                                                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    out, err = await proc.communicate(json.dumps(body).encode())
    if proc.returncode != 0:
        raise MCPError(f"curl failed: {err.decode()[:200]}")
    raw = out.decode("utf-8", "replace")
    # skip proxy "200 Connection Established" blocks: the last header block belongs to the response
    blocks = raw.split("\r\n\r\n")
    i = 0
    while i < len(blocks) - 1 and blocks[i + 1].startswith("HTTP/"):
        i += 1
    head, text = blocks[i], "\r\n\r\n".join(blocks[i + 1:])
    lines = head.split("\r\n")
    status = int(lines[0].split()[1])
    hdrs = {l.split(":", 1)[0].strip().lower(): l.split(":", 1)[1].strip() for l in lines[1:] if ":" in l}
    return _Resp(status, hdrs, text)


class MCPClient:
    def __init__(self, url: str, transport: str = "httpx") -> None:
        self.url = url
        self.transport = transport
        self.session_id: str | None = None
        self._ids = itertools.count(1)

    def _headers(self) -> dict:
        h = {"User-Agent": USER_AGENT, "Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
        if self.session_id:
            h["Mcp-Session-Id"] = self.session_id
        return h

    @staticmethod
    def _decode(r: httpx.Response) -> dict:
        if "text/event-stream" in r.headers.get("content-type", ""):
            last = None
            for line in r.text.splitlines():
                if line.startswith("data:"):
                    last = json.loads(line[5:].strip())
            if last is None:
                raise MCPError("empty event stream")
            return last
        return r.json()

    async def _rpc(self, client: httpx.AsyncClient, method: str, params: dict | None = None, notify: bool = False):
        msg: dict = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        if not notify:
            msg["id"] = next(self._ids)
        if self.transport == "curl":
            r = await _curl_post(self.url, msg, self._headers(), 15)
        else:
            r = await client.post(self.url, json=msg, headers=self._headers(), timeout=8)
        if r.status_code in (401, 403):
            raise MCPError(f"{self.url} requires sign-in ({r.status_code})")
        r.raise_for_status()
        self.session_id = r.headers.get("mcp-session-id", self.session_id)
        if notify:
            return None
        body = self._decode(r)
        if "error" in body:
            raise MCPError(str(body["error"])[:300])
        return body.get("result", {})

    async def connect(self, client: httpx.AsyncClient) -> dict:
        result = await self._rpc(client, "initialize", {
            "protocolVersion": PROTOCOL,
            "capabilities": {},
            "clientInfo": {"name": "offload-find", "version": "0.1"},
        })
        await self._rpc(client, "notifications/initialized", notify=True)
        return result

    async def call(self, client: httpx.AsyncClient, tool: str, arguments: dict):
        if self.session_id is None:
            await self.connect(client)
        result = await self._rpc(client, "tools/call", {"name": tool, "arguments": arguments})
        if result.get("isError"):
            raise MCPError(f"{tool} failed: {str(result.get('content'))[:300]}")
        if "structuredContent" in result:
            return result["structuredContent"]
        texts = [c.get("text", "") for c in result.get("content", []) if c.get("type") == "text"]
        joined = "\n".join(texts)
        try:
            return json.loads(joined)
        except json.JSONDecodeError:
            return joined
