#!/usr/bin/env python3
"""
    SPDX-FileCopyrightText: 2026 Infiniti151
    SPDX-License-Identifier: MIT
    ---
    COPR Build Monitor & Telegram Notifier (single package)

    Polls one COPR build until it reaches a final state (or a deadline), then
    sends a status message with a per-chroot table (see CHROOTS) to Telegram. Standard library
    only, so the workflow needs no pip install.

    Environment:
        TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID   Telegram credentials
        APP                                    package name (default: rpmcrab)
        OLD_VER, NEW_VER                       versions shown in the message
        PHOTO_URL                              image URL sent with the message (PNG/JPEG,
                                               not SVG); "" disables it
        DRY_RUN=1                              print the message instead of sending it
                                               (Telegram variables are then not needed)

    Usage:
        check_copr_builds.py <build_id>

    Exit code: 0 if the build succeeded, 1 otherwise (failed, canceled, timeout
    or a failed notification), so a bad build also turns the workflow run red.
"""
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

COPR_API = "https://copr.fedorainfracloud.org/api_3"

# Chroots shown in the status table, in display order.
CHROOTS = {
    "fedora-44-x86_64": "Fedora 44",
    "fedora-45-x86_64": "Fedora 45",
    "fedora-eln-x86_64": "Fedora ELN",
    "fedora-rawhide-x86_64": "Fedora Rawhide",
}

TERMINAL_STATES = {"succeeded", "failed", "canceled", "skipped"}

# Image shown above the message (upstream's social header). Override with PHOTO_URL,
# or set PHOTO_URL="" to send plain text.
PHOTO_URL = "https://raw.githubusercontent.com/plusky/rpmcrab/main/docs/assets/social-header.png"
CAPTION_LIMIT = 1024     # Telegram's caption length limit

POLL_INTERVAL = 120      # seconds between polls
MAX_WAIT = 60 * 60       # give up waiting after one hour


def get_json(url, tries=3):
    """GET a JSON document, retrying transient errors."""
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "rpmcrab-copr"})
            with urllib.request.urlopen(req, timeout=30) as res:
                return json.loads(res.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            permanent = 400 <= e.code < 500 and e.code != 429
            if permanent or i == tries - 1:
                raise
        except (urllib.error.URLError, TimeoutError):
            if i == tries - 1:
                raise
        time.sleep(5 * (i + 1))


def get_build(build_id):
    return get_json(f"{COPR_API}/build/{build_id}")


def get_chroot_state(build_id, chroot):
    try:
        query = urllib.parse.urlencode({"build_id": build_id, "chrootname": chroot})
        return get_json(f"{COPR_API}/build-chroot?{query}").get("state", "unknown")
    except Exception:
        return "unknown"


def build_table(states):
    """Monospace table for Telegram's <pre> block."""
    width = max([len("Chroot")] + [len(label) for label in CHROOTS.values()])
    rows = [f"{'Chroot':<{width}} | Status", f"{'-' * width}-+-------"]
    for chroot, label in CHROOTS.items():
        state = states.get(chroot, "unknown")
        icon = "✅" if state == "succeeded" else "❌" if state == "failed" else "⏳"
        rows.append(f"{label:<{width}} | {icon}")
    return f"<pre>{html.escape(chr(10).join(rows))}</pre>"


def telegram_post(token, method, fields):
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}", data=data
    )
    try:
        urllib.request.urlopen(req, timeout=60).read()
    except urllib.error.HTTPError as e:
        # Telegram explains the problem in the JSON body (e.g. "chat not found").
        detail = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {e.code}: {detail}") from None


def send_message(token, chat_id, text):
    telegram_post(token, "sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    })


def send_photo(token, chat_id, photo_url, caption):
    """Telegram downloads the image itself, so it must be a PNG/JPEG/WEBP URL (not SVG)."""
    telegram_post(token, "sendPhoto", {
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML",
    })


def notify(token, chat_id, message, photo_url):
    """Photo with the message as caption when possible, plain text otherwise."""
    if photo_url and len(message) <= CAPTION_LIMIT:
        try:
            send_photo(token, chat_id, photo_url, message)
            return
        except Exception as e:
            print(f"Warning: sending the photo failed ({e}); falling back to text.",
                  file=sys.stderr)
    send_message(token, chat_id, message)


def build_message(app, old_ver, new_ver, build_id, overall, states):
    status = {
        "succeeded": "✅ succeeded",
        "timeout": "⏳ still running (stopped waiting)",
        "canceled": "⚠️ canceled",
        "skipped": "⚠️ skipped",
    }.get(overall, "❌ failed")

    if old_ver and old_ver != new_ver:
        version = f"<code>{html.escape(old_ver)}</code> → <code>{html.escape(new_ver)}</code>"
    else:
        version = f"<code>{html.escape(new_ver)}</code> (rebuild)"

    lines = [
        f"<b>{html.escape(app)}</b>",
        "",
        f"<b>Overall:</b> {status}",
        f"<b>Version:</b> {version}",
    ]
    if overall != "succeeded":
        lines += ["", build_table(states), ""]
    lines += [
        f"<b>Build ID:</b> <code>{html.escape(build_id)}</code>",
        f'<a href="https://copr.fedorainfracloud.org/coprs/build/{build_id}/">View Build on Copr</a>',
    ]
    return "\n".join(lines)


def wait_for_build(build_id):
    """Returns (overall_state, build_dict). overall_state is 'timeout' at the deadline."""
    deadline = time.monotonic() + MAX_WAIT
    build = {}
    while True:
        try:
            build = get_build(build_id)
            state = build.get("state", "unknown")
            print(f"Build {build_id}: {state}", flush=True)
            if state in TERMINAL_STATES:
                return state, build
        except Exception as e:
            print(f"Warning: could not read build {build_id}: {e}", file=sys.stderr)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return "timeout", build
        time.sleep(min(POLL_INTERVAL, remaining))


def main():
    if len(sys.argv) != 2 or not re.fullmatch(r"\d+", sys.argv[1]):
        print("Usage: check_copr_builds.py <build_id>", file=sys.stderr)
        sys.exit(1)
    build_id = sys.argv[1]

    dry_run = bool(os.environ.get("DRY_RUN"))
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not dry_run and not (token and chat_id):
        print("Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set "
              "(or use DRY_RUN=1).", file=sys.stderr)
        sys.exit(1)
    app = os.environ.get("APP", "rpmcrab")
    old_ver = os.environ.get("OLD_VER", "")
    new_ver = os.environ.get("NEW_VER", "")

    overall, _ = wait_for_build(build_id)
    states = {c: get_chroot_state(build_id, c) for c in CHROOTS}

    message = build_message(app, old_ver, new_ver, build_id, overall, states)
    photo_url = os.environ.get("PHOTO_URL", PHOTO_URL)
    if dry_run:
        print("--- DRY RUN: message that would be sent ---")
        print(f"(photo: {photo_url or 'none'})")
        print(message)
        sys.exit(0 if overall == "succeeded" else 1)

    try:
        notify(token, chat_id, message, photo_url)
    except Exception as e:
        print(f"Error: Telegram notification failed: {e}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0 if overall == "succeeded" else 1)


if __name__ == "__main__":
    main()