from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from src.db.models import PredictionRecord, UserProfile


def _user_to_dict(user: UserProfile) -> Dict[str, Any]:
    return {
        "id": user.id,
        "external_user_id": user.external_user_id,
        "email": user.email,
        "user_segment": user.user_segment,
        "device_type": user.device_type,
        "os_type": user.os_type,
        "region": user.region,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


def _prediction_to_dict(prediction: PredictionRecord) -> Dict[str, Any]:
    return {
        "id": prediction.id,
        "user_id": prediction.user_id,
        "request_id": prediction.request_id,
        "dropoff_probability": prediction.dropoff_probability,
        "predicted_label": prediction.predicted_label,
        "risk_level": prediction.risk_level,
        "threshold_used": prediction.threshold_used,
        "payload_json": prediction.payload_json,
        "created_at": prediction.created_at.isoformat() if prediction.created_at else None,
    }


def create_user(session: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    user = UserProfile(
        external_user_id=str(payload["external_user_id"]),
        email=payload.get("email"),
        user_segment=payload.get("user_segment"),
        device_type=payload.get("device_type"),
        os_type=payload.get("os_type"),
        region=payload.get("region"),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return _user_to_dict(user)


def list_users(
    session: Session,
    limit: int = 100,
    offset: int = 0,
    user_segment: str | None = None,
) -> List[Dict[str, Any]]:
    """List users with optimized filtering. O(log n + k) with index on user_segment and id."""
    query = session.query(UserProfile)
    if user_segment:
        query = query.filter(UserProfile.user_segment == str(user_segment))

    # Index-based sorting on primary key for stable pagination
    rows = query.order_by(UserProfile.id.desc()).offset(offset).limit(limit).all()
    return [_user_to_dict(row) for row in rows]


def get_user(session: Session, user_id: int) -> Dict[str, Any] | None:
    user = session.query(UserProfile).filter(UserProfile.id == user_id).first()
    return _user_to_dict(user) if user else None


def update_user(session: Session, user_id: int, payload: Dict[str, Any]) -> Dict[str, Any] | None:
    user = session.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user:
        return None

    for key in ["email", "user_segment", "device_type", "os_type", "region"]:
        if key in payload:
            setattr(user, key, payload.get(key))

    if "external_user_id" in payload:
        user.external_user_id = str(payload["external_user_id"])

    user.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(user)
    return _user_to_dict(user)


def delete_user(session: Session, user_id: int) -> bool:
    user = session.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user:
        return False

    session.delete(user)
    session.commit()
    return True


def create_prediction_record(
    session: Session,
    prediction_result: Dict[str, Any],
    request_id: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    user_id = None
    external_user_id = payload.get("external_user_id")
    if external_user_id:
        user = session.query(UserProfile).filter(UserProfile.external_user_id == str(external_user_id)).first()
        if user:
            user_id = user.id

    record = PredictionRecord(
        user_id=user_id,
        request_id=request_id,
        dropoff_probability=float(prediction_result.get("dropoff_probability", 0.0)),
        predicted_label=int(prediction_result.get("predicted_label", 0)),
        risk_level=str(prediction_result.get("risk_level", "unknown")),
        threshold_used=float(prediction_result.get("threshold_used", 0.5)),
        payload_json=json.dumps(payload, ensure_ascii=True),
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return _prediction_to_dict(record)


def list_predictions(
    session: Session,
    limit: int = 100,
    offset: int = 0,
    risk_level: str | None = None,
    min_probability: float | None = None,
) -> List[Dict[str, Any]]:
    """List predictions with optimized filtering. O(log n + k) with indexes on risk_level, created_at, and dropoff_probability."""
    query = session.query(PredictionRecord)
    if risk_level:
        query = query.filter(PredictionRecord.risk_level == str(risk_level))
    if min_probability is not None:
        query = query.filter(PredictionRecord.dropoff_probability >= float(min_probability))

    # Index-based sorting on primary key for stable pagination - O(log n)
    rows = query.order_by(PredictionRecord.id.desc()).offset(offset).limit(limit).all()
    return [_prediction_to_dict(row) for row in rows]
