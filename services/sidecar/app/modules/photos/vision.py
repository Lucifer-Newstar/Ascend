"""Optional feedback on two progress photos from a local vision model (Ollama).

Off unless the user turns it on, never for anyone under 18, and the model is told not to
talk about body fat, weight or looks. Its reply then passes a guard that drops every
sentence with a number or one of those words; if nothing is left, the user gets a plain
"nothing useful to say" instead. Nothing leaves the PC: the model runs on localhost.
"""

from __future__ import annotations

import base64
import re

import httpx

from app.modules.coach.ollama import KEEP_ALIVE, THINK_RE, OllamaUnavailable, reply_content

VISION_VERSION = "photo-feedback-v1"
MIN_AGE = 18

PROMPT = (
    "You are a strength coach looking at two progress photos of the same person, the "
    "first older and the second newer. In at most 3 short sentences, describe visible "
    "changes in posture, muscle definition and symmetry, and suggest one training focus. "
    "Rules: no numbers of any kind, never estimate body fat or weight, never comment on "
    "attractiveness, skin, face or private areas, no medical claims. If the photos are "
    "not comparable (different pose, light or framing), say so and stop."
)

BANNED = re.compile(
    r"\d|%|\b(fat|fats|fatty|weigh\w*|kg|kgs|kilo\w*|lbs?|pounds?|bmi|obese|obesity|"
    r"overweight|underweight|skinny|chubby|calori\w*|diet\w*|attractive\w*|ugly|"
    r"handsome|beautiful|sexy|hot|unattractive|thin|lean\w*|bulky)\b",
    re.IGNORECASE,
)
SENTENCE = re.compile(r"(?<=[.!?])\s+")
FALLBACK = (
    "I can't say anything useful about these two photos. Same spot, same light and the "
    "same pose make the next comparison easier."
)


def guard(text: str) -> tuple[str, bool]:
    """(safe text, whether anything was removed)."""
    text = THINK_RE.sub("", text).strip()
    kept = [s.strip() for s in SENTENCE.split(text) if s.strip() and not BANNED.search(s)]
    kept = kept[:3]
    removed = len(kept) < len([s for s in SENTENCE.split(text) if s.strip()])
    if not kept:
        return FALLBACK, True
    return " ".join(kept), removed


def compare(host: str, model: str, older: bytes, newer: bytes, timeout: float = 120.0) -> str:
    if not host:
        raise OllamaUnavailable("no usable OLLAMA_HOST")
    payload = {
        "model": model,
        "stream": False,
        "think": False,
        "keep_alive": KEEP_ALIVE,
        "options": {"temperature": 0.2, "num_predict": 160},
        "messages": [
            {
                "role": "user",
                "content": PROMPT,
                "images": [base64.b64encode(older).decode(), base64.b64encode(newer).decode()],
            }
        ],
    }
    try:
        r = httpx.post(f"{host}/api/chat", json=payload, timeout=timeout)
        r.raise_for_status()
        return reply_content(r.json())
    except (httpx.HTTPError, ValueError) as e:
        raise OllamaUnavailable(str(e)) from e
