from app.models.audit_log import AuditLog


def log_action(db, user_id: int, action: str, entity: str, entity_id: int, description: str = None):
    log = AuditLog(
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        description=description,
    )
    db.add(log)
    db.commit()
