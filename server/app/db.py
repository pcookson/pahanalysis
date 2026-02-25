from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings


def get_db_path() -> Path:
    return Path(settings.sqlite_db_path)


def get_connection() -> sqlite3.Connection:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pah_scores (
                product_id TEXT PRIMARY KEY,
                score_version TEXT NOT NULL,
                confidence REAL NOT NULL,
                grade TEXT NOT NULL,
                computed_at TEXT NOT NULL,
                coverage_json TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                notes TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pah_overrides (
                product_id TEXT PRIMARY KEY,
                user_label TEXT NOT NULL,
                user_confidence REAL,
                note TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def get_pah_score(product_id: str, score_version: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                product_id,
                score_version,
                confidence,
                grade,
                computed_at,
                coverage_json,
                evidence_json,
                notes
            FROM pah_scores
            WHERE product_id = ? AND score_version = ?
            """,
            (product_id, score_version),
        ).fetchone()

    if row is None:
        return None

    return {
        "product_id": row["product_id"],
        "score_version": row["score_version"],
        "confidence": float(row["confidence"]),
        "grade": row["grade"],
        "computed_at": row["computed_at"],
        "coverage": json.loads(row["coverage_json"]),
        "evidence": json.loads(row["evidence_json"]),
        "notes": row["notes"],
    }


def upsert_pah_score(score: dict[str, Any]) -> None:
    coverage_json = json.dumps(score["coverage"], separators=(",", ":"), sort_keys=True)
    evidence_json = json.dumps(score["evidence"], separators=(",", ":"), sort_keys=True)

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO pah_scores (
                product_id,
                score_version,
                confidence,
                grade,
                computed_at,
                coverage_json,
                evidence_json,
                notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(product_id) DO UPDATE SET
                score_version = excluded.score_version,
                confidence = excluded.confidence,
                grade = excluded.grade,
                computed_at = excluded.computed_at,
                coverage_json = excluded.coverage_json,
                evidence_json = excluded.evidence_json,
                notes = excluded.notes
            """,
            (
                score["product_id"],
                score["score_version"],
                float(score["confidence"]),
                score["grade"],
                score["computed_at"],
                coverage_json,
                evidence_json,
                score.get("notes"),
            ),
        )
        conn.commit()


def get_pah_override(product_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                product_id,
                user_label,
                user_confidence,
                note,
                updated_at
            FROM pah_overrides
            WHERE product_id = ?
            """,
            (product_id,),
        ).fetchone()

    if row is None:
        return None

    return {
        "product_id": row["product_id"],
        "user_label": row["user_label"],
        "user_confidence": (
            float(row["user_confidence"]) if row["user_confidence"] is not None else None
        ),
        "note": row["note"],
        "updated_at": row["updated_at"],
    }


def upsert_pah_override(
    *,
    product_id: str,
    user_label: str,
    user_confidence: float | None,
    note: str | None,
) -> dict[str, Any]:
    updated_at = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO pah_overrides (
                product_id,
                user_label,
                user_confidence,
                note,
                updated_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(product_id) DO UPDATE SET
                user_label = excluded.user_label,
                user_confidence = excluded.user_confidence,
                note = excluded.note,
                updated_at = excluded.updated_at
            """,
            (product_id, user_label, user_confidence, note, updated_at),
        )
        conn.commit()

    return {
        "product_id": product_id,
        "user_label": user_label,
        "user_confidence": user_confidence,
        "note": note,
        "updated_at": updated_at,
    }
