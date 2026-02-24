import hmac
import secrets
from typing import Optional

import requests
from flask import current_app, session

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def is_turnstile_enabled() -> bool:
    return bool(
        current_app.config.get("TURNSTILE_ENABLED")
        and current_app.config.get("TURNSTILE_SITE_KEY")
        and current_app.config.get("TURNSTILE_SECRET_KEY")
    )


def verify_turnstile_token(token: str, remote_ip: Optional[str] = None) -> bool:
    if not token:
        return False

    payload = {
        "secret": current_app.config.get("TURNSTILE_SECRET_KEY"),
        "response": token,
        "remoteip": remote_ip,
    }

    try:
        response = requests.post(TURNSTILE_VERIFY_URL, data=payload, timeout=5)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return False

    return bool(data.get("success"))


def _captcha_session_keys(scope: str) -> tuple[str, str]:
    question_key = f"captcha_{scope}_question"
    answer_key = f"captcha_{scope}_answer"
    return question_key, answer_key


def generate_math_challenge(scope: str) -> str:
    left = secrets.randbelow(15) + 5
    right = secrets.randbelow(9) + 1

    if secrets.randbelow(2):
        question = f"What is {left} + {right}?"
        answer = left + right
    else:
        if right > left:
            left, right = right, left
        question = f"What is {left} - {right}?"
        answer = left - right

    question_key, answer_key = _captcha_session_keys(scope)
    session[question_key] = question
    session[answer_key] = str(answer)
    return question


def get_math_challenge(scope: str) -> str:
    question_key, _ = _captcha_session_keys(scope)
    question = session.get(question_key)
    if question:
        return question
    return generate_math_challenge(scope)


def verify_math_challenge(scope: str, answer: str) -> bool:
    _, answer_key = _captcha_session_keys(scope)
    expected = session.get(answer_key)
    submitted = (answer or "").strip()

    is_valid = bool(expected) and hmac.compare_digest(submitted, str(expected))

    question_key, _ = _captcha_session_keys(scope)
    session.pop(answer_key, None)
    session.pop(question_key, None)

    return is_valid
