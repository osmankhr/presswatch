"""Send emails via AgentMail -- the weekly digest, and system alerts
(e.g. the LLM provider falling back to OpenRouter)."""
import os

from agentmail import AgentMail

INBOX = "richard_feynman@agentmail.to"
API_KEY = os.environ.get("AGENTMAIL_API_KEY")

# Alerts always go here regardless of who's on the digest recipient list --
# a stuck Claude login/quota is an operational issue, not digest content.
ALERT_RECIPIENT = os.environ.get("PRESSWATCH_ALERT_RECIPIENT", "o.kahraman.phys@gmail.com")


def _client() -> AgentMail:
    if not API_KEY:
        raise RuntimeError("AGENTMAIL_API_KEY env var not set")
    return AgentMail(api_key=API_KEY)


def send(subject: str, html_body: str, text_body: str, recipients: list[str]) -> None:
    client = _client()
    for recipient in recipients:
        response = client.inboxes.messages.send(
            inbox_id=INBOX,
            to=[recipient],
            subject=subject,
            text=text_body,
            html=html_body,
        )
        print(f"[mailer] sent '{subject}' to {recipient} (msg: {response.message_id})")


def send_alert(subject: str, body: str) -> None:
    """Plain-text system alert, e.g. the LLM provider fallback notice."""
    send(
        subject=f"[PressWatch] {subject}",
        html_body=f"<pre>{body}</pre>",
        text_body=body,
        recipients=[ALERT_RECIPIENT],
    )
