#!/usr/bin/env python3
"""Authorize one Beatra Skill package without a local callback listener."""

from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import secrets
import signal
import socket
import stat
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import webbrowser
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUTHORIZATION_ORIGIN = "https://api.beatra.ai"
MCP_URL = "https://mcp.beatra.ai/mcp"
DEVICE_AUTHORIZATION_URL = f"{AUTHORIZATION_ORIGIN}/oauth/device_authorization"
TOKEN_URL = f"{AUTHORIZATION_ORIGIN}/oauth/token"
PACKAGE_SLUG = "ai-logo-maker"
PACKAGE_DISPLAY_NAME = "AI Logo Maker"
PACKAGE_VERSION = "0.2.0"
CLIENT_ID = f"beatra-skill-{PACKAGE_SLUG}"
GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"
SCOPE = (
    "mcp:tools artifacts:write images:generate videos:generate music:generate "
    "speech:generate voices:read voices:write wallet:spend tasks:read artifacts:read tasks:cancel"
)
HTTP_USER_AGENT = f"Beatra-Skill/{PACKAGE_SLUG}/{PACKAGE_VERSION}"
POLL_SECONDS = 5
_PLATFORM_VALUE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
# How long Beatra keeps an approval open for a helper that does not say how
# long it keeps checking: every helper released before `max_poll_seconds`.
DEFAULT_APPROVAL_SECONDS = 15 * 60
# The longest this helper keeps one approval open. Beatra grants this only to
# a helper that declares it (`max_poll_seconds` below); the approval's own
# `expires_in` still decides, so a server that grants less is followed.
MAX_WAIT_SECONDS = 60 * 60
# This helper keeps its device code and comes back for an approval later (the
# next run, or mcp_client before any call). Beatra then tells it how to wait
# (`beatra_wait_policy`) and whether its approval page has been opened.
CLIENT_FEATURES = "collect_later"
# One run's foreground wait, and when a run whose page was never opened hands
# the link back, when Beatra sends no policy (a server older than the policy,
# or an approval an older helper opened): the long wait every helper before
# 09-23 had, with the link surfaced early for hosts that show output late.
DEFAULT_RUN_SECONDS = 900
DEFAULT_EARLY_RETURN_SECONDS = 60
# A run this short returns before most users finish signing in: its agent is
# told to run it again at once.
SHORT_RUN_SECONDS = 120
# How often a long run repeats the link, for hosts that show only the tail.
PROGRESS_SECONDS = 120
# How long a run waits for another run that is creating an approval right now.
LOCK_WAIT_SECONDS = 20
# A run that has not heard from Beatra for this long hands back to its agent.
UNREACHABLE_HAND_BACK_SECONDS = 60
# slow_down backs polling off by 5 s each time; two commands checking the same
# code would otherwise push each other far past the pace an Allow needs.
MAX_POLL_INTERVAL_SECONDS = 15
_UTC = timezone.utc  # noqa: UP017 -- datetime.UTC is unavailable on Python 3.10.

PostForm = Callable[[str, dict[str, str]], tuple[int, dict[str, Any]]]
CredentialProbe = Callable[[Path], bool]
AUTH_REQUIRED_CODE = "BEATRA_AUTH_REQUIRED"
AUTH_REQUIRED_MESSAGE = (
    f"{AUTH_REQUIRED_CODE}: Beatra authorization is no longer valid. Run "
    "`python3 scripts/authorize.py` again and follow its output "
    'until it prints "Beatra is ready".'
)
AUTH_IN_PROGRESS_CODE = "BEATRA_AUTH_IN_PROGRESS"
AUTH_IN_PROGRESS_MESSAGE = (
    f"{AUTH_IN_PROGRESS_CODE}: Another Beatra authorization is being started on this "
    "computer right now. Run this same command again in a moment; it continues that "
    "approval instead of starting a second one."
)
AUTH_PENDING_CODE = "BEATRA_AUTH_PENDING"
# Exit status of a run that stopped at its --wait-seconds budget while the user
# has not selected Allow yet: not done, not failed.
EXIT_PENDING = 3
WAIT_SECONDS_MIN = 30
WAIT_SECONDS_MAX = 900
# Locks without a heartbeat come only from helpers released before it, which
# never ran past their 15-minute approval; this is their age limit. It stays
# fixed however long this helper may keep an approval open.
LEGACY_LOCK_TTL_SECONDS = DEFAULT_APPROVAL_SECONDS + 120
# A live helper refreshes its lock from a background thread, whatever the main
# flow is blocked on (a request, a slow_down wait, the browser opening). A lock
# nobody refreshed for the stale window belongs to a helper the agent killed;
# the next run takes it over instead of waiting out the TTL.
AUTH_LOCK_HEARTBEAT_SECONDS = 10
AUTH_LOCK_HEARTBEAT_STALE_SECONDS = 90
# An approval given just before the code expired stays redeemable this long.
REDEEM_GRACE_SECONDS = 60
# A saved approval that lapsed this recently was still being continued by
# reruns; report the expiry instead of silently opening yet another page.
EXPIRED_NOTICE_SECONDS = 600
DECLINED_MESSAGE = (
    "Beatra authorization stopped (access_denied). If Allow was not declined on "
    "purpose, run this same command again for a new approval page."
)
EXPIRED_MESSAGE = (
    "Beatra authorization stopped (expired_token): the approval page expired before "
    "Allow was selected. If the user still wants to connect, run this same command "
    "again for a new approval page."
)
# Polls answer in milliseconds. A short timeout keeps the retry after a lost
# response well inside the server's 120 s re-delivery window for an issued token.
POLL_TIMEOUT_SECONDS = 15
PENDING_AUTHORIZATION_FILE = "pending_authorization.json"
_CLIENT_ID_VALUE = re.compile(r"beatra-skill-[a-z0-9][a-z0-9-]{0,63}\Z")
UNREACHABLE_MESSAGE = "Beatra authorization service is unreachable"
_START_ERRORS = {
    "invalid_client",
    "invalid_request",
    "invalid_scope",
    "invalid_target",
    "server_error",
    "temporarily_unavailable",
}
_TERMINAL_POLL_ERRORS = {
    "access_denied",
    "expired_token",
    "invalid_client",
    "invalid_grant",
    "invalid_request",
    "invalid_target",
}
# The server answers these while it is briefly unable to decide, including the
# moment an approval lands between two polls; polling again completes the flow.
_TRANSIENT_POLL_ERRORS = {"server_error", "temporarily_unavailable"}


class _TransientAuthorizationError(RuntimeError):
    """The authorization service could not be reached or answered with a gateway error."""


class _ApprovalPending(Exception):
    """This run ended before the user selected Allow: its time budget ran out,
    its approval page was never opened (so the agent must show the link), or
    the host stopped it."""

    def __init__(
        self,
        verification_url: str,
        *,
        answered: bool = True,
        minutes_left: int = 1,
        legacy: bool = False,
        connects_later: bool = False,
        stopped: bool = False,
        unopened: bool = False,
    ) -> None:
        super().__init__(verification_url)
        self.verification_url = verification_url
        self.answered = answered
        self.minutes_left = minutes_left
        self.legacy = legacy
        self.connects_later = connects_later
        self.stopped = stopped
        self.unopened = unopened

    def instructions(self) -> str:
        if not self.answered:
            # Say what actually happened: asking the user to approve again
            # would be wrong while the approval may already be given.
            return (
                f"{AUTH_PENDING_CODE}: Beatra could not be reached during this run, so it is "
                "not known yet whether the user selected Allow. The approval page stays "
                f"valid for about {self.minutes_left} more minutes: {self.verification_url}\n"
                "Tell the user the connection to Beatra is being retried and that they do "
                "not need to approve again. Then run this same command again; it continues "
                "this same approval. Repeat until it prints \"Beatra is ready\"."
            )
        if self.legacy:
            # Short runs: a session still following the 09-23 instructions
            # (--wait-seconds), or Beatra's short-run switch.
            return (
                f"{AUTH_PENDING_CODE}: The user has not selected Allow yet. "
                f"Approval page: {self.verification_url}\n"
                "Share this link with the user if you have not already (it may "
                "already be open in their browser). Then run this same command "
                "again right away: it continues this same approval, so the user "
                "never approves twice. Repeat until it prints \"Beatra is ready\". "
                "Signing in or creating an account can take a few minutes; keep "
                "running it until then."
            )
        if self.unopened:
            return (
                f"{AUTH_PENDING_CODE}: The approval page has not been opened yet. "
                f"Show this link to the user in the chat now: {self.verification_url}\n"
                "Then run this same command again: it continues this same approval, so "
                "the user never approves twice, and waits for Allow."
                + (
                    " If the user approves while nothing is running, Beatra connects "
                    "automatically the next time you use it."
                    if self.connects_later
                    else ""
                )
            )
        lead = "This run was stopped" if self.stopped else "The user has not selected Allow yet"
        later = (
            " If the user approves while nothing is running, Beatra connects "
            "automatically the next time you use it - they never approve twice."
            if self.connects_later
            else ""
        )
        return (
            f"{AUTH_PENDING_CODE}: {lead}. Approval page: {self.verification_url}\n"
            "Show this link to the user in the chat if you have not already (it may "
            "already be open in their browser). Then run this same command again: "
            "it continues this same approval, so the user never approves twice, and "
            "waits for Allow." + later
        )


class _Stopped(BaseException):
    """The host asked this run to stop (SIGINT, SIGTERM, SIGHUP)."""


class _AuthorizationInProgress(RuntimeError):
    """Another run is creating an approval on this computer right now."""


class _RejectRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        _request: urllib.request.Request,
        _file_pointer: Any,
        code: int,
        _message: str,
        _headers: Any,
        _new_url: str,
    ) -> None:
        raise RuntimeError(f"Beatra authorization refused HTTP redirect ({code})")


def _default_post_form(url: str, fields: dict[str, str], *, timeout: float | None = None) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(fields).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": HTTP_USER_AGENT,
        },
        method="POST",
    )
    opener = urllib.request.build_opener(_RejectRedirectHandler())
    try:
        if timeout is None:
            timeout = POLL_TIMEOUT_SECONDS if url == TOKEN_URL else 30
        with opener.open(request, timeout=timeout) as response:
            status = int(response.status)
            raw = response.read()
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        try:
            raw = exc.read()
        except (OSError, http.client.HTTPException) as read_error:
            raise _TransientAuthorizationError(UNREACHABLE_MESSAGE) from read_error
    except (OSError, http.client.HTTPException) as exc:
        # URLError covers DNS, refused connections and TLS handshakes; a
        # timeout or reset while waiting for the response surfaces unwrapped.
        raise _TransientAuthorizationError(UNREACHABLE_MESSAGE) from exc
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        failure = _TransientAuthorizationError if status >= 500 or status == 429 else RuntimeError
        raise failure(f"Beatra authorization returned HTTP {status}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Beatra authorization returned HTTP {status}")
    return status, payload


def _private_directory(path: Path) -> None:
    # POSIX gets explicit 700/600. On Windows the state directory lives under
    # the user profile, whose default ACL is already private to the user —
    # the same posture as gh/aws/gcloud credential stores. The former custom
    # DACL ceremony was dropped deliberately: its command patterns read as
    # hostile to agent safety policies and endpoint security, failing installs
    # while adding no protection an elevated administrator could not bypass.
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name == "posix":
        path.chmod(0o700)


def _restrict_file(path: Path) -> None:
    if os.name == "posix":
        path.chmod(0o600)


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    _private_directory(path.parent)
    temporary = path.parent / f".{path.name}.{secrets.token_hex(8)}.tmp"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        _restrict_file(temporary)
        os.replace(temporary, path)
        _restrict_file(path)
        if os.name == "posix":
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def _installation_reference(state_dir: Path) -> str:
    path = state_dir / "installation.json"
    if path.exists():
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            reference = value["external_installation_ref"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Beatra installation state is invalid") from exc
        if not isinstance(reference, str) or not reference.startswith("beatra:"):
            raise RuntimeError("Beatra installation state is invalid")
        _restrict_file(path)
        return reference

    reference = f"beatra:{uuid.uuid4()}"
    _atomic_json(
        path,
        {
            "schema_version": 1,
            "external_installation_ref": reference,
            "created_at": datetime.now(_UTC).isoformat(),
        },
    )
    return reference


def _required_string(payload: dict[str, Any], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value:
        raise RuntimeError("Beatra authorization response is incomplete")
    return value


def _positive_int(payload: dict[str, Any], name: str, default: int) -> int:
    value = payload.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return default
    return value


def _validate_verification_url(value: str, *, user_code: str) -> str:
    expected = f"{AUTHORIZATION_ORIGIN}/device#code={urllib.parse.quote(user_code, safe='-')}"
    if value != expected:
        raise RuntimeError("Beatra authorization verification URL is invalid")
    return value


def _existing_credential(state_dir: Path) -> Path | None:
    path = state_dir / "credentials.json"
    try:
        path_stat = os.lstat(path)
        if not stat.S_ISREG(path_stat.st_mode):
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, json.JSONDecodeError):
        return None
    required_strings = (
        "access_token",
        "credential_id",
        "installation_id",
        "scope",
        "authorized_at",
    )
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != 1
        or value.get("mcp_url") != MCP_URL
        or value.get("token_type") != "Bearer"
        or any(not isinstance(value.get(name), str) or not value[name] for name in required_strings)
        or set(value["scope"].split()) != set(SCOPE.split())
    ):
        return None
    _restrict_file(path)
    return path


def _default_probe_credential(credential_path: Path) -> bool:
    import mcp_client

    try:
        mcp_client.verify(state_dir=credential_path.parent)
    except mcp_client.AuthenticationRequired:
        return False
    return True


def _read_authorization_lock(path: Path) -> tuple[dict[str, Any], tuple[int, int], float] | None:
    try:
        path_stat = os.lstat(path)
        if not stat.S_ISREG(path_stat.st_mode):
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, json.JSONDecodeError):
        return None
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != 1
        or not isinstance(value.get("owner_nonce"), str)
        or not value["owner_nonce"]
        or isinstance(value.get("created_at"), bool)
        or not isinstance(value.get("created_at"), (int, float))
    ):
        return None
    return value, (path_stat.st_dev, path_stat.st_ino), path_stat.st_mtime


def _lock_abandoned(payload: dict[str, Any], *, touched_at: float, now: float) -> bool:
    """A heartbeat lock is judged by its heartbeat alone: a live helper may run
    longer than any TTL (a resumed code, then a fresh one). Locks from older
    helpers, which never heartbeat, keep their fixed age limit."""

    if payload.get("heartbeat") is True:
        return now - touched_at > AUTH_LOCK_HEARTBEAT_STALE_SECONDS
    return now - float(payload["created_at"]) > LEGACY_LOCK_TTL_SECONDS


def _unreadable_lock_abandoned(path: Path, *, now: float) -> bool:
    try:
        path_stat = os.lstat(path)
    except OSError:
        return True
    return stat.S_ISREG(path_stat.st_mode) and now - path_stat.st_mtime > LEGACY_LOCK_TTL_SECONDS


def _touch_lock(path: Path, when: float) -> None:
    with suppress(OSError):
        os.utime(path, (when, when))


def _same_file_identity(path: Path, identity: tuple[int, int]) -> bool:
    try:
        current = os.lstat(path)
    except OSError:
        return False
    return stat.S_ISREG(current.st_mode) and (current.st_dev, current.st_ino) == identity


def _create_lock(
    path: Path,
    *,
    owner_nonce: str,
    wall_time: Callable[[], float],
) -> tuple[tuple[int, int], float]:
    """Create and write the lock file; (its identity, when it was written)."""

    descriptor = -1
    owned_identity: tuple[int, int] | None = None
    for attempt in range(2):
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            owned_stat = os.fstat(descriptor)
            owned_identity = (owned_stat.st_dev, owned_stat.st_ino)
            break
        except FileExistsError as exc:
            existing = _read_authorization_lock(path)
            if existing is None:
                # Unreadable (a helper died mid-write, or another tool's file):
                # stale once older than any helper ever held a lock, so it
                # cannot block every future authorization.
                if not _unreadable_lock_abandoned(path, now=wall_time()):
                    raise _AuthorizationInProgress(AUTH_IN_PROGRESS_MESSAGE) from exc
                with suppress(OSError):
                    path.unlink()
                if attempt == 1:
                    raise _AuthorizationInProgress(AUTH_IN_PROGRESS_MESSAGE) from exc
                continue
            payload, identity, touched_at = existing
            if not _lock_abandoned(payload, touched_at=touched_at, now=wall_time()) or not _same_file_identity(
                path, identity
            ):
                raise _AuthorizationInProgress(AUTH_IN_PROGRESS_MESSAGE) from exc
            with suppress(OSError):
                path.unlink()
            if attempt == 1:
                raise _AuthorizationInProgress(AUTH_IN_PROGRESS_MESSAGE) from exc
    if descriptor < 0 or owned_identity is None:
        raise _AuthorizationInProgress(AUTH_IN_PROGRESS_MESSAGE)
    try:
        created_at = wall_time()
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            descriptor = -1
            json.dump(
                {
                    "schema_version": 1,
                    "owner_nonce": owner_nonce,
                    "created_at": created_at,
                    "heartbeat": True,
                },
                stream,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        _restrict_file(path)
        _touch_lock(path, created_at)
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        if _same_file_identity(path, owned_identity):
            with suppress(OSError):
                path.unlink()
        raise
    return owned_identity, created_at


@contextmanager
def _device_authorization_lock(
    state_dir: Path,
    *,
    wall_time: Callable[[], float],
    lock_nonce: Callable[[], str],
) -> Iterator[None]:
    path = state_dir / ".authorize.lock"
    owner_nonce = lock_nonce()
    if not isinstance(owner_nonce, str) or not owner_nonce:
        raise RuntimeError("Beatra authorization lock owner is invalid")

    # A stop between creating the lock file and writing it would leave an
    # empty lock that older helpers treat as busy: it waits until written.
    with _SIGNALS.deferred():
        owned_identity, _created_at = _create_lock(path, owner_nonce=owner_nonce, wall_time=wall_time)
    try:
        if _SIGNALS.requested:
            _SIGNALS.requested = False
            raise _Stopped()
        stopped = threading.Event()

        def heartbeat() -> None:
            while not stopped.wait(AUTH_LOCK_HEARTBEAT_SECONDS):
                if _same_file_identity(path, owned_identity):
                    _touch_lock(path, wall_time())

        beater = threading.Thread(target=heartbeat, name="beatra-authorize-heartbeat", daemon=True)
        beater.start()
        try:
            yield
        finally:
            stopped.set()
            beater.join(timeout=1)
    finally:
        with _SIGNALS.deferred():
            if _same_file_identity(path, owned_identity):
                existing = _read_authorization_lock(path)
                if existing is None or existing[0]["owner_nonce"] == owner_nonce:
                    with suppress(OSError):
                        path.unlink()


def _safe_protocol_error(value: Any, allowed: set[str]) -> str:
    return value if isinstance(value, str) and value in allowed else "request_failed"


def detect_host_platform(explicit: str | None = None) -> str:
    """The agent environment this process runs inside (docs/device-model.md).

    Order: explicit agent self-report > environment signatures > unknown.
    Detection reads the process environment only — nothing else runs,
    nothing reaches the network.
    """
    if explicit:
        candidate = explicit.strip().lower().replace(" ", "-")
        if _PLATFORM_VALUE.fullmatch(candidate):
            return candidate
    env = os.environ
    if env.get("CLAUDECODE") == "1" or "CLAUDE_CODE_ENTRYPOINT" in env:
        return "claude-code"
    if any(key.startswith("CODEX_") for key in env):
        return "codex"
    ai_agent = env.get("AI_AGENT", "").lower()
    matched = re.match(r"([a-z0-9-]+)_", ai_agent)
    if matched and _PLATFORM_VALUE.fullmatch(matched.group(1)):
        return matched.group(1)
    return "unknown"


def device_display_name() -> str | None:
    """A hostname the user will recognise in the console device list."""
    try:
        name = socket.gethostname().strip()
    except OSError:
        return None
    if not name or not name.isprintable():
        return None
    return name[:120]


def write_host_config(state_dir: Path, *, platform: str, device_name: str | None) -> None:
    """Persist detection results so mcp_client never re-detects per request
    and still has a truth source when its own env detection comes up empty.
    Best-effort: config failure must never block authorization."""
    try:
        payload: dict[str, Any] = {"platform": platform}
        if device_name:
            payload["device_name"] = device_name
        (state_dir / "host.json").write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass


def _own_skill_root() -> Path | None:
    """The installed package root this script runs from, when knowable."""
    try:
        return Path(__file__).resolve().parent.parent
    except NameError:
        return None


def record_skill_installation(
    state_dir: Path,
    *,
    platform: str,
    skill_root: Path | None = None,
) -> None:
    """Upsert this package into the device-local skill inventory.

    ~/.beatra/skills.json is the device's own answer to "which skills still
    use this connection". The uninstall flow may only revoke the shared
    credential once this inventory says nothing else is left, so every
    authorization records its package here. Best-effort: inventory failure
    must never block authorization.
    """

    try:
        root = skill_root or _own_skill_root()
        if root is None:
            return
        resolved = str(Path(root).expanduser().resolve())
        path = state_dir / "skills.json"
        entries: list[dict[str, Any]] = []
        if path.exists():
            value = json.loads(path.read_text(encoding="utf-8"))
            loaded = value.get("skills") if isinstance(value, dict) else None
            if isinstance(loaded, list):
                entries = [entry for entry in loaded if isinstance(entry, dict)]
        entries = [
            entry
            for entry in entries
            if not (
                entry.get("slug") == PACKAGE_SLUG and entry.get("install_path") == resolved
            )
        ]
        entries.append(
            {
                "slug": PACKAGE_SLUG,
                "platform": platform,
                "install_path": resolved,
                "recorded_at": datetime.now(_UTC).isoformat(),
            }
        )
        _atomic_json(path, {"schema_version": 1, "skills": entries})
    except (OSError, TypeError, ValueError):
        pass


def _pending_path(state_dir: Path) -> Path:
    return state_dir / PENDING_AUTHORIZATION_FILE


def _discard_pending(state_dir: Path, *, device_code: str | None = None) -> None:
    """Remove the saved approval; with a device code, only when it is still the
    one saved, so a helper never deletes an approval another run opened."""

    path = _pending_path(state_dir)
    if device_code is not None:
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, TypeError, json.JSONDecodeError):
            return
        if not isinstance(saved, dict) or saved.get("device_code") != device_code:
            return
    with suppress(OSError):
        path.unlink(missing_ok=True)


def _save_pending(state_dir: Path, pending: dict[str, Any]) -> None:
    """Remember the open approval so a helper the agent stopped can be rerun
    and finish it, instead of asking the user to approve a second time.

    One file, readable by every helper since 09-23: their fields keep their
    meaning (`expires_at` is when the approval page closes) and the fields this
    helper adds beside them are carried along untouched by the older ones. The
    device code is protected exactly like the credential."""
    _atomic_json(
        _pending_path(state_dir),
        {"schema_version": 1, **{key: value for key, value in pending.items() if key != "schema_version"}},
    )


def _collect_until(value: dict[str, Any]) -> float:
    """Until when the saved approval can still be collected. Beatra keeps an
    approval for its collect window after Allow; a code saved without one (an
    older helper, or the window off) lapses with its page as before."""

    page_closes = float(value["expires_at"]) + REDEEM_GRACE_SECONDS
    collect_until = value.get("collect_until")
    if isinstance(collect_until, bool) or not isinstance(collect_until, (int, float)):
        return page_closes
    return max(page_closes, float(collect_until))


def _load_pending(state_dir: Path, *, wall_time: Callable[[], float]) -> tuple[dict[str, Any] | None, bool]:
    """The saved approval this run should continue, and whether one lapsed
    moments ago (then a replacement page is shown, not opened, so repeated
    runs never keep opening new tabs)."""

    path = _pending_path(state_dir)
    try:
        path_stat = os.lstat(path)
        if not stat.S_ISREG(path_stat.st_mode):
            return None, False
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, json.JSONDecodeError):
        return None, False
    try:
        # Every Beatra Skill package shares ~/.beatra and the one credential, so
        # an approval opened by another package's helper is finished as is,
        # polling with the client id it was created for.
        if (
            not isinstance(value, dict)
            or value.get("schema_version") != 1
            or not isinstance(value.get("client_id"), str)
            or not _CLIENT_ID_VALUE.fullmatch(value["client_id"])
            or not isinstance(value.get("device_code"), str)
            or not value["device_code"]
            or isinstance(value.get("interval"), bool)
            or not isinstance(value.get("interval"), int)
            or value["interval"] <= 0
            or isinstance(value.get("expires_at"), bool)
            or not isinstance(value.get("expires_at"), (int, float))
        ):
            raise ValueError("pending authorization is invalid")
        _validate_verification_url(
            str(value.get("verification_uri_complete")),
            user_code=str(value.get("user_code")),
        )
    except (RuntimeError, ValueError):
        _discard_pending(state_dir)
        return None, False
    now = wall_time()
    if now >= _collect_until(value):
        _discard_pending(state_dir, device_code=str(value["device_code"]))
        return None, now < float(value["expires_at"]) + EXPIRED_NOTICE_SECONDS
    _restrict_file(path)
    return value, False


def _policy_int(policy: Any, name: str, *, maximum: int) -> int | None:
    value = policy.get(name) if isinstance(policy, dict) else None
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        return None
    return value


def _start_authorization(
    *,
    state_dir: Path,
    host_platform: str,
    device_name: str | None,
    post_form: PostForm,
    wall_time: Callable[[], float],
) -> dict[str, Any]:
    external_reference = _installation_reference(state_dir)
    form: dict[str, str] = {
        "client_id": CLIENT_ID,
        "resource": MCP_URL,
        "scope": SCOPE,
        "platform": host_platform,
        "client_name": PACKAGE_DISPLAY_NAME,
        "external_installation_ref": external_reference,
        "package_version": PACKAGE_VERSION,
        "package_slug": PACKAGE_SLUG,
        # This helper keeps checking an approval for up to MAX_WAIT_SECONDS;
        # Beatra keeps it open that long only when told so.
        "max_poll_seconds": str(MAX_WAIT_SECONDS),
        "client_features": CLIENT_FEATURES,
    }
    if device_name:
        form["device_name"] = device_name
    status, created = post_form(DEVICE_AUTHORIZATION_URL, form)
    if status != 200:
        code = _safe_protocol_error(created.get("error"), _START_ERRORS)
        raise RuntimeError(f"Beatra authorization could not start ({code})")

    device_code = _required_string(created, "device_code")
    user_code = _required_string(created, "user_code")
    verification_url = _validate_verification_url(
        _required_string(created, "verification_uri_complete"),
        user_code=user_code,
    )
    interval = max(POLL_SECONDS, _positive_int(created, "interval", POLL_SECONDS))
    server_lifetime = _positive_int(created, "expires_in", DEFAULT_APPROVAL_SECONDS)
    now = wall_time()
    expires_at = now + min(server_lifetime, MAX_WAIT_SECONDS)
    pending: dict[str, Any] = {
        "client_id": CLIENT_ID,
        "device_code": device_code,
        "user_code": user_code,
        "verification_uri_complete": verification_url,
        "interval": interval,
        "expires_at": expires_at,
        "created_at": now,
    }
    policy = created.get("beatra_wait_policy")
    run_seconds = _policy_int(policy, "run_seconds", maximum=WAIT_SECONDS_MAX)
    if run_seconds:
        pending["run_seconds"] = max(WAIT_SECONDS_MIN, run_seconds)
        early = _policy_int(policy, "early_return_seconds", maximum=WAIT_SECONDS_MAX)
        pending["early_return_seconds"] = early or 0
        window = _policy_int(policy, "collect_window_seconds", maximum=90 * 24 * 60 * 60)
        if window:
            # Beatra keeps an approval collectable this long after Allow; Allow
            # is possible until the page closes.
            pending["collect_until"] = expires_at + REDEEM_GRACE_SECONDS + window
    if created.get("beatra_approved") is True:
        # This device already approved moments ago and nothing collected it:
        # Beatra carried that approval over to this code. Nothing to open.
        pending["opened"] = True
        pending["approved_on_create"] = True
    _save_pending(state_dir, pending)
    return pending


def _mark_opened(state_dir: Path, pending: dict[str, Any]) -> None:
    if not pending.get("opened"):
        pending["opened"] = True
        _save_pending(state_dir, pending)


def _say(text: str) -> None:
    """Print for the agent; output trouble never stops the approval.

    A host that closed the pipe (or cannot encode) loses the text, not the
    run: output goes to the null device from then on and polling continues."""

    try:
        print(text, flush=True)
    except (OSError, ValueError):
        _silence_stdout()


def _silence_stdout() -> None:
    with suppress(OSError, ValueError):
        sys.stdout = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115 -- replaces stdout for the process


def _announce(
    verification_url: str,
    open_browser: Callable[[str], bool],
    *,
    open_page: bool = True,
) -> bool:
    """Show the link; open the page when asked. False when a page was meant to
    open and could not, so the agent must show the link right away."""

    # The link fragment already carries the approval code, so the page
    # verifies it by itself. Never announce the code separately: the approval
    # page does not display it and the user never types or compares it.
    _say(f"Open this Beatra approval page: {verification_url}")
    _say(
        "If the browser shows Beatra sign-in first, sign in or create the "
        "account there; the approval page continues automatically. The only "
        "decision on it is selecting Allow."
    )
    _say("Beatra detects Allow by itself - no chat confirmation is needed from the user.")
    if not open_page:
        return True
    try:
        return bool(open_browser(verification_url))
    except Exception:
        return False


class _SignalGuard:
    """Delays a stop request while the credential is being written."""

    def __init__(self) -> None:
        self.deferring = False
        self.requested = False

    def handle(self, _signum: int, _frame: Any) -> None:
        if self.deferring:
            self.requested = True
            return
        raise _Stopped()

    @contextmanager
    def deferred(self, *, then_stop: bool = False) -> Iterator[None]:
        """Hold a stop request until the block is done; with `then_stop`,
        honour it right after (a stop during a credential write is dropped:
        the credential is saved, and the run finishes in seconds)."""

        self.deferring = True
        try:
            yield
        finally:
            self.deferring = False
        if then_stop and self.requested:
            self.requested = False
            raise _Stopped()


_SIGNALS = _SignalGuard()


def _install_signal_handlers(handler: Any = None) -> None:
    for name in ("SIGINT", "SIGTERM", "SIGHUP"):
        number = getattr(signal, name, None)
        if number is None:
            continue
        with suppress(OSError, ValueError, RuntimeError):
            signal.signal(number, handler or _SIGNALS.handle)


def _save_credential(state_dir: Path, polled: dict[str, Any]) -> Path:
    """Write the credential Beatra issued, in the format every helper reads."""

    access_token = _required_string(polled, "access_token")
    if polled.get("token_type") != "Bearer":
        raise RuntimeError("Beatra authorization returned an unsupported token type")
    scope = _required_string(polled, "scope")
    if set(scope.split()) != set(SCOPE.split()):
        raise RuntimeError("Beatra authorization returned an unsupported scope")
    credential_path = state_dir / "credentials.json"
    with _SIGNALS.deferred():
        _atomic_json(
            credential_path,
            {
                "schema_version": 1,
                "mcp_url": MCP_URL,
                "token_type": "Bearer",
                "access_token": access_token,
                "credential_id": _required_string(polled, "credential_id"),
                "installation_id": _required_string(polled, "installation_id"),
                "scope": scope,
                "authorized_at": datetime.now(_UTC).isoformat(),
                "idle_expires_in": _positive_int(polled, "idle_expires_in", 15 * 24 * 60 * 60),
            },
        )
    return credential_path


def _poll_fields(pending: dict[str, Any]) -> dict[str, str]:
    return {
        "grant_type": GRANT_TYPE,
        "device_code": str(pending["device_code"]),
        "client_id": str(pending["client_id"]),
        "resource": MCP_URL,
    }


def _classify_poll(status: int, polled: dict[str, Any], unreachable: bool) -> str:
    """token / pending / slow_down / denied / expired / transient / failed:<code>."""

    if status == 200:
        return "token"
    error = polled.get("error") if isinstance(polled.get("error"), str) else None
    if unreachable or status >= 500 or (status == 429 and error != "slow_down") or error in _TRANSIENT_POLL_ERRORS:
        return "transient"
    if error == "authorization_pending":
        return "pending"
    if error == "slow_down":
        return "slow_down"
    if error == "access_denied":
        return "denied"
    if error == "expired_token":
        return "expired"
    return f"failed:{_safe_protocol_error(error, _TERMINAL_POLL_ERRORS)}"


def _minutes_left(pending: dict[str, Any], wall_time: Callable[[], float]) -> int:
    return max(1, int(float(pending["expires_at"]) - wall_time() + 59) // 60)


def _fresh_credential(state_dir: Path, *, since: float) -> Path | None:
    """A credential another process (mcp_client, another run) saved during
    this run: the approval was collected elsewhere."""

    credential_path = _existing_credential(state_dir)
    if credential_path is None:
        return None
    try:
        if os.stat(credential_path).st_mtime < since:
            return None
    except OSError:
        return None
    return credential_path


def _obtain_pending(
    *,
    state_dir: Path,
    host_platform: str,
    device_name: str | None,
    post_form: PostForm,
    sleep: Callable[[float], None],
    monotonic: Callable[[], float],
    wall_time: Callable[[], float],
    lock_nonce: Callable[[], str],
    renew: bool = False,
) -> tuple[dict[str, Any], bool]:
    """(approval, resumed). The lock is held only while an approval is
    created, never while waiting for Allow: any number of runs may poll the
    same saved code, which Beatra answers consistently.

    A saved approval whose page closed moments ago without Allow is reported
    instead of replaced (the user may have walked away; a new page opens when
    the command is run again). `renew` skips that check for a code this run
    already found over."""

    pending, lapsed = _load_pending(state_dir, wall_time=wall_time)
    if pending is not None:
        return pending, True
    if lapsed and not renew:
        raise RuntimeError(EXPIRED_MESSAGE)
    give_up = monotonic() + LOCK_WAIT_SECONDS
    while True:
        try:
            with _device_authorization_lock(state_dir, wall_time=wall_time, lock_nonce=lock_nonce):
                pending, _ = _load_pending(state_dir, wall_time=wall_time)
                if pending is not None:
                    return pending, True
                created = _start_authorization(
                    state_dir=state_dir,
                    host_platform=host_platform,
                    device_name=device_name,
                    post_form=post_form,
                    wall_time=wall_time,
                )
                return created, False
        except _AuthorizationInProgress:
            pending, _ = _load_pending(state_dir, wall_time=wall_time)
            if pending is not None:
                return pending, True
            if monotonic() >= give_up:
                raise
            sleep(2)


def _wait_for_credential(
    pending: dict[str, Any],
    *,
    resumed: bool,
    force: bool,
    state_dir: Path,
    host_platform: str,
    device_name: str | None,
    post_form: PostForm,
    probe_credential: CredentialProbe,
    open_browser: Callable[[str], bool],
    sleep: Callable[[float], None],
    monotonic: Callable[[], float],
    wall_time: Callable[[], float],
    lock_nonce: Callable[[], str],
    wait_seconds: float | None,
) -> Path:
    global _CURRENT_LINK
    legacy = wait_seconds is not None
    started_mono = monotonic()
    started_wall = wall_time()
    # Credential files carry real modification times, whatever clock is injected.
    started_real = time.time()
    rejected_credential_at: float | None = None
    renewed = False

    def budget_for(current: dict[str, Any]) -> float:
        if legacy:
            return float(wait_seconds or 0)
        run_seconds = current.get("run_seconds")
        if isinstance(run_seconds, bool) or not isinstance(run_seconds, int) or run_seconds <= 0:
            return float(DEFAULT_RUN_SECONDS)
        return float(run_seconds)

    def early_return_for(current: dict[str, Any]) -> float | None:
        if legacy:
            return None
        early = current.get("early_return_seconds")
        if "run_seconds" not in current:
            return float(DEFAULT_EARLY_RETURN_SECONDS)
        if isinstance(early, bool) or not isinstance(early, int) or early <= 0:
            return None
        return float(early)

    def connects_later(current: dict[str, Any]) -> bool:
        return _collect_until(current) > float(current["expires_at"]) + REDEEM_GRACE_SECONDS

    def show_new(current: dict[str, Any]) -> bool:
        """A code this run created: print its link at once and open its page.
        False when no page could open, so the agent must show the link now."""

        global _CURRENT_LINK
        _CURRENT_LINK = str(current["verification_uri_complete"])
        if current.get("approved_on_create"):
            _say("This computer's earlier approval carries over; connecting now.")
            return True
        opened = _announce(_CURRENT_LINK, open_browser, open_page=True)
        _mark_opened(state_dir, current)
        return opened

    def show_resumed(current: dict[str, Any]) -> None:
        """A saved code still waiting for Allow: its link again, and its page
        if no run managed to open it yet."""

        global _CURRENT_LINK
        _CURRENT_LINK = str(current["verification_uri_complete"])
        _say("Continuing the Beatra approval that is already open.")
        open_page = not current.get("opened")
        _announce(_CURRENT_LINK, open_browser, open_page=open_page)
        if open_page:
            _mark_opened(state_dir, current)

    if resumed:
        # Checked before anything is shown: it may already be approved (then
        # no page is needed at all) or over.
        _CURRENT_LINK = str(pending["verification_uri_complete"])
        browser_ok = True
        early_after: float | None = None
        wait_first = False
    else:
        browser_ok = show_new(pending)
        early_after = early_return_for(pending)
        # A code approved at creation is collected at once.
        wait_first = not pending.get("approved_on_create")
    budget = budget_for(pending)
    interval = int(pending["interval"])
    answered = False
    announced = not resumed
    page_opened: bool | None = None
    next_progress = started_mono + PROGRESS_SECONDS
    # When Beatra last answered this run: a run that cannot reach it (offline,
    # a sandbox without network) says so within a minute instead of waiting.
    last_answer = started_mono

    def pending_error(current: dict[str, Any]) -> _ApprovalPending:
        return _ApprovalPending(
            str(current["verification_uri_complete"]),
            answered=answered,
            minutes_left=_minutes_left(current, wall_time),
            # Short runs (the 09-23 shape, or Beatra's fallback switch) need the
            # agent to rerun at once, exactly as the 09-23 instructions said.
            legacy=legacy or budget_for(current) <= SHORT_RUN_SECONDS,
            connects_later=connects_later(current),
            unopened=page_opened is False,
        )

    while True:
        if wait_first:
            sleep(min(float(interval), max(0.0, budget - (monotonic() - started_mono))))
            wait_first = False
        elapsed = max(monotonic() - started_mono, wall_time() - started_wall)
        # Never start a poll that could outlast the run: the host's own timeout
        # sits just past it.
        if budget - elapsed < POLL_TIMEOUT_SECONDS:
            raise pending_error(pending)
        if not force and (collected := _fresh_credential(state_dir, since=started_real)):
            written_at = collected.stat().st_mtime
            if written_at != rejected_credential_at:
                _say("Beatra authorization was completed by another Beatra command.")
                if probe_credential(collected):
                    _discard_pending(state_dir, device_code=str(pending["device_code"]))
                    _say("Beatra is ready.")
                    return collected
                rejected_credential_at = written_at
        try:
            status, polled = post_form(TOKEN_URL, _poll_fields(pending))
            unreachable = False
        except _TransientAuthorizationError:
            # The poll may have reached the server and its answer been lost;
            # the next poll inside the re-delivery window recovers the token.
            status, polled, unreachable = 0, {}, True
        outcome = _classify_poll(status, polled, unreachable)
        if outcome == "token":
            credential_path = _save_credential(state_dir, polled)
            _discard_pending(state_dir, device_code=str(pending["device_code"]))
            _say("Beatra authorization saved to the private credential file.")
            if not probe_credential(credential_path):
                credential_path.unlink(missing_ok=True)
                raise RuntimeError(AUTH_REQUIRED_MESSAGE)
            _say("Beatra is ready.")
            return credential_path
        if outcome != "transient":
            answered = True
            last_answer = monotonic()
        elif not legacy and monotonic() - last_answer >= UNREACHABLE_HAND_BACK_SECONDS:
            answered = False
            raise pending_error(pending)
        if outcome == "denied":
            _discard_pending(state_dir, device_code=str(pending["device_code"]))
            # A decline ends the run: the user may have meant it, so a new
            # page opens only when the command is run again.
            raise RuntimeError(DECLINED_MESSAGE)
        if outcome == "expired" or outcome.startswith("failed:"):
            _discard_pending(state_dir, device_code=str(pending["device_code"]))
            lapsed_long_ago = wall_time() >= float(pending["expires_at"]) + EXPIRED_NOTICE_SECONDS
            if resumed and not renewed and (outcome != "expired" or lapsed_long_ago):
                # The saved code can no longer finish: it lapsed long ago (the
                # user is back for a new session) or cannot finish for another
                # reason. One fresh approval, opened as any new one.
                renewed = True
                pending, resumed = _obtain_pending(
                    state_dir=state_dir,
                    host_platform=host_platform,
                    device_name=device_name,
                    post_form=post_form,
                    sleep=sleep,
                    monotonic=monotonic,
                    wall_time=wall_time,
                    lock_nonce=lock_nonce,
                    renew=True,
                )
                if resumed:
                    announced = False
                    browser_ok, early_after, wait_first = True, None, False
                else:
                    announced = True
                    browser_ok = show_new(pending)
                    early_after = early_return_for(pending)
                    wait_first = not pending.get("approved_on_create")
                interval = int(pending["interval"])
                page_opened = None
                continue
            if outcome == "expired":
                # Lapsed moments ago without Allow: say so; running the command
                # again opens a new page.
                raise RuntimeError(EXPIRED_MESSAGE)
            raise RuntimeError(f"Beatra authorization stopped ({outcome.split(':', 1)[1]})")
        if outcome in {"pending", "slow_down"} and not announced:
            show_resumed(pending)
            announced = True
        if outcome == "pending" and isinstance(polled.get("page_opened"), bool):
            page_opened = bool(polled["page_opened"])
        if outcome == "slow_down":
            # Another command may be checking the same code; back off, but not
            # so far that an approval waits long to be noticed.
            interval = min(max(interval + 5, _positive_int(polled, "interval", interval)), MAX_POLL_INTERVAL_SECONDS)
        # The approval page was never opened: the agent must show the link, and
        # some hosts show nothing until the command ends. Hand it back now —
        # at once when no browser could open, after a minute otherwise.
        if (
            early_after
            and page_opened is not True
            and (not browser_ok or monotonic() - started_mono >= float(early_after))
        ):
            raise pending_error(pending)
        if monotonic() >= next_progress and not legacy:
            next_progress += PROGRESS_SECONDS
            _say(
                "Still waiting for Allow on the approval page "
                f"(about {_minutes_left(pending, wall_time)} more minutes): "
                f"{pending['verification_uri_complete']}"
            )
        if wall_time() >= float(pending["expires_at"]) + REDEEM_GRACE_SECONDS and outcome in {"pending", "slow_down"}:
            _discard_pending(state_dir, device_code=str(pending["device_code"]))
            raise RuntimeError(EXPIRED_MESSAGE)
        remaining = budget - max(monotonic() - started_mono, wall_time() - started_wall)
        if remaining < POLL_TIMEOUT_SECONDS:
            raise pending_error(pending)
        sleep(min(float(interval), remaining))


def collect_saved_approval(
    state_dir: Path | None = None,
    *,
    post_form: PostForm | None = None,
    wall_time: Callable[[], float] = time.time,
) -> tuple[str, str | None]:
    """One check of the approval this computer is waiting for, for mcp_client
    to run before a Beatra call that has no working credential.

    ("collected", None): the approval was given; the credential is saved.
    ("pending", link): still waiting for Allow on that page.
    ("unreachable", link): Beatra could not be asked; nothing changed.
    ("none", None): nothing to collect (none saved, declined, or lapsed).
    """

    state_dir = (state_dir or Path.home() / ".beatra").expanduser()
    pending, _ = _load_pending(state_dir, wall_time=wall_time)
    if pending is None:
        return "none", None
    link = str(pending["verification_uri_complete"])
    try:
        status, polled = (post_form or _collect_post_form)(TOKEN_URL, _poll_fields(pending))
    except _TransientAuthorizationError:
        return "unreachable", link
    outcome = _classify_poll(status, polled, False)
    if outcome == "token":
        _save_credential(state_dir, polled)
        _discard_pending(state_dir, device_code=str(pending["device_code"]))
        return "collected", None
    if outcome in {"pending", "slow_down"}:
        return "pending", link
    if outcome == "transient":
        return "unreachable", link
    _discard_pending(state_dir, device_code=str(pending["device_code"]))
    return "none", None


def _collect_post_form(url: str, fields: dict[str, str]) -> tuple[int, dict[str, Any]]:
    return _default_post_form(url, fields, timeout=5)


def authorize(
    *,
    state_dir: Path | None = None,
    platform: str | None = None,
    skill_root: Path | None = None,
    force: bool = False,
    post_form: PostForm = _default_post_form,
    probe_credential: CredentialProbe = _default_probe_credential,
    open_browser: Callable[[str], bool] = webbrowser.open,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    wall_time: Callable[[], float] = time.time,
    lock_nonce: Callable[[], str] = lambda: secrets.token_hex(16),
    wait_seconds: float | None = None,
) -> Path:
    """Ensure that the one shared Beatra credential is live and ready."""

    state_dir = (state_dir or Path.home() / ".beatra").expanduser()
    _private_directory(state_dir)
    host_platform = detect_host_platform(platform)
    device_name = device_display_name()
    write_host_config(state_dir, platform=host_platform, device_name=device_name)
    record_skill_installation(state_dir, platform=host_platform, skill_root=skill_root)
    if not force and (credential_path := _existing_credential(state_dir)):
        if probe_credential(credential_path):
            _say("Beatra is ready with the existing private credential.")
            return credential_path
        credential_path.unlink(missing_ok=True)

    pending, resumed = _obtain_pending(
        state_dir=state_dir,
        host_platform=host_platform,
        device_name=device_name,
        post_form=post_form,
        sleep=sleep,
        monotonic=monotonic,
        wall_time=wall_time,
        lock_nonce=lock_nonce,
    )
    return _wait_for_credential(
        pending,
        resumed=resumed,
        force=force,
        state_dir=state_dir,
        host_platform=host_platform,
        device_name=device_name,
        post_form=post_form,
        probe_credential=probe_credential,
        open_browser=open_browser,
        sleep=sleep,
        monotonic=monotonic,
        wall_time=wall_time,
        lock_nonce=lock_nonce,
        wait_seconds=wait_seconds,
    )


#: The approval link this process last showed, for the message a stopped run prints.
_CURRENT_LINK: str | None = None


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Authorize the {PACKAGE_DISPLAY_NAME} Skill")
    parser.add_argument(
        "--platform",
        default=None,
        help=(
            "Name of the agent environment running this install (for example "
            "claude-code, codex, workbuddy). Detected from the environment "
            "when omitted."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Start a new Beatra Device Authorization even when a credential exists.",
    )
    parser.add_argument(
        "--wait-seconds",
        type=int,
        default=None,
        help=(
            "Return within about this many seconds while the approval is still "
            f"pending ({WAIT_SECONDS_MIN}-{WAIT_SECONDS_MAX}); running the same command "
            "again continues the same approval."
        ),
    )
    args = parser.parse_args()
    if args.wait_seconds is not None and not WAIT_SECONDS_MIN <= args.wait_seconds <= WAIT_SECONDS_MAX:
        parser.error(f"--wait-seconds must be between {WAIT_SECONDS_MIN} and {WAIT_SECONDS_MAX}")
    # Agents read this output through a pipe, where Python would otherwise hold
    # the approval link in a buffer until exit and drop it if the run is killed.
    with suppress(AttributeError, ValueError):
        sys.stdout.reconfigure(line_buffering=True)
    _install_signal_handlers()
    try:
        authorize(platform=args.platform, force=args.force, wait_seconds=args.wait_seconds)
        code = 0
    except _ApprovalPending as pending:
        _say(pending.instructions())
        code = EXIT_PENDING
    except _AuthorizationInProgress:
        _say(AUTH_IN_PROGRESS_MESSAGE)
        code = EXIT_PENDING
    except (_Stopped, KeyboardInterrupt):
        # A second stop request while reporting must not turn into a traceback.
        _install_signal_handlers(signal.SIG_IGN)
        if _CURRENT_LINK:
            _say(_ApprovalPending(_CURRENT_LINK, stopped=True).instructions())
        else:
            _say(
                f"{AUTH_PENDING_CODE}: This run was stopped before an approval page was "
                "ready. Run this same command again."
            )
        code = EXIT_PENDING
    except RuntimeError as exc:
        with suppress(OSError, ValueError):
            print(str(exc), file=sys.stderr, flush=True)
        code = 1
    # A host that already closed the pipe must not turn the exit status into
    # a flush error.
    try:
        sys.stdout.flush()
    except (OSError, ValueError):
        _silence_stdout()
    try:
        sys.stderr.flush()
    except (OSError, ValueError):
        with suppress(OSError, ValueError):
            sys.stderr = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115 -- replaces stderr for the process
    return code


if __name__ == "__main__":
    raise SystemExit(main())
