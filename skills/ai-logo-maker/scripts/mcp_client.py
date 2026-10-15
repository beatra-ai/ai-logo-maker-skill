#!/usr/bin/env python3
"""Minimal credential-file-backed Beatra Streamable HTTP client."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import locale
import math
import os
import re
import stat
import sys
import sysconfig
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from contextlib import suppress
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, TypeVar

sys.dont_write_bytecode = True  # never leave __pycache__ inside the installed Skill

PROTOCOL_VERSION = "2025-11-25"
PACKAGE_SLUG = "ai-logo-maker"
PACKAGE_DISPLAY_NAME = "AI Logo Maker"
PACKAGE_VERSION = "0.2.4"
PACKAGE_CHANNEL = "canonical"
PACKAGE_LOCALE = "en"
PACKAGE_DISCOVERY_URL = "https://beatra.ai/skills/ai-logo-maker/install.json"
PACKAGE_CDN_BASE_TEMPLATE = "https://cdn.beatra.ai/agent-packages/ai-logo-maker/v{version}"
PACKAGE_ROUTE_POLICY = "auto"
CLIENT_INFO = {"name": f"beatra-skill-{PACKAGE_SLUG}", "version": PACKAGE_VERSION}
_PLATFORM_VALUE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
REGISTRATION_TIMEOUT_SECONDS = 10.0
HTTP_USER_AGENT = f"Beatra-Skill/{PACKAGE_SLUG}/{PACKAGE_VERSION}"
CANONICAL_MCP_URL = "https://mcp.beatra.ai/mcp"
#: Transport hosts per network route, as (mcp, api, site, cdn). Identity never
#: comes from this table: the credential, the token resource and the update
#: discovery stay bound to the constants above, and only a request's host
#: follows the route (spec 2026-10-09 §5.1). The cn channel ships the second
#: row in place of the first.
ROUTE_HOSTS = {
    "ai": ("mcp.beatra.ai", "api.beatra.ai", "beatra.ai", "cdn.beatra.ai"),
    "cn": ("mcp.beatra.cn", "api.beatra.cn", "www.beatra.cn", "cdn.beatra.cn"),
}
ROUTE_POLICIES = ("auto", "ai", "cn")
NETWORK_FILE = "network.json"
NETWORK_SCHEMA_VERSION = 1
MAX_NETWORK_BYTES = 4096
ROUTE_PROBE_PATH = "/skill-route"
ROUTE_PROBE_USER_AGENT = "Beatra-Skill-Route/1"
ROUTE_PROBE_CN_AFTER_SECONDS = 1.0
ROUTE_PROBE_DEADLINE_SECONDS = 2.5
ROUTE_SHORT_TTL_SECONDS = 10 * 60
ROUTE_MIN_TTL_SECONDS = 60 * 60
ROUTE_MAX_TTL_SECONDS = 7 * 24 * 60 * 60
ROUTE_POLICY_VERSION = 1
ROUTE_REPROBE_INTERVAL_SECONDS = 2 * 60
GATEWAY_FAILURE_STATUSES = frozenset({502, 503, 504})
MAX_ROUTE_ANSWER_BYTES = 4096
_COUNTRY_SOURCES = ("cloudflare", "ip2region", "unknown", "disabled")
_COUNTRY_CODE = re.compile(r"[A-Z]{2}\Z")
#: Ask one network ("ai" or "cn") for its /skill-route answer: the decoded JSON
#: body, or None when nothing usable came back.
RouteProbe = Callable[[str], object]
REGISTRATION_MAX_AGE_SECONDS = 24 * 60 * 60
REGISTRATION_CACHE_FILE = "registration.json"
MAX_LOCAL_RECORD_BYTES = 4096
INSTALL_SOURCES = ("website", "github", "skillhub", "skillatlas", "modelscope", "workbuddy", "clawhub")
GUESSABLE_SOURCES = (*INSTALL_SOURCES, "other")
INSTALL_SOURCE_FILE = "install-source.json"
MAX_INSTALL_SOURCE_BYTES = 1024
SOURCE_RECORD_FILE = "source.json"
_SOURCE_BASIS_RANK = {"inferred": 1, "store_marker": 2, "stamp": 3}
#: The ClawHub CLI's own record of an install (`readSkillOrigin`, clawhub
#: 0.23.3 dist/skills.js); the legacy directory name comes second.
_CLAWHUB_ORIGINS = (".clawhub/origin.json", ".clawdhub/origin.json")
_CHANNEL_VALUE = re.compile(r"[a-z][a-z0-9]{0,31}\Z")
_LOCALE_TAG = re.compile(r"[a-z]{2,3}(?:-[A-Z]{2})?\Z")
_OS_VERSION = re.compile(r"[A-Za-z0-9._ -]{1,40}\Z")
_ARCH_VALUE = re.compile(r"[a-z0-9._-]{1,48}\Z")
_OS_NAMES = {"darwin": "darwin", "linux": "linux", "win32": "windows"}
_ROUTE_BASES = ("server", "cn_geoip", "cn_unreachable", "undecided")
#: A registration is sent again when any of these change, or after a day.
_REGISTRATION_KEY = (
    "external_installation_ref",
    "package_version",
    "platform",
    "channel",
    "channel_locale",
    "route",
    "install_source",
    "install_source_basis",
)
#: After an insufficient-credit refusal, further calls to that tool stay on this
#: computer until the balance covers it, one recheck, a success, or this long.
BALANCE_HOLD_FILE = "balance-holds.json"
BALANCE_HOLD_SCHEMA_VERSION = 1
BALANCE_HOLD_SECONDS = 30 * 60
MAX_BALANCE_HOLD_BYTES = 64 * 1024
WAIT_FOR_TOP_UP = "wait_for_user_top_up"
UPDATE_DISCOVERY_TIMEOUT_SECONDS = 3.0
MAX_UPDATE_DISCOVERY_BYTES = 64 * 1024
MAX_SOURCES_BYTES = 64 * 1024
VERSION_CHECK_MAX_AGE_SECONDS = 24 * 60 * 60
MAX_LOCK_BYTES = 1024 * 1024
SKILLHUB_LOCK_FILE = ".skills_store_lock.json"
SKILLS_CLI_PROJECT_LOCK = "skills-lock.json"
SKILLS_CLI_GLOBAL_LOCK = ".skill-lock.json"
_STORE_SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
# A backslash is an escape in a POSIX shell, and a plain path character on Windows.
_PLAIN_POSIX = re.compile(r"[A-Za-z0-9_./:@%+=,-]+\Z")
_PLAIN_WINDOWS = re.compile(r"[A-Za-z0-9_./:\\@%+=,-]+\Z")
_GH_REPO_LINE = re.compile(r"^\s+github-repo:\s*\S+\s*$", re.MULTILINE)
SOURCE_LABELS = {
    "website": "the Beatra website",
    "github": "GitHub",
    "skillhub": "SkillHub",
    "clawhub": "ClawHub",
    "modelscope": "ModelScope",
    "workbuddy": "WorkBuddy",
}
_SEMVER = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)\Z")
PostJson = Callable[
    [str, dict[str, str], dict[str, Any], float],
    tuple[int, dict[str, str], dict[str, Any] | None],
]
PutBytes = Callable[[str, dict[str, str], bytes], dict[str, Any]]
GetBytes = Callable[[str, float, int], bytes]
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
AUTH_REQUIRED_CODE = "BEATRA_AUTH_REQUIRED"
RECONNECT_GUIDANCE = (
    "Reconnect with `python3 scripts/authorize.py` and follow "
    'its output until it prints "Beatra is ready".'
)
T = TypeVar("T")
AUTH_REQUIRED_MESSAGE = f"{AUTH_REQUIRED_CODE}: Beatra authorization is no longer valid. {RECONNECT_GUIDANCE}"


class AuthenticationRequired(RuntimeError):
    """The remote MCP endpoint definitively rejected the bearer credential."""


class CredentialsMissing(RuntimeError):
    """No usable credential file: this computer has not connected yet."""


def _allowlisted_unauthorized_message(raw: bytes) -> str | None:
    """Take only error.message from a Beatra 401 envelope. Never dump the body."""

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
        return None
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    details = error.get("details")
    reason = details.get("reason") if isinstance(details, dict) else None
    if error.get("code") != "mcp_connection_required" and reason != "mcp_connection_required":
        return None
    message = error.get("message")
    if not isinstance(message, str):
        return None
    cleaned = message.strip()
    return cleaned or None


def _authentication_required_message(raw: bytes) -> str:
    message = _allowlisted_unauthorized_message(raw)
    if message is None:
        return AUTH_REQUIRED_MESSAGE
    return f"{AUTH_REQUIRED_CODE}: {message} {RECONNECT_GUIDANCE}"


def _require_status(status: int, accepted: set[int], operation: str) -> None:
    if status == 401:
        raise AuthenticationRequired(AUTH_REQUIRED_MESSAGE)
    if status not in accepted:
        raise RuntimeError(f"{operation} returned HTTP {status}")


class _RejectRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, operation: str = "Beatra MCP") -> None:
        super().__init__()
        self.operation = operation

    def redirect_request(
        self,
        _request: urllib.request.Request,
        _file_pointer: Any,
        code: int,
        _message: str,
        _headers: Any,
        _new_url: str,
    ) -> None:
        raise RuntimeError(f"{self.operation} refused HTTP redirect ({code})")


def _default_post_json(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: float = 60.0,
) -> tuple[int, dict[str, str], dict[str, Any] | None]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={**headers, "User-Agent": HTTP_USER_AGENT},
        method="POST",
    )
    opener = urllib.request.build_opener(_RejectRedirectHandler())
    try:
        with opener.open(request, timeout=timeout) as response:
            status = int(response.status)
            response_headers = dict(response.headers.items())
            raw = response.read()
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        if status in GATEWAY_FAILURE_STATUSES:
            note_route_failure()
        raw = b""
        try:
            raw = exc.read() or b""
        except Exception:
            raw = b""
        if status == 401:
            raise AuthenticationRequired(_authentication_required_message(raw)) from None
        _require_status(status, set(), "Beatra MCP")
        raise AssertionError("unreachable") from exc
    except urllib.error.URLError as exc:
        note_route_failure()
        raise RuntimeError("Beatra MCP is unreachable") from exc
    except (OSError, http.client.HTTPException):
        note_route_failure()
        raise
    if not raw:
        return status, response_headers, None
    try:
        body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Beatra MCP returned HTTP {status} with an invalid response") from exc
    if not isinstance(body, dict):
        raise RuntimeError(f"Beatra MCP returned HTTP {status} with an invalid response")
    return status, response_headers, body


def _default_put_bytes(
    url: str,
    headers: dict[str, str],
    content: bytes,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=content,
        headers={**headers, "User-Agent": HTTP_USER_AGENT},
        method="PUT",
    )
    opener = urllib.request.build_opener(_RejectRedirectHandler("Beatra upload"))
    try:
        with opener.open(request, timeout=120) as response:
            status = int(response.status)
            raw = response.read()
    except urllib.error.HTTPError as exc:
        if int(exc.code) in GATEWAY_FAILURE_STATUSES:
            note_route_failure()
        raise RuntimeError(f"Beatra upload returned HTTP {int(exc.code)}") from exc
    except urllib.error.URLError as exc:
        note_route_failure()
        raise RuntimeError("Beatra upload host is unreachable") from exc
    except (OSError, http.client.HTTPException):
        note_route_failure()
        raise
    if not 200 <= status < 300:
        raise RuntimeError(f"Beatra upload returned HTTP {status}")
    try:
        body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Beatra upload returned an invalid response") from exc
    if not isinstance(body, dict):
        raise RuntimeError("Beatra upload returned an invalid response")
    return body


def _default_get_bytes(url: str, timeout: float, max_bytes: int) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json, application/zip",
            "User-Agent": HTTP_USER_AGENT,
        },
        method="GET",
    )
    opener = urllib.request.build_opener(_RejectRedirectHandler("Beatra update"))
    try:
        with opener.open(request, timeout=timeout) as response:
            if int(response.status) != 200:
                raise RuntimeError(f"Beatra update returned HTTP {int(response.status)}")
            declared = response.headers.get("Content-Length")
            if declared is not None:
                try:
                    declared_bytes = int(declared)
                except ValueError as exc:
                    raise RuntimeError("Beatra update returned an invalid content length") from exc
                if declared_bytes < 0 or declared_bytes > max_bytes:
                    raise RuntimeError("Beatra update exceeded the download limit")
            content = response.read(max_bytes + 1)
    except urllib.error.HTTPError as exc:
        if int(exc.code) in GATEWAY_FAILURE_STATUSES:
            note_route_failure()
        raise RuntimeError(f"Beatra update returned HTTP {int(exc.code)}") from exc
    except urllib.error.URLError as exc:
        note_route_failure()
        raise RuntimeError("Beatra update host is unreachable") from exc
    except (OSError, http.client.HTTPException):
        note_route_failure()
        raise
    if len(content) > max_bytes:
        raise RuntimeError("Beatra update exceeded the download limit")
    return content


def _read_local_upload(path: Path) -> tuple[str, bytes]:
    candidate = path.expanduser()
    descriptor = -1
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(candidate, flags)
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_size < 1
            or before.st_size > MAX_UPLOAD_BYTES
        ):
            raise RuntimeError(
                f"Local upload must be one regular file between 1 and {MAX_UPLOAD_BYTES} bytes"
            )
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            content = handle.read(MAX_UPLOAD_BYTES + 1)
            after = os.fstat(handle.fileno())
        stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
        if (
            len(content) != before.st_size
            or len(content) > MAX_UPLOAD_BYTES
            or any(getattr(before, field) != getattr(after, field) for field in stable_fields)
        ):
            raise RuntimeError("Local upload changed while it was being read")
    except RuntimeError:
        raise
    except OSError as exc:
        raise RuntimeError("Local upload must be one readable regular file") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    return candidate.name, content


def _header_value(headers: dict[str, str], name: str) -> str | None:
    return next((value for key, value in headers.items() if key.lower() == name.lower()), None)


def _complete_upload(
    result: dict[str, Any],
    *,
    mime_type: str,
    content: bytes,
    put_bytes: PutBytes,
) -> dict[str, str]:
    structured = result.get("structuredContent")
    instruction = structured.get("upload") if isinstance(structured, dict) else None
    if not isinstance(instruction, dict) or instruction.get("method") != "PUT":
        raise RuntimeError("Beatra upload instructions are invalid")
    url = instruction.get("url")
    headers = instruction.get("headers")
    if not isinstance(url, str) or not isinstance(headers, dict):
        raise RuntimeError("Beatra upload instructions are invalid")
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise RuntimeError("Beatra upload instructions are invalid")
    if not all(isinstance(key, str) and isinstance(value, str) for key, value in headers.items()):
        raise RuntimeError("Beatra upload instructions are invalid")
    content_type = _header_value(headers, "Content-Type")
    content_length = _header_value(headers, "Content-Length")
    if content_type != mime_type or content_length != str(len(content)):
        raise RuntimeError("Beatra upload instructions are invalid")
    response = put_bytes(url, dict(headers), content)
    artifact_id = response.get("artifact_id")
    if not isinstance(artifact_id, str) or not artifact_id:
        raise RuntimeError("Beatra upload returned an invalid response")
    return {"type": "artifact", "artifact_id": artifact_id}


def _semver(value: object) -> tuple[int, int, int]:
    if not isinstance(value, str):
        raise RuntimeError("Beatra update returned an invalid version")
    matched = _SEMVER.fullmatch(value)
    if matched is None:
        raise RuntimeError("Beatra update returned an invalid version")
    return (
        int(matched.group(1)),
        int(matched.group(2)),
        int(matched.group(3)),
    )


_ACTIVE_ROUTE: str | None = None
_ROUTE_STATE_DIR: Path | None = None


def route_policy() -> str:
    """How this build picks its network: `auto` decides per computer, `ai` and
    `cn` are fixed. Anything unrendered or unknown is the fixed `ai`."""

    return PACKAGE_ROUTE_POLICY if PACKAGE_ROUTE_POLICY in ROUTE_POLICIES else "ai"


def _read_network(state_dir: Path) -> dict[str, Any]:
    """`~/.beatra/network.json`, or {} when it is missing, unreadable, too large,
    or written in a schema this helper does not know."""

    try:
        with (state_dir.expanduser() / NETWORK_FILE).open("rb") as handle:
            content = handle.read(MAX_NETWORK_BYTES + 1)
        if len(content) > MAX_NETWORK_BYTES:
            return {}
        value = json.loads(content.decode("utf-8"))
    except (OSError, ValueError, RecursionError):
        return {}
    if not isinstance(value, dict):
        return {}
    version = value.get("schema_version")
    if isinstance(version, bool) or version != NETWORK_SCHEMA_VERSION:
        return {}
    return value


def current_route(state_dir: Path | None = None) -> str:
    """The network this process sends requests over. It never asks Beatra:
    `resolve_route` decides once at process start and records the answer."""

    policy = route_policy()
    if policy != "auto":
        return policy
    if _ACTIVE_ROUTE in ROUTE_HOSTS:
        return _ACTIVE_ROUTE
    if state_dir is not None:
        recorded = _read_network(state_dir).get("route")
        if isinstance(recorded, str) and recorded in ROUTE_HOSTS:
            return recorded
    return "ai"


def route_mcp_url(route: str) -> str:
    return f"https://{ROUTE_HOSTS[route][0]}/mcp"


def route_api_origin(route: str) -> str:
    return f"https://{ROUTE_HOSTS[route][1]}"


def _with_host(url: str, host: str) -> str:
    return urllib.parse.urlunsplit(urllib.parse.urlsplit(url)._replace(netloc=host))


def _site_url(url: str, route: str) -> str:
    return _with_host(url, ROUTE_HOSTS[route][2])


def _update_get(
    url: str,
    transport: Callable[[str, str], str],
    *,
    route: str | None,
    timeout: float,
    limit: int,
    get_bytes: GetBytes,
) -> bytes:
    """GET one update object, named by its identity URL, over the route. Update
    objects are verified by checksum, so under the auto policy a failure may
    retry once over the other route (spec §5.5); business requests never do."""

    chosen = route or current_route()
    try:
        return get_bytes(transport(url, chosen), timeout, limit)
    except Exception:  # any failure on this route may be tried on the other
        if route_policy() != "auto":
            raise
        other = "cn" if chosen == "ai" else "ai"
        return get_bytes(transport(url, other), timeout, limit)


def _route_answer(value: object) -> dict[str, Any] | None:
    """A structurally valid /skill-route answer, else None (spec §5.2)."""

    if not isinstance(value, dict) or value.get("schema_version") != 1:
        return None
    route = value.get("route")
    country = value.get("country_code")
    ttl = value.get("ttl_seconds")
    if (
        route not in ("ai", "cn", None)
        or value.get("country_source") not in _COUNTRY_SOURCES
        or not (country is None or (isinstance(country, str) and _COUNTRY_CODE.fullmatch(country)))
        or isinstance(ttl, bool)
        or not isinstance(ttl, int)
    ):
        return None
    return {
        "route": route,
        "country_code": country,
        "country_source": value["country_source"],
        "ttl_seconds": ttl,
    }


def _default_route_probe(route: str) -> object:
    """GET /skill-route on one network. It carries no credential, package or
    installation identity: only its own fixed User-Agent (spec §5.2, D1)."""

    request = urllib.request.Request(
        f"{route_api_origin(route)}{ROUTE_PROBE_PATH}",
        headers={"Accept": "application/json", "User-Agent": ROUTE_PROBE_USER_AGENT},
        method="GET",
    )
    opener = urllib.request.build_opener(_RejectRedirectHandler("Beatra route check"))
    try:
        with opener.open(request, timeout=ROUTE_PROBE_DEADLINE_SECONDS) as response:
            if int(response.status) != 200:
                return None
            raw = response.read(MAX_ROUTE_ANSWER_BYTES + 1)
        if len(raw) > MAX_ROUTE_ANSWER_BYTES:
            return None
        return json.loads(raw.decode("utf-8"))
    except (OSError, ValueError, RuntimeError, http.client.HTTPException):
        return None


def _probe_routes(
    probe: RouteProbe,
    *,
    cn_after_seconds: float,
    deadline_seconds: float,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Ask .ai first, and .cn at once when .ai says cn, fails, or is still
    silent after `cn_after_seconds`; stop as soon as the result cannot change,
    and never later than the hard deadline (spec §5.2, §5.8). Each probe runs
    in a daemon thread because getaddrinfo ignores urllib's timeout."""

    answers: dict[str, dict[str, Any] | None] = {}
    changed = threading.Condition()

    def ask(route: str) -> None:
        try:
            reply = _route_answer(probe(route))
        except Exception:  # a probe that raised gave no answer
            reply = None
        with changed:
            answers[route] = reply
            changed.notify_all()

    def launch(route: str) -> None:
        threading.Thread(target=ask, args=(route,), name=f"beatra-route-{route}", daemon=True).start()

    started = time.monotonic()
    cn_asked = False
    launch("ai")
    with changed:
        while True:
            elapsed = time.monotonic() - started
            ai_known = "ai" in answers
            if ai_known and (answers["ai"] or {}).get("route") == "ai":
                break
            if not cn_asked and (ai_known or elapsed >= cn_after_seconds):
                cn_asked = True
                launch("cn")
            if ai_known and "cn" in answers:
                break
            remaining = deadline_seconds - elapsed
            if remaining <= 0:
                break
            wait = remaining if cn_asked else min(remaining, cn_after_seconds - elapsed)
            changed.wait(max(wait, 0.001))
        return answers.get("ai"), answers.get("cn")


def _clamp_ttl(value: int) -> int:
    return max(ROUTE_MIN_TTL_SECONDS, min(ROUTE_MAX_TTL_SECONDS, value))


def decide_route(
    ai: dict[str, Any] | None,
    cn: dict[str, Any] | None,
    *,
    previous: str | None,
) -> dict[str, Any]:
    """The §5.2 table. Only a mainland verdict with a reachable .cn switches to
    cn; with no usable answer the computer keeps the route it had, so a relay
    blip never pushes a blocked mainland computer back to .ai."""

    def decided(route: str, basis: str, reply: dict[str, Any] | None, lifetime: int) -> dict[str, Any]:
        return {
            "route": route,
            "basis": basis,
            "country_code": reply["country_code"] if reply else None,
            "country_source": reply["country_source"] if reply else "unknown",
            "lifetime": lifetime,
        }

    if ai is not None and ai["route"] == "cn":
        if cn is not None:
            return decided("cn", "server", ai, _clamp_ttl(ai["ttl_seconds"]))
        return decided("ai", "cn_unreachable", ai, ROUTE_SHORT_TTL_SECONDS)
    if ai is not None and ai["route"] == "ai":
        return decided("ai", "server", ai, _clamp_ttl(ai["ttl_seconds"]))
    if cn is not None and cn["route"] in ROUTE_HOSTS:
        return decided(cn["route"], "cn_geoip", cn, _clamp_ttl(cn["ttl_seconds"]))
    fallback = previous if previous in ROUTE_HOSTS else "ai"
    return decided(fallback, "undecided", None, ROUTE_SHORT_TTL_SECONDS)


def _still_valid(record: dict[str, Any], now: float) -> bool:
    expires_at = record.get("expires_at")
    return isinstance(expires_at, (int, float)) and not isinstance(expires_at, bool) and now < expires_at


def _update_network(
    state_dir: Path,
    changes: dict[str, Any],
    *,
    remove: tuple[str, ...] = (),
) -> None:
    """Read-modify-write `network.json`, keeping `approval_link` and any key a
    newer helper added. Concurrent processes: the last writer wins."""

    record = _read_network(state_dir)
    record.update(changes)
    for key in remove:
        record.pop(key, None)
    record["schema_version"] = NETWORK_SCHEMA_VERSION
    _write_private_json(state_dir.expanduser() / NETWORK_FILE, record)


def resolve_route(
    state_dir: Path | None = None,
    *,
    now: float | None = None,
    probe: RouteProbe | None = None,
    cn_after_seconds: float = ROUTE_PROBE_CN_AFTER_SECONDS,
    deadline_seconds: float = ROUTE_PROBE_DEADLINE_SECONDS,
) -> str:
    """Decide once per process which network this computer uses (spec §5.2).

    Only `auto` builds decide; the cn channel is fixed and never asks. Every
    outcome is recorded so an offline computer does not ask on every command,
    and nothing here can fail the command that follows.
    """

    global _ACTIVE_ROUTE, _ROUTE_STATE_DIR
    policy = route_policy()
    if policy != "auto":
        _ACTIVE_ROUTE = policy
        return policy
    resolved = (state_dir or Path.home() / ".beatra").expanduser()
    _ROUTE_STATE_DIR = resolved
    observed = time.time() if now is None else now
    record = _read_network(resolved)
    recorded = record.get("route")
    # A route another helper wrote may be any JSON value: only a known name counts.
    previous = recorded if isinstance(recorded, str) and recorded in ROUTE_HOSTS else None
    if previous is not None and (record.get("pinned") is True or _still_valid(record, observed)):
        _ACTIVE_ROUTE = previous
        return previous
    try:
        ai, cn = _probe_routes(
            probe or _default_route_probe,
            cn_after_seconds=cn_after_seconds,
            deadline_seconds=deadline_seconds,
        )
        decision = decide_route(ai, cn, previous=previous)
    except Exception:
        decision = decide_route(None, None, previous=previous)
    _ACTIVE_ROUTE = decision["route"]
    with suppress(Exception):
        _update_network(
            resolved,
            {
                "route": decision["route"],
                "basis": decision["basis"],
                "pinned": False,
                "country_code": decision["country_code"],
                "country_source": decision["country_source"],
                "decided_at": int(observed),
                "expires_at": int(observed) + decision["lifetime"],
                "last_probe_at": int(observed),
                "policy_version": ROUTE_POLICY_VERSION,
            },
        )
    return decision["route"]


def note_route_failure(state_dir: Path | None = None, *, now: float | None = None) -> None:
    """A connection failure or gateway error on this computer's route: let the
    next process decide again (spec §5.5), at most once every two minutes and
    never for a route the user pinned. The failed request itself is never
    resent; it returns the error it always did."""

    if route_policy() != "auto":
        return
    resolved = state_dir or _ROUTE_STATE_DIR
    if resolved is None:
        return
    observed = time.time() if now is None else now
    with suppress(Exception):
        record = _read_network(resolved)
        if record.get("route") not in ROUTE_HOSTS or record.get("pinned") is True:
            return
        expires = record.get("expires_at")
        if isinstance(expires, (int, float)) and not isinstance(expires, bool) and expires <= observed:
            return  # already due for a new decision; later failures add nothing
        last = record.get("last_probe_at")
        if (
            isinstance(last, (int, float))
            and not isinstance(last, bool)
            and observed - last < ROUTE_REPROBE_INTERVAL_SECONDS
        ):
            return
        _update_network(resolved, {"expires_at": int(observed)})


_ROUTE_NAMES = {"ai": "the international network", "cn": "the mainland China network"}


def approval_link_preference(state_dir: Path) -> str:
    """`ai` when the user chose to open approval links on Beatra's international
    site (`authorize.py --approval-link ai`), else `auto` (spec §5.7)."""

    return "ai" if _read_network(state_dir).get("approval_link") == "ai" else "auto"


def set_approval_link_preference(state_dir: Path, choice: str) -> None:
    if choice == "ai":
        _update_network(state_dir, {"approval_link": "ai"})
    elif choice == "auto":
        _update_network(state_dir, {}, remove=("approval_link",))
    else:
        raise RuntimeError("Choose ai or auto for the approval link")


def _probe_one(probe: RouteProbe, route: str, *, deadline_seconds: float) -> dict[str, Any] | None:
    replies: list[dict[str, Any] | None] = []
    done = threading.Event()

    def ask() -> None:
        try:
            replies.append(_route_answer(probe(route)))
        except Exception:
            replies.append(None)
        finally:
            done.set()

    threading.Thread(target=ask, name=f"beatra-route-{route}", daemon=True).start()
    done.wait(deadline_seconds)
    return replies[0] if replies else None


def pin_route(
    choice: str,
    state_dir: Path,
    *,
    now: float | None = None,
    probe: RouteProbe | None = None,
    deadline_seconds: float = ROUTE_PROBE_DEADLINE_SECONDS,
) -> str:
    """`network --use`: keep one network until `--use auto` (spec §5.4). A
    network that does not answer right now is refused, so a computer is never
    locked onto a route it cannot reach."""

    global _ACTIVE_ROUTE
    if route_policy() != "auto":
        raise RuntimeError("This installation always uses the mainland China network; its network cannot be changed.")
    observed = time.time() if now is None else now
    if choice == "auto":
        _update_network(state_dir, {"pinned": False, "expires_at": 0})
        _ACTIVE_ROUTE = None
        return resolve_route(state_dir, now=observed, probe=probe)
    if choice not in ROUTE_HOSTS:
        raise RuntimeError("Choose cn, ai or auto")
    reply = _probe_one(probe or _default_route_probe, choice, deadline_seconds=deadline_seconds)
    if reply is None:
        raise RuntimeError(
            f"Beatra did not answer over {_ROUTE_NAMES[choice]} just now, so it was not selected. "
            "Check the connection and try again."
        )
    _update_network(
        state_dir,
        {
            "route": choice,
            "basis": "pinned",
            "pinned": True,
            "country_code": reply["country_code"],
            "country_source": reply["country_source"],
            "decided_at": int(observed),
            "expires_at": None,
            "last_probe_at": int(observed),
            "policy_version": ROUTE_POLICY_VERSION,
        },
    )
    _ACTIVE_ROUTE = choice
    return choice


def network_status(state_dir: Path) -> dict[str, Any]:
    policy = route_policy()
    status: dict[str, Any] = {
        "policy": policy,
        "route": current_route(state_dir),
        "approval_link": approval_link_preference(state_dir),
    }
    if policy != "auto":
        status["basis"] = "channel"
        return status
    record = _read_network(state_dir)
    if record.get("route") in ROUTE_HOSTS:
        for key in ("basis", "pinned", "country_code", "expires_at"):
            if key in record:
                status[key] = record[key]
    return status


def _network_command(choice: str | None, state_dir: Path) -> None:
    try:
        route = pin_route(choice, state_dir) if choice is not None else None
    except OSError as exc:
        raise RuntimeError(f"Could not save the network choice: {exc}") from exc
    if choice == "auto":
        print(f"Beatra chooses this computer's network automatically again; it now uses {_ROUTE_NAMES[route]}.")
    elif choice is not None:
        print(
            f"Beatra will use {_ROUTE_NAMES[route]} until you run "
            "`python3 scripts/mcp_client.py network --use auto`."
        )
    print(json.dumps(network_status(state_dir), ensure_ascii=False, separators=(",", ":")))


def _discovery_url() -> str:
    return PACKAGE_DISCOVERY_URL


def _json_object(content: bytes, operation: str) -> dict[str, Any]:
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{operation} returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{operation} returned invalid JSON")
    return value


def _sources_url() -> str:
    """The package's version list beside its discovery document, on the same
    official site host (no host literal here: cn builds rewrite the discovery)."""

    parts = urllib.parse.urlsplit(_discovery_url())
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, f"/skills/{PACKAGE_SLUG}/sources.json", "", ""))


def fetch_sources(*, get_bytes: GetBytes = _default_get_bytes, route: str | None = None) -> dict[str, Any]:
    document = _json_object(
        _update_get(
            _sources_url(),
            _site_url,
            route=route,
            timeout=UPDATE_DISCOVERY_TIMEOUT_SECONDS,
            limit=MAX_SOURCES_BYTES,
            get_bytes=get_bytes,
        ),
        "Beatra version list",
    )
    if (
        document.get("schema_version") != 1
        or document.get("package") != PACKAGE_SLUG
        or not isinstance(document.get("sources"), dict)
    ):
        raise RuntimeError("Beatra version list is invalid")
    return document


def _source_version(document: dict[str, Any], source: str) -> str | None:
    value = document["sources"].get(source)
    return value if isinstance(value, str) and _SEMVER.fullmatch(value) else None


def _shell_quote(value: str) -> str:
    """Quote a path for a POSIX shell (single quotes) or Windows (double quotes).

    Plain characters stay bare. A backslash is plain only on Windows.
    """

    windows = os.name == "nt"
    if (_PLAIN_WINDOWS if windows else _PLAIN_POSIX).fullmatch(value):
        return value
    if windows:
        return '"' + value.replace('"', '\\"') + '"'
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _locked_entry(path: Path, *, minimum: int) -> dict[str, Any] | None:
    value = _small_regular_json(path, MAX_LOCK_BYTES)
    if not isinstance(value, dict):
        return None
    version = value.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version < minimum:
        return None
    skills = value.get("skills")
    entry = skills.get(PACKAGE_SLUG) if isinstance(skills, dict) else None
    return entry if isinstance(entry, dict) else None


def _skills_cli_source(entry: dict[str, Any]) -> str | None:
    source = entry.get("source")
    if not isinstance(source, str):
        return None
    if source.startswith("beatra-ai/"):
        return "github"
    if source == "modelscope.cn":
        return "modelscope"
    return None


def _has_github_metadata(install_root: Path) -> bool:
    try:
        with (install_root / "SKILL.md").open("r", encoding="utf-8") as handle:
            head = handle.read(16 * 1024)
    except (OSError, UnicodeDecodeError):
        return False
    matched = re.match(r"\A---\n(.*?)\n---\n", head, re.DOTALL)
    return matched is not None and _GH_REPO_LINE.search(matched.group(1)) is not None


def _install_page_url() -> str:
    discovery = _discovery_url()
    return discovery[: -len("install.json")] + "install.md" if discovery.endswith("/install.json") else discovery


def detect_installer(
    install_root: Path,
    *,
    home: Path | None = None,
) -> dict[str, str] | None:
    """Which store or tool installed this copy, read only from local records,
    and the command that updates it there (spec 2026-10-14 §4.3). None when no
    record identifies one: such a copy gets no notice."""

    home = home or Path.home()
    slug = PACKAGE_SLUG
    origin = _clawhub_origin(install_root)
    if origin is not None:
        if origin.get("sourceKind") == "skills-sh":
            return None
        store_slug = origin["slug"] if _STORE_SLUG.fullmatch(origin["slug"]) else slug
        return {
            "source": "clawhub",
            "command": (
                f"clawhub update {store_slug} --workdir {_shell_quote(str(install_root.parent.parent))}"
                f" --dir {_shell_quote(install_root.parent.name)}"
            ),
            "hint": "add --force if it reports local changes",
        }
    if _locked_entry(install_root.parent / SKILLHUB_LOCK_FILE, minimum=1) is not None:
        return {
            "source": "skillhub",
            "command": f"skillhub install {slug} --force --dir {_shell_quote(str(install_root.parent))}",
        }
    parents = install_root.parents
    project = parents[2] if len(parents) > 2 else None
    if _has_github_metadata(install_root):
        command = f"gh skill update {slug}"
        if project is not None and project != home:
            command = f"{command} (run in {_shell_quote(str(project))})"
        return {"source": "github", "command": command}
    for directory in list(parents)[1:5]:
        entry = _locked_entry(directory / SKILLS_CLI_PROJECT_LOCK, minimum=1)
        if entry is not None:
            source = _skills_cli_source(entry)
            if source is None:
                return None
            return {
                "source": source,
                "command": f"npx skills update {slug} -p -y (run in {_shell_quote(str(directory))})",
            }
    if project == home:
        # The skills CLI's global lock. Its XDG_STATE_HOME location is not read:
        # the helpers read the process environment only for host detection.
        entry = _locked_entry(home / ".agents" / SKILLS_CLI_GLOBAL_LOCK, minimum=3)
        if entry is not None:
            source = _skills_cli_source(entry)
            return None if source is None else {"source": source, "command": f"npx skills update {slug} -g -y"}
    stamped = _stamped_source(install_root)
    if stamped == "workbuddy":
        return {"source": "workbuddy", "command": "open this Skill in WorkBuddy and update it there"}
    if stamped == "website" and globals().get("PACKAGE_CHANNEL") == "canonical":
        return {"source": "website", "command": f"reinstall from {_install_page_url()}"}
    return None


def version_notice(installed: dict[str, str], document: dict[str, Any]) -> str | None:
    available = _source_version(document, installed["source"])
    if available is None or _semver(available) <= _semver(PACKAGE_VERSION):
        return None
    hint = f" ({installed['hint']})" if installed.get("hint") else ""
    return (
        f"Beatra notice: {PACKAGE_SLUG} {available} is available from "
        f"{SOURCE_LABELS[installed['source']]} (installed: {PACKAGE_VERSION}). "
        f"Update with: {installed['command']}{hint}"
    )


def _has_version_list() -> bool:
    """A rendered package names its version list; an unrendered build (the
    WorkBuddy connector keeps placeholders) has none and never asks for one."""

    if not _STORE_SLUG.fullmatch(PACKAGE_SLUG):
        return False
    try:
        parts = urllib.parse.urlsplit(_discovery_url())
    except ValueError:
        return False
    return parts.scheme == "https" and bool(parts.hostname)


def maybe_notify_update(
    *,
    state_dir: Path | None = None,
    install_root: Path | None = None,
    get_bytes: GetBytes = _default_get_bytes,
    now: float | None = None,
    home: Path | None = None,
    stream: Any = None,
) -> str | None:
    """Once a day at most, say on stderr when the place this copy came from
    has a newer version. Reads only, never changes the installation, and any
    failure is silent: the user's command always runs as asked."""

    try:
        if not _has_version_list():
            return None  # an unrendered build has no list
        resolved_state = state_dir or Path.home() / ".beatra"
        resolved_root = (install_root or _current_install_root()).resolve()
        # Throttle before reading install locks, so an unidentified copy parses
        # them at most once a day.
        update_home = _update_home(resolved_state, resolved_root)
        state = _read_update_state(update_home)
        observed = time.time() if now is None else now
        last = state.get("last_checked_at")
        if (
            isinstance(last, (int, float))
            and not isinstance(last, bool)
            and 0 <= observed - float(last) < VERSION_CHECK_MAX_AGE_SECONDS
        ):
            return None
        state["last_checked_at"] = observed
        _write_private_json(update_home / "state.json", state)
        installed = detect_installer(resolved_root, home=home)
        if installed is None:
            return None
        notice = version_notice(installed, fetch_sources(get_bytes=get_bytes, route=current_route(resolved_state)))
        if notice is not None:
            print(notice, file=stream or sys.stderr)
        return notice
    except Exception:
        return None


def update_status(
    *,
    state_dir: Path | None = None,
    install_root: Path | None = None,
    get_bytes: GetBytes = _default_get_bytes,
    home: Path | None = None,
) -> str:
    """`update` / `update --check`: report what the install source offers now; never install."""

    if not _has_version_list():
        return f"{PACKAGE_SLUG} {PACKAGE_VERSION} is installed. Update it the way you installed it."
    resolved_state = state_dir or Path.home() / ".beatra"
    resolved_root = (install_root or _current_install_root()).resolve()
    installed = detect_installer(resolved_root, home=home)
    if installed is None:
        return (
            f"{PACKAGE_SLUG} {PACKAGE_VERSION} is installed. This copy does not show which store or tool "
            "installed it; update it the way you installed it."
        )
    try:
        document = fetch_sources(get_bytes=get_bytes, route=current_route(resolved_state))
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError("Beatra version list is unavailable") from exc
    return version_notice(installed, document) or (
        f"No newer {PACKAGE_SLUG} version is available from "
        f"{SOURCE_LABELS[installed['source']]} (installed: {PACKAGE_VERSION})."
    )


def _current_install_root() -> Path:
    try:
        return Path(__file__).resolve().parent.parent
    except NameError as exc:
        raise RuntimeError("Beatra package installation path is unavailable") from exc


def _ensure_private_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        with suppress(OSError):
            path.chmod(0o700)


def _update_home(state_dir: Path, install_root: Path) -> Path:
    identity = hashlib.sha256(str(install_root.resolve()).encode("utf-8")).hexdigest()[:24]
    root = state_dir.expanduser() / "updates" / identity
    _ensure_private_directory(root)
    return root


def _read_update_state(update_home: Path) -> dict[str, Any]:
    path = update_home / "state.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": 1}
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        return {"schema_version": 1}
    return value


def _write_private_json(path: Path, value: dict[str, Any]) -> None:
    _ensure_private_directory(path.parent)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{os.urandom(4).hex()}.tmp")
    descriptor = -1
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = -1
            json.dump(value, handle, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def _credentials(state_dir: Path) -> tuple[str, str]:
    state_dir = state_dir.expanduser()
    path = state_dir / "credentials.json"
    if not path.is_file():
        # Not connected yet (or the file is gone): the caller may still find
        # an approval waiting to be collected.
        raise CredentialsMissing(f"Beatra credentials are missing. {RECONNECT_GUIDANCE}")
    try:
        value = json.loads(_read_private_credentials(state_dir, path))
        mcp_url = value["mcp_url"]
        token = value["access_token"]
        token_type = value["token_type"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise CredentialsMissing(f"Beatra credentials are missing. {RECONNECT_GUIDANCE}") from exc
    if (
        not isinstance(mcp_url, str)
        or mcp_url != CANONICAL_MCP_URL
        or not isinstance(token, str)
        or not token
        or token_type != "Bearer"
    ):
        raise CredentialsMissing("Beatra credential file is invalid; authorize again")
    return mcp_url, token


def _read_private_credentials(state_dir: Path, path: Path) -> str:
    if os.name == "nt":
        # The state directory lives under the user profile, whose default
        # ACL is already private to the user (the gh/aws/gcloud posture).
        # The former custom DACL verification was dropped deliberately: its
        # command patterns read as hostile to agent safety policies and
        # endpoint security, failing installs while adding nothing an
        # elevated administrator could not bypass.
        return path.read_text(encoding="utf-8")
    if os.name != "posix":
        raise RuntimeError("Beatra credential permissions are unsupported on this platform")
    try:
        directory_stat = os.lstat(state_dir)
        if (
            not stat.S_ISDIR(directory_stat.st_mode)
            or stat.S_IMODE(directory_stat.st_mode) != 0o700
            or directory_stat.st_uid != os.getuid()
        ):
            raise RuntimeError("Beatra credential permissions are unsafe; authorize again")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            file_stat = os.fstat(descriptor)
            if (
                not stat.S_ISREG(file_stat.st_mode)
                or stat.S_IMODE(file_stat.st_mode) != 0o600
                or file_stat.st_uid != os.getuid()
            ):
                raise RuntimeError("Beatra credential permissions are unsafe; authorize again")
            with os.fdopen(descriptor, encoding="utf-8") as handle:
                descriptor = -1
                return handle.read()
        finally:
            if descriptor >= 0:
                os.close(descriptor)
    except RuntimeError:
        raise
    except OSError as exc:
        raise RuntimeError("Beatra credential permissions are unsafe; authorize again") from exc


def _message_result(body: dict[str, Any] | None, request_id: int) -> dict[str, Any]:
    if body is None or body.get("jsonrpc") != "2.0" or body.get("id") != request_id:
        raise RuntimeError("Beatra MCP returned an invalid protocol response")
    error = body.get("error")
    if isinstance(error, dict):
        code = error.get("code")
        raise RuntimeError(f"Beatra MCP protocol request failed ({code})")
    result = body.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("Beatra MCP returned an invalid protocol response")
    return result


def _tool_failure_message(result: dict[str, Any]) -> str | None:
    """Return complete agent-readable diagnostics for tool or terminal Task failure."""

    structured = result.get("structuredContent")
    structured_mapping = structured if isinstance(structured, dict) else {}
    task = structured_mapping.get("task")
    task_mapping = task if isinstance(task, dict) else {}
    is_tool_error = result.get("isError") is True
    status = structured_mapping.get("status") or task_mapping.get("status")
    if not is_tool_error and status != "failed":
        return None

    error = structured_mapping.get("error")
    if not isinstance(error, dict):
        error = task_mapping.get("error")
    content = result.get("content")
    content_items = content if isinstance(content, list) else []
    readable = " ".join(
        str(item["text"])
        for item in content_items
        if isinstance(item, dict)
        and item.get("type") == "text"
        and isinstance(item.get("text"), str)
    )
    details = (
        json.dumps(error, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        if isinstance(error, dict)
        else ""
    )
    if readable and details:
        return f"{readable} {details}"
    if readable:
        return readable
    if details:
        return details
    return "Beatra tool call failed without structured diagnostics."


_HOST_PLATFORM: str | None = None


def host_platform(state_dir: Path | None = None) -> str:
    """The agent environment this process runs inside, resolved once per
    process (docs/device-model.md): env signatures > host.json written at
    authorize time > unknown. Never a per-request cost."""
    global _HOST_PLATFORM
    if _HOST_PLATFORM is None:
        _HOST_PLATFORM = _detect_host_platform(state_dir or Path.home() / ".beatra")
    return _HOST_PLATFORM


def _detect_host_platform(state_dir: Path) -> str:
    env = os.environ
    if env.get("CLAUDECODE") == "1" or "CLAUDE_CODE_ENTRYPOINT" in env:
        return "claude-code"
    if any(key.startswith("CODEX_") for key in env):
        return "codex"
    ai_agent = env.get("AI_AGENT", "").lower()
    matched = re.match(r"([a-z0-9-]+)_", ai_agent)
    if matched and _PLATFORM_VALUE.fullmatch(matched.group(1)):
        return matched.group(1)
    try:
        value = json.loads((state_dir / "host.json").read_text(encoding="utf-8"))
        candidate = value.get("platform")
        if isinstance(candidate, str) and _PLATFORM_VALUE.fullmatch(candidate):
            return candidate
    except (OSError, ValueError, AttributeError):
        pass
    return "unknown"


class Session:
    def __init__(self, *, state_dir: Path, post_json: PostJson) -> None:
        _identity_url, token = _credentials(state_dir)
        self.url = route_mcp_url(current_route(state_dir))
        self.headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "MCP-Protocol-Version": PROTOCOL_VERSION,
        }
        token = ""
        self.post_json = post_json

    def send(self, payload: dict[str, Any], timeout: float = 60.0) -> tuple[int, dict[str, Any] | None]:
        status, response_headers, body = self.post_json(self.url, dict(self.headers), payload, timeout)
        session_id = next(
            (value for name, value in response_headers.items() if name.lower() == "mcp-session-id"),
            None,
        )
        if session_id:
            self.headers["MCP-Session-Id"] = session_id
        return status, body

    def initialize(self) -> None:
        status, body = self.send(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": CLIENT_INFO,
                },
            }
        )
        _require_status(status, {200}, "Beatra MCP initialize")
        result = _message_result(body, 1)
        negotiated_version = result.get("protocolVersion")
        if negotiated_version != PROTOCOL_VERSION:
            raise RuntimeError("Beatra MCP returned an unsupported protocol version")
        self.headers["MCP-Protocol-Version"] = negotiated_version
        status, _ = self.send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        _require_status(status, {200, 202}, "Beatra MCP initialization")

    def request(
        self,
        request_id: int,
        method: str,
        params: dict[str, Any],
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        if method == "tools/call":
            arguments = params.get("arguments")
            if isinstance(arguments, dict):
                # Source attribution (docs/device-model.md): every business call
                # names the package and host environment that initiated it. The
                # server strips these before schema validation; they never
                # change a retry's idempotency identity.
                arguments.setdefault("source_package_slug", PACKAGE_SLUG)
                arguments.setdefault("source_platform", host_platform())
        status, body = self.send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            },
            timeout,
        )
        _require_status(status, {200}, "Beatra MCP request")
        return _message_result(body, request_id)


def _registration_reference(state_dir: Path) -> str:
    try:
        value = json.loads((state_dir / "installation.json").read_text(encoding="utf-8"))
        reference = value["external_installation_ref"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Beatra installation state is invalid; authorize again") from exc
    if not isinstance(reference, str) or not reference.startswith("beatra:"):
        raise RuntimeError("Beatra installation state is invalid; authorize again")
    return reference


def _small_regular_json(path: Path, limit: int) -> Any:
    """The JSON value of a regular file no larger than `limit` bytes, else None.
    Symbolic links, directories, oversized or undecodable files are ignored."""

    try:
        info = os.lstat(path)
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            return None
        with path.open("rb") as handle:
            raw = handle.read(limit + 1)
    except OSError:
        return None
    if len(raw) > limit:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, RecursionError):
        return None


def _channel_identity() -> tuple[str, str] | None:
    """The channel and locale fixed at build time, when this build has a real
    one (the WorkBuddy connector keeps placeholders and reports none)."""

    channel = globals().get("PACKAGE_CHANNEL")
    locale_name = globals().get("PACKAGE_LOCALE")
    if (
        isinstance(channel, str)
        and isinstance(locale_name, str)
        and _CHANNEL_VALUE.fullmatch(channel)
        and _LOCALE_TAG.fullmatch(locale_name)
    ):
        return channel, locale_name
    return None


def _route_report(state_dir: Path) -> tuple[str, str] | None:
    policy = route_policy()
    if policy != "auto":
        return policy, "channel"
    record = _read_network(state_dir)
    route = record.get("route")
    if route not in ROUTE_HOSTS:
        return None
    if record.get("pinned") is True:
        return route, "pinned"
    basis = record.get("basis")
    return (route, basis) if basis in _ROUTE_BASES else None


def _os_release(system: str | None) -> str | None:
    if system == "darwin":
        # macOS only. On Windows the platform module may query WMI or start a
        # shell, which endpoint security reads as reconnaissance (spec §7).
        import platform

        return platform.mac_ver()[0] or None
    if system == "windows":
        version = sys.getwindowsversion()
        return f"{version.major}.{version.minor}.{version.build}"
    if system == "linux":
        return os.uname().release
    return None


def _environment() -> dict[str, Any]:
    """Coarse runtime facts for distribution analytics (spec §7): no user name,
    path, environment variable or address. A fact outside the shape Beatra
    records is left out rather than sent."""

    facts: dict[str, Any] = {}
    system = _OS_NAMES.get(sys.platform) or ("linux" if sys.platform.startswith("linux") else None)
    if system is not None:
        facts["os"] = system
    with suppress(Exception):
        release = _os_release(system)
        if isinstance(release, str) and _OS_VERSION.fullmatch(release):
            facts["os_version"] = release
    with suppress(Exception):
        arch = sysconfig.get_platform().lower()
        if _ARCH_VALUE.fullmatch(arch):
            facts["arch"] = arch
    facts["python"] = ".".join(str(part) for part in sys.version_info[:3])
    with suppress(Exception):
        language = locale.getlocale()[0]
        if isinstance(language, str):
            tag = language.replace("_", "-")
            if _LOCALE_TAG.fullmatch(tag):
                facts["locale"] = tag
    with suppress(Exception):
        offset = datetime.now().astimezone().utcoffset()
        if offset is not None:
            minutes = int(offset.total_seconds() // 60)
            if -720 <= minutes <= 840:
                facts["tz_offset_minutes"] = minutes
    return facts


def _own_install_root() -> Path | None:
    try:
        return _current_install_root()
    except RuntimeError:
        return None


def _stamped_source(install_root: Path) -> str | None:
    """The `install-source.json` Beatra adds to a copy it hands to a store or
    site (spec §6.1). It is in no manifest, so updates leave it in place."""

    value = _small_regular_json(install_root / INSTALL_SOURCE_FILE, MAX_INSTALL_SOURCE_BYTES)
    if isinstance(value, dict) and value.get("schema_version") == 1 and value.get("source") in INSTALL_SOURCES:
        return value["source"]
    return None


def _clawhub_origin(install_root: Path) -> dict[str, Any] | None:
    """The ClawHub CLI's own record of this install (`readSkillOrigin`, clawhub
    0.23.3 dist/skills.js), when it parses; the legacy directory name comes second."""

    for relative in _CLAWHUB_ORIGINS:
        value = _small_regular_json(install_root / relative, MAX_LOCAL_RECORD_BYTES)
        if value is None:
            continue  # unreadable or unparsable: the CLI tries the legacy name
        # A file that parses decides, as in the CLI's `readSkillOrigin`.
        if not isinstance(value, dict) or value.get("version") != 1:
            return None
        installed_at = value.get("installedAt")
        if (
            all(isinstance(value.get(key), str) and value[key] for key in ("registry", "slug", "installedVersion"))
            and isinstance(installed_at, (int, float))
            and not isinstance(installed_at, bool)
            and math.isfinite(installed_at)
        ):
            return value
        return None
    return None


def _store_marker_source(install_root: Path) -> str | None:
    """A store client's own record inside this installation, for the stores
    whose record format is verified (spec §6.3: ClawHub only)."""

    origin = _clawhub_origin(install_root)
    if origin is None:
        return None
    return "github" if origin.get("sourceKind") == "skills-sh" else "clawhub"


def _read_source_record(update_home: Path) -> dict[str, Any] | None:
    value = _small_regular_json(update_home / SOURCE_RECORD_FILE, MAX_LOCAL_RECORD_BYTES)
    if not isinstance(value, dict):
        return None
    basis, source = value.get("basis"), value.get("value")
    if not isinstance(basis, str) or not isinstance(source, str) or basis not in _SOURCE_BASIS_RANK:
        return None
    if source in INSTALL_SOURCES or (source == "other" and basis == "inferred"):
        return value
    return None


def record_install_source(value: str, basis: str, *, update_home: Path, now: float) -> dict[str, Any]:
    """Keep the strongest evidence (spec §6.3): a stamp always wins because the
    file is the current fact; otherwise only a stronger basis replaces."""

    stored = _read_source_record(update_home)
    if stored is not None:
        same = stored["value"] == value and stored["basis"] == basis
        not_stronger = _SOURCE_BASIS_RANK[basis] <= _SOURCE_BASIS_RANK[stored["basis"]]
        if same or (basis != "stamp" and not_stronger):
            return stored
    record = {"value": value, "basis": basis, "recorded_at": int(now)}
    _write_private_json(update_home / SOURCE_RECORD_FILE, record)
    return record


def _install_source(state_dir: Path, install_root: Path, *, now: float) -> tuple[str, str] | None:
    # Evidence in the installation decides, even when the state directory is
    # read-only; saving the record is best effort (spec §6.3).
    stamped = _stamped_source(install_root)
    marker = None if stamped is not None else _store_marker_source(install_root)
    found = (stamped, "stamp") if stamped is not None else (marker, "store_marker") if marker is not None else None
    if found is not None:
        with suppress(Exception):
            kept = record_install_source(found[0], found[1], update_home=_update_home(state_dir, install_root), now=now)
            return kept["value"], kept["basis"]
        return found
    record = _read_source_record(_update_home(state_dir, install_root))
    return (record["value"], record["basis"]) if record else None


def guess_install_source(
    value: str,
    *,
    state_dir: Path | None = None,
    install_root: Path | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    """`install-source --guess`: the agent's reading of how this Skill was
    installed, from the conversation. It never replaces a stamp or a store
    record (spec §6.3)."""

    if value not in GUESSABLE_SOURCES:
        raise RuntimeError("Unknown install source")
    resolved_state = state_dir or Path.home() / ".beatra"
    root = (install_root or _current_install_root()).resolve()
    observed = time.time() if now is None else now
    return record_install_source(value, "inferred", update_home=_update_home(resolved_state, root), now=observed)


def _registration_arguments(
    state_dir: Path,
    install_root: Path | None,
    *,
    now: float,
) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "package_slug": PACKAGE_SLUG,
        "package_version": PACKAGE_VERSION,
        "platform": host_platform(state_dir),
        "external_installation_ref": _registration_reference(state_dir),
    }
    identity = _channel_identity()
    if identity is not None:
        arguments["channel"], arguments["channel_locale"] = identity
    with suppress(Exception):
        route = _route_report(state_dir)
        if route is not None:
            arguments["route"], arguments["route_basis"] = route
    if install_root is not None:
        with suppress(Exception):
            source = _install_source(state_dir, install_root, now=now)
            if source is not None:
                arguments["install_source"], arguments["install_source_basis"] = source
    with suppress(Exception):
        environment = _environment()
        if environment:
            arguments["environment"] = environment
    return arguments


def _registration_key(arguments: dict[str, Any]) -> dict[str, Any]:
    return {key: arguments.get(key) for key in _REGISTRATION_KEY}


def _registration_is_fresh(
    state_dir: Path,
    install_root: Path,
    arguments: dict[str, Any],
    *,
    now: float,
) -> bool:
    value = _small_regular_json(
        _update_home(state_dir, install_root) / REGISTRATION_CACHE_FILE, MAX_LOCAL_RECORD_BYTES
    )
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        return False
    registered_at = value.get("registered_at")
    return (
        value.get("key") == _registration_key(arguments)
        and isinstance(registered_at, (int, float))
        and not isinstance(registered_at, bool)
        and now - float(registered_at) < REGISTRATION_MAX_AGE_SECONDS
    )


def _write_registration_cache(
    state_dir: Path,
    install_root: Path,
    arguments: dict[str, Any],
    *,
    now: float,
    recognized: bool | None,
) -> None:
    _write_private_json(
        _update_home(state_dir, install_root) / REGISTRATION_CACHE_FILE,
        {
            "schema_version": 1,
            "key": _registration_key(arguments),
            "registered_at": now,
            "recognized": recognized,
        },
    )


def _record_skill_inventory(state_dir: Path) -> None:
    """Keep this package present in the device-local skill inventory.

    ~/.beatra/skills.json is what the uninstall flow consults before it may
    revoke the shared credential — recording on every use (not only at
    authorize time) means an install that skipped or predates the authorize
    step still becomes visible before anyone decides it does not exist.
    Best-effort: inventory failure never blocks the requested operation.
    """

    try:
        try:
            root = Path(__file__).resolve().parent.parent
        except NameError:
            return
        resolved = str(root)
        path = state_dir / "skills.json"
        entries: list[dict[str, Any]] = []
        if path.exists():
            value = json.loads(path.read_text(encoding="utf-8"))
            loaded = value.get("skills") if isinstance(value, dict) else None
            if isinstance(loaded, list):
                entries = [entry for entry in loaded if isinstance(entry, dict)]
        if any(
            entry.get("slug") == PACKAGE_SLUG and entry.get("install_path") == resolved
            for entry in entries
        ):
            return
        entries.append(
            {
                "slug": PACKAGE_SLUG,
                "platform": host_platform(state_dir),
                "install_path": resolved,
                "recorded_at": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
            }
        )
        temporary = path.with_name(f".{path.name}.inventory.tmp")
        temporary.write_text(
            json.dumps(
                {"schema_version": 1, "skills": entries},
                ensure_ascii=False,
                separators=(",", ":"),
            )
            + "\n",
            encoding="utf-8",
        )
        with suppress(OSError):
            temporary.chmod(0o600)
        temporary.replace(path)
    except Exception:
        pass


def register_installation(
    session: Session,
    *,
    state_dir: Path,
    now: float | None = None,
    install_root: Path | None = None,
) -> None:
    """Best-effort registration of this installation (spec 2026-10-09 §7), the
    one report the Skill sends: package, channel, network route, install source
    and coarse runtime facts. It never blocks the requested creative operation."""

    _record_skill_inventory(state_dir)
    observed_at = time.time() if now is None else now
    try:
        root = install_root or _own_install_root()
        arguments = _registration_arguments(state_dir, root, now=observed_at)
        cached = dict(arguments)
        fresh = False
        if root is not None:
            # An unreadable or unwritable state directory means "not fresh":
            # the registration is still sent.
            with suppress(Exception):
                fresh = _registration_is_fresh(state_dir, root, cached, now=observed_at)
        if fresh:
            return
        result = session.request(
            2,
            "tools/call",
            {"name": "beatra.installations.register", "arguments": arguments},
            # Registration does not get the business-call time budget: a
            # degraded backend may cost the user at most this long, once per
            # cache window, before their real work proceeds.
            timeout=REGISTRATION_TIMEOUT_SECONDS,
        )
        if _tool_failure_message(result):
            return
        structured = result.get("structuredContent")
        recognized = structured.get("recognized") if isinstance(structured, dict) else None
        if root is not None:
            # The cache is best effort; its failure never undoes a sent registration.
            with suppress(Exception):
                _write_registration_cache(
                    state_dir,
                    root,
                    cached,
                    now=observed_at,
                    recognized=recognized if isinstance(recognized, bool) else None,
                )
    except Exception:
        # Registration is deliberately best effort. No transport, protocol,
        # cache, or future client error may block the creative call that follows.
        return


def _session_with_registration(
    *,
    state_dir: Path,
    post_json: PostJson,
) -> Session:
    session = Session(state_dir=state_dir, post_json=post_json)
    session.initialize()
    register_installation(session, state_dir=state_dir)
    return session


def verify(
    *,
    state_dir: Path | None = None,
    post_json: PostJson = _default_post_json,
) -> None:
    resolved_state_dir = state_dir or Path.home() / ".beatra"
    session = _session_with_registration(state_dir=resolved_state_dir, post_json=post_json)
    result = session.request(
        2,
        "tools/call",
        {"name": "beatra.tasks.list", "arguments": {}},
    )
    if failure := _tool_failure_message(result):
        raise RuntimeError(f"Beatra connection verification was rejected: {failure}")
    print("Beatra connection verified with the non-billable task list.")


def upload(
    path: Path,
    *,
    mime_type: str,
    state_dir: Path | None = None,
    post_json: PostJson = _default_post_json,
    put_bytes: PutBytes = _default_put_bytes,
) -> dict[str, str]:
    if re.fullmatch(r"[a-z0-9][a-z0-9.+-]*/[a-z0-9][a-z0-9.+-]*", mime_type) is None:
        raise RuntimeError("Local upload MIME type is invalid")
    filename, content = _read_local_upload(path)
    resolved_state_dir = state_dir or Path.home() / ".beatra"
    session = _session_with_registration(state_dir=resolved_state_dir, post_json=post_json)
    result = session.request(
        2,
        "tools/call",
        {
            "name": "beatra.assets.upload",
            "arguments": {
                "filename": filename,
                "mime_type": mime_type,
                "size_bytes": len(content),
            },
        },
    )
    if failure := _tool_failure_message(result):
        raise RuntimeError(f"Beatra rejected the upload grant request: {failure}")
    return _complete_upload(
        result,
        mime_type=mime_type,
        content=content,
        put_bytes=put_bytes,
    )


def _balance_hold_key(state_dir: Path) -> str | None:
    """Holds belong to one credential, so a second account signed in on this
    computer is never held by the first one's refusal. Never the token itself."""

    try:
        _identity_url, token = _credentials(state_dir)
    except Exception:
        return None
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:32]


def _credits(value: object) -> Decimal | None:
    if not isinstance(value, str):
        return None
    try:
        amount = Decimal(value)
    except InvalidOperation:
        return None
    return amount if amount.is_finite() else None


def _hold_is_live(hold: object, now: float) -> bool:
    if not isinstance(hold, dict):
        return False
    held_at = hold.get("held_at")
    if isinstance(held_at, bool) or not isinstance(held_at, (int, float)):
        return False
    try:
        age = now - float(held_at)
    except OverflowError:
        return False
    # A clock set back reads as expired: a hold may end early, never late.
    return (
        math.isfinite(age)
        and 0 <= age < BALANCE_HOLD_SECONDS
        and isinstance(hold.get("message"), str)
        and isinstance(hold.get("top_up_url"), str)
    )


def _read_balance_holds(state_dir: Path, now: float) -> dict[str, dict[str, dict[str, Any]]]:
    """Live holds by credential and tool. Anything unreadable reads as none:
    a damaged record must never stop a call."""

    value = _small_regular_json(state_dir.expanduser() / BALANCE_HOLD_FILE, MAX_BALANCE_HOLD_BYTES)
    if not isinstance(value, dict) or value.get("schema_version") != BALANCE_HOLD_SCHEMA_VERSION:
        return {}
    holds = value.get("holds")
    if not isinstance(holds, dict):
        return {}
    live: dict[str, dict[str, dict[str, Any]]] = {}
    for key, tools in holds.items():
        if isinstance(key, str) and isinstance(tools, dict):
            kept = {tool: hold for tool, hold in tools.items() if isinstance(tool, str) and _hold_is_live(hold, now)}
            if kept:
                live[key] = kept
    return live


def _balance_refusal(result: dict[str, Any]) -> dict[str, Any] | None:
    """The facts of an insufficient-credit refusal that waits for a top-up.
    A refusal with another way forward (the free first video: change the
    request and it runs at no charge) is never held."""

    structured = result.get("structuredContent")
    error = structured.get("error") if isinstance(structured, dict) else None
    if result.get("isError") is not True or not isinstance(error, dict):
        return None
    details = error.get("details")
    details = details if isinstance(details, dict) else {}
    message = error.get("message")
    top_up_url = details.get("top_up_url")
    if (
        error.get("code") != "insufficient_balance"
        or details.get("retry_policy", WAIT_FOR_TOP_UP) != WAIT_FOR_TOP_UP
        or "offer" in details
        or not isinstance(message, str)
        or not message
        or not isinstance(top_up_url, str)
        or not top_up_url
    ):
        return None
    facts: dict[str, Any] = {"message": message, "top_up_url": top_up_url}
    for name in ("required_credits", "balance_credits"):
        if _credits(details.get(name)) is not None:
            facts[name] = details[name]
    return facts


def _balance_covers(hold: dict[str, Any], balance: Decimal) -> bool:
    required = _credits(hold.get("required_credits"))
    return balance >= required if required is not None else balance > 0


def _steps_down(refusal: dict[str, Any], previous: dict[str, Any] | None) -> bool:
    """A refused recheck that asked for less than the hold it rechecked: someone
    choosing cheaper requests keeps one more recheck. A loop at one price never
    steps down, so it stays held."""

    if previous is None:
        return False
    asked = _credits(refusal.get("required_credits"))
    held = _credits(previous.get("required_credits"))
    return asked is not None and held is not None and asked < held


def _note_balance_outcome(
    state_dir: Path,
    key: str,
    tool_name: str,
    result: dict[str, Any],
    *,
    rechecked: bool,
    now: float,
) -> None:
    """Hold the tool after a refusal; lift holds the balance now covers; lift
    the tool's hold after it succeeds. Best effort: never fails the call."""

    try:
        holds = _read_balance_holds(state_dir, now)
        before = json.dumps(holds, sort_keys=True)
        mine = dict(holds.get(key, {}))
        refusal = _balance_refusal(result)
        if refusal is not None:
            spent = rechecked and not _steps_down(refusal, mine.get(tool_name))
            mine[tool_name] = {**refusal, "held_at": now, "rechecked": spent}
        elif _tool_failure_message(result) is not None:
            return
        elif tool_name == "beatra.wallet.get":
            structured = result.get("structuredContent")
            balance = _credits(structured.get("balance_credits") if isinstance(structured, dict) else None)
            if balance is None:
                return
            mine = {tool: hold for tool, hold in mine.items() if not _balance_covers(hold, balance)}
        else:
            mine.pop(tool_name, None)
        if mine:
            holds[key] = mine
        else:
            holds.pop(key, None)
        # Untouched holds mean no write: an ordinary success never rewrites,
        # and a record this version cannot read is left alone.
        if json.dumps(holds, sort_keys=True) == before:
            return
        path = state_dir.expanduser() / BALANCE_HOLD_FILE
        if holds:
            _write_private_json(path, {"schema_version": BALANCE_HOLD_SCHEMA_VERSION, "holds": holds})
        else:
            path.unlink(missing_ok=True)
    except Exception:
        return


def _utc(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: UP017


def _held_result(tool_name: str, hold: dict[str, Any]) -> dict[str, Any]:
    """The refusal Beatra gave, repeated without sending anything. Same shape and
    exit status as the refusal itself: the text a user may be shown is Beatra's
    own message, and what ends the hold is in details.agent_note, as on the
    server's refusal."""

    required = hold.get("required_credits")
    lifts = (
        f"the hold lifts once the balance covers {required} credits"
        if required is not None
        else "the hold lifts once the balance is above zero"
    )
    rechecked = hold.get("rechecked") is True
    expires_at = _utc(hold["held_at"] + BALANCE_HOLD_SECONDS)
    last = (
        f"A recheck was already refused, so the hold stays until then or until {expires_at}."
        if rechecked
        else "If the user chose a cheaper request instead, run that cheaper call once with --recheck-balance."
    )
    note = (
        f"Not sent: Beatra refused {tool_name} for insufficient credits at {_utc(hold['held_at'])}, "
        f"so this computer is holding further {tool_name} calls. Stop the remaining paid work, "
        "including the rest of any batch or script, and tell the user to top up. After the user "
        f"says they have topped up, call beatra.wallet.get; {lifts}. {last}"
    )
    details: dict[str, Any] = {
        "top_up_url": hold["top_up_url"],
        "retry_policy": WAIT_FOR_TOP_UP,
        "agent_note": note,
    }
    for name in ("required_credits", "balance_credits"):
        if name in hold:
            details[name] = hold[name]
    details["local_hold"] = {
        "tool": tool_name,
        "held_at": _utc(hold["held_at"]),
        "expires_at": expires_at,
        "recheck_available": not rechecked,
    }
    return {
        "isError": True,
        "content": [{"type": "text", "text": hold["message"]}],
        "structuredContent": {
            "error": {
                "code": "insufficient_balance",
                "type": "billing_error",
                "retryable": False,
                "message": hold["message"],
                "details": details,
            }
        },
    }


def call_tool(
    tool_name: str,
    arguments: dict[str, Any],
    *,
    state_dir: Path | None = None,
    post_json: PostJson = _default_post_json,
    recheck_balance: bool = False,
    now: float | None = None,
) -> dict[str, Any]:
    """Call one tool, unless Beatra recently refused it for insufficient
    credits: then answer from the hold on this computer and send nothing, so a
    batch loop stops reaching Beatra after its first refusal."""

    resolved_state_dir = state_dir or Path.home() / ".beatra"
    observed = time.time() if now is None else now
    key = _balance_hold_key(resolved_state_dir)
    try:
        hold = _read_balance_holds(resolved_state_dir, observed).get(key, {}).get(tool_name) if key else None
    except Exception:
        # A record nobody can read is no hold: it must never stop a call.
        hold = None
    if hold is not None and (not recheck_balance or hold.get("rechecked") is True):
        return _held_result(tool_name, hold)
    session = _session_with_registration(state_dir=resolved_state_dir, post_json=post_json)
    result = session.request(2, "tools/call", {"name": tool_name, "arguments": arguments})
    if key:
        _note_balance_outcome(
            resolved_state_dir, key, tool_name, result, rechecked=hold is not None, now=observed
        )
    return result


def _read_tool_arguments() -> dict[str, Any]:
    try:
        arguments = json.load(os.sys.stdin)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Tool arguments on stdin must be one JSON object") from exc
    if not isinstance(arguments, dict):
        raise RuntimeError("Tool arguments on stdin must be one JSON object")
    return arguments


def _run_command(
    command: str,
    tool_name: str | None = None,
    arguments: dict[str, Any] | None = None,
    *,
    recheck_balance: bool = False,
) -> dict[str, Any]:
    if command == "tools":
        session = _session_with_registration(
            state_dir=Path.home() / ".beatra",
            post_json=_default_post_json,
        )
        return session.request(2, "tools/list", {})
    if arguments is None:
        arguments = _read_tool_arguments()
    assert tool_name is not None
    return call_tool(
        tool_name,
        arguments,
        state_dir=Path.home() / ".beatra",
        post_json=_default_post_json,
        recheck_balance=recheck_balance,
    )


CollectApproval = Callable[[Path], tuple[str, str | None]]


def _default_collect_approval(state_dir: Path) -> tuple[str, str | None]:
    """The helper's one-check collection, when this package has it."""

    import authorize  # the package's own helper, beside this file

    collect = getattr(authorize, "collect_saved_approval", None)
    if collect is None:
        return "none", None
    return collect(state_dir)


def _connect_waiting_approval(
    state_dir: Path,
    collect: CollectApproval | None = None,
) -> tuple[str, str | None]:
    """Before giving up on a call with no working credential: an approval the
    user already gave on this computer may be waiting to be collected (the
    agent was stopped while they selected Allow). One quick check; anything
    unexpected reads as nothing waiting, so the call fails as it always did."""

    try:
        outcome, link = (collect or _default_collect_approval)(state_dir)
    except Exception:
        return "none", None
    if outcome not in {"collected", "pending", "unreachable", "none"}:
        return "none", None
    return outcome, link


def _with_waiting_approval(
    operation: Callable[[], T],
    *,
    state_dir: Path,
    collect: CollectApproval | None = None,
) -> T:
    """Run one command; if it has no working credential, collect an approval
    that is waiting and run it once more."""

    try:
        return operation()
    except (AuthenticationRequired, CredentialsMissing) as exc:
        outcome, link = _connect_waiting_approval(state_dir, collect)
        if outcome == "collected":
            return operation()
        if outcome == "pending" and link:
            raise AuthenticationRequired(
                f"{AUTH_REQUIRED_CODE}: Beatra is waiting for the user to select Allow on "
                f"the approval page: {link}\nShow this link to the user if you have not "
                "already, then run `python3 scripts/authorize.py`: it continues this same "
                "approval and waits for Allow."
            ) from exc
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Call Beatra through Streamable HTTP")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("verify", help="Run the non-billable connection check")
    subparsers.add_parser("tools", help="List available Beatra tools")
    call = subparsers.add_parser("call", help="Call one tool with a JSON object on stdin")
    call.add_argument("tool_name")
    call.add_argument(
        "--recheck-balance",
        action="store_true",
        help="Send this call once although Beatra recently refused this tool for insufficient credits",
    )
    local_upload = subparsers.add_parser(
        "upload",
        help="Upload one local regular file and print its artifact reference",
    )
    local_upload.add_argument("path", type=Path)
    local_upload.add_argument(
        "--mime-type",
        required=True,
        help="Exact media MIME type, such as image/png, audio/mpeg, or video/mp4",
    )
    update = subparsers.add_parser(
        "update",
        help="Show whether the store or tool you installed from has a newer version",
    )
    update.add_argument(
        "--check",
        action="store_true",
        help="Same as update: report only; this client never changes its own files",
    )
    network = subparsers.add_parser("network", help="Show or choose the Beatra network this computer uses")
    network.add_argument(
        "--use",
        choices=("cn", "ai", "auto"),
        help="Keep the mainland China (cn) or international (ai) network until --use auto",
    )
    source = subparsers.add_parser(
        "install-source",
        help="Record where this Skill was installed from, when the conversation shows it",
    )
    source.add_argument("--guess", required=True, choices=GUESSABLE_SOURCES)
    args = parser.parse_args()
    try:
        state_dir = Path.home() / ".beatra"
        # One route decision per process, before the version check and any
        # request (spec §5.2).
        resolve_route(state_dir)
        if args.command == "update":
            print(update_status(state_dir=state_dir))
        elif args.command == "network":
            _network_command(args.use, state_dir)
        elif args.command == "install-source":
            try:
                recorded = guess_install_source(args.guess, state_dir=state_dir)
            except OSError as exc:
                raise RuntimeError(f"Could not save the install source: {exc}") from exc
            if (recorded["value"], recorded["basis"]) == (args.guess, "inferred"):
                print(f"Recorded where this Skill was installed from: {args.guess}.")
            else:
                print(f"Kept the recorded install source: {recorded['value']} ({recorded['basis']}).")
        else:
            maybe_notify_update(state_dir=state_dir)
        if args.command == "verify":
            _with_waiting_approval(verify, state_dir=state_dir)
        elif args.command == "upload":
            result = _with_waiting_approval(
                lambda: upload(args.path, mime_type=args.mime_type),
                state_dir=state_dir,
            )
            print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        elif args.command in {"tools", "call"}:
            # Read once: a call retried after collecting an approval reuses them.
            arguments = _read_tool_arguments() if args.command == "call" else None
            result = _with_waiting_approval(
                lambda: _run_command(
                    args.command,
                    getattr(args, "tool_name", None),
                    arguments,
                    recheck_balance=getattr(args, "recheck_balance", False),
                ),
                state_dir=state_dir,
            )
            print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
            if failure := _tool_failure_message(result):
                print(failure, file=os.sys.stderr)
                return 1
    except AuthenticationRequired as exc:
        print(str(exc), file=os.sys.stderr)
        return 1
    except RuntimeError as exc:
        print(str(exc), file=os.sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    # authorize.py's `import mcp_client` must get this running module, not run
    # a second copy that cannot see the route this process decided (one host
    # per process, spec §5.5).
    os.sys.modules["mcp_client"] = os.sys.modules[__name__]
    raise SystemExit(main())
