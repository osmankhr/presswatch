"""LLM provider: Claude by default (via the dedicated n8n profile), OpenRouter
as a failure-triggered fallback, with a one-time-per-run email alert when the
fallback actually gets used.

Reuses the isolated-profile mechanism already built for the n8n hackathon
project (~/n8n-data/claude-profiles/<profile>/, each an independent `claude
login` session) rather than sharing a login that other projects also use.
Calls the `claude` binary directly with HOME overridden to the profile's
directory instead of shelling out to ~/n8n-data/run-claude.sh, because this
needs --output-format json for cost/token logging (matches the pattern
established in hr_tech's llm_provider.py) and structured failure detection,
neither of which run-claude.sh's plain-text output supports.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

CLAUDE_BIN = "/home/osman/.local/bin/claude"
CLAUDE_PROFILE = os.environ.get("PRESSWATCH_CLAUDE_PROFILE", "aiworkspacetr")
CLAUDE_PROFILE_HOME = Path(f"/home/osman/n8n-data/claude-profiles/{CLAUDE_PROFILE}")
CLAUDE_MODEL = os.environ.get("PRESSWATCH_CLAUDE_MODEL", "claude-sonnet-5")

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-3.7-sonnet")

# Alert once per process run, not once per failed call -- a whole run's worth
# of fallback calls should produce one email, not a flood.
_fallback_alerted = False


def _call_claude(prompt: str, system: str | None, timeout: int) -> str | None:
    if not (CLAUDE_PROFILE_HOME / ".claude" / ".credentials.json").exists():
        logger.warning(
            "Claude profile %r has no credentials at %s -- not logged in",
            CLAUDE_PROFILE,
            CLAUDE_PROFILE_HOME,
        )
        return None

    env = os.environ.copy()
    env["HOME"] = str(CLAUDE_PROFILE_HOME)

    cmd = [CLAUDE_BIN, "--print", "--model", CLAUDE_MODEL, "--tools", "", "--output-format", "json"]
    if system:
        cmd += ["--system-prompt", system]

    try:
        result = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True, timeout=timeout, env=env
        )
    except FileNotFoundError:
        logger.error("claude CLI not found at %s", CLAUDE_BIN)
        return None
    except subprocess.TimeoutExpired:
        logger.warning("claude CLI (profile=%s) timed out after %ds", CLAUDE_PROFILE, timeout)
        return None

    if result.returncode != 0:
        logger.warning(
            "claude CLI (profile=%s) returned non-zero: %s", CLAUDE_PROFILE, result.stderr[:300]
        )
        return None

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        logger.warning("claude CLI (profile=%s) did not return valid JSON", CLAUDE_PROFILE)
        return None

    if payload.get("is_error"):
        logger.warning(
            "claude CLI (profile=%s) reported an error result: %s",
            CLAUDE_PROFILE,
            str(payload.get("result"))[:300],
        )
        return None

    text = payload.get("result")
    if not isinstance(text, str):
        return None

    usage = payload.get("usage") or {}
    logger.info(
        "claude call ok (profile=%s): %.2fs $%.4f in=%s out=%s",
        CLAUDE_PROFILE,
        (payload.get("duration_ms") or 0) / 1000,
        payload.get("total_cost_usd") or 0.0,
        usage.get("input_tokens"),
        usage.get("output_tokens"),
    )
    return text


def _call_openrouter(prompt: str, system: str | None, timeout: int) -> str | None:
    if not OPENROUTER_API_KEY:
        logger.error("OpenRouter fallback needed but OPENROUTER_API_KEY is not set")
        return None

    import requests

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={"model": OPENROUTER_MODEL, "messages": messages},
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception:
        logger.exception("OpenRouter fallback call failed")
        return None


def _alert_fallback(reason: str) -> None:
    global _fallback_alerted
    if _fallback_alerted:
        return
    _fallback_alerted = True
    try:
        from mailer import send_alert

        send_alert(
            subject="fell back to OpenRouter",
            body=(
                f"Claude (profile={CLAUDE_PROFILE}) failed, PressWatch is using the "
                f"OpenRouter fallback for the rest of this run.\n\n"
                f"Reason: {reason}\n\n"
                f"Check the Claude login/quota for the '{CLAUDE_PROFILE}' profile:\n"
                f"  ls {CLAUDE_PROFILE_HOME}/.claude/.credentials.json\n"
                f"  HOME={CLAUDE_PROFILE_HOME} claude login   # if it needs re-auth"
            ),
        )
    except Exception:
        logger.exception("Failed to send fallback alert email")


def call_model_text(*, prompt: str, system: str | None = None, timeout: int = 60) -> str | None:
    """Call Claude first; fall back to OpenRouter on any failure, alerting once per run."""
    text = _call_claude(prompt, system, timeout)
    if text is not None:
        return text

    logger.warning("Claude call failed -- falling back to OpenRouter")
    _alert_fallback(reason="Claude CLI call failed or returned no usable output (see logs)")
    return _call_openrouter(prompt, system, timeout)
