from flask import request

from app.extensions import db
from app.models import AuditLog, User


def record_audit_event(action: str, status: str, user: User | None = None) -> None:
    ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
    user_agent = (request.user_agent.string or "")[:255]

    log = AuditLog(
        user_id=user.id if user else None,
        action=action,
        status=status,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.session.add(log)
