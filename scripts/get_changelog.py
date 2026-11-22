#!/usr/bin/env python3
"""
    SPDX-FileCopyrightText: 2026 Infiniti151
    SPDX-License-Identifier: MIT
    ---
    Release Notes -> RPM %changelog lines

    Fetches the GitHub release notes for a tag and prints them as "- ..." lines
    for an RPM spec %changelog entry (max 10 lines). Falls back to
    "- Update to <version>" when the tag has no release or the notes are empty.

    Usage:
        get_changelog.py <owner/repo> <tag>
"""
import json
import os
import re
import sys
import urllib.request

MAX_LINES = 10
TRUNCATED = "- ... (see upstream for full release notes)"


def fetch_release_body(repo, tag):
    headers = {"User-Agent": "rpmcrab-copr", "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as res:
            return json.loads(res.read().decode("utf-8")).get("body") or ""
    except Exception:
        return ""


def format_changelog(body, version):
    text = re.sub(r"<[^>]*>", "", body or "")              # HTML tags
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)    # [text](url) -> text
    text = text.replace("**", "")

    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):                # blanks and headings
            continue
        if re.match(r"(?i)^[*_ ]*full changelog", line):
            continue
        line = re.sub(r"^[-*•]\s*", "", line)
        line = re.sub(r"\s+by\s+@\S+\s+in\s+\S+$", "", line)  # "by @user in <pr url>"
        if line and not re.fullmatch(r"https?://\S+", line):
            lines.append(f"- {line}")

    if not lines:
        return f"- Update to {version}"
    if len(lines) > MAX_LINES:
        lines = lines[:MAX_LINES] + [TRUNCATED]
    return "\n".join(lines)


def main():
    if len(sys.argv) != 3:
        print("Usage: get_changelog.py <owner/repo> <tag>", file=sys.stderr)
        sys.exit(1)
    repo, tag = sys.argv[1], sys.argv[2]
    version = re.sub(r"^[vV]\.?", "", tag)
    print(format_changelog(fetch_release_body(repo, tag), version))


if __name__ == "__main__":
    main()
