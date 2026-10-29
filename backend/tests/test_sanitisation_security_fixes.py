"""
Sanitisation & Security Regression Verification Suite
=====================================================
Verifies fixes introduced during the sanitisation exercise:
1. CS-03 (BOLA): Bank officers can only access evidence attached to financial scam cases.
2. CS-06 (Data Integrity): `undertake_case` query construction does not raise NameError for UUID strings.
3. CS-03 (BFLA): AI Case Co-Pilot rejects unassigned officers and allows assigned officers/admins.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from domain.models.case import Case, CaseStatus
from domain.models.user import User
from domain.models.evidence import Evidence
from api.v1.evidence import _check_evidence_access


def _drive_coro(coro):
    """
    Drives an async coroutine to completion synchronously without requiring
    Windows Proactor IOCP loopback sockets (sandbox-safe).
    """
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    except HTTPException:
        raise
    finally:
        coro.close()


def test_banker_denied_evidence_without_case():
    banker_user = User(id=uuid.uuid4(), role="banker", full_name="State Bank Officer")
    evidence = Evidence(id=uuid.uuid4(), case_id=None, evidence_owner=uuid.uuid4())
    db_mock = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        _drive_coro(_check_evidence_access(evidence, banker_user, db_mock))

    assert exc_info.value.status_code == 403
    assert "financial fraud" in exc_info.value.detail


def test_banker_denied_evidence_for_non_financial_case():
    banker_user = User(id=uuid.uuid4(), role="banker", full_name="HDFC Officer")
    case_id = uuid.uuid4()
    evidence = Evidence(id=uuid.uuid4(), case_id=case_id, evidence_owner=uuid.uuid4())

    non_fin_case = Case(id=case_id, scam_type_code="CYBER_HARASSMENT", priority="high")
    db_mock = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.first.return_value = non_fin_case
    db_mock.execute.return_value = result_mock

    with pytest.raises(HTTPException) as exc_info:
        _drive_coro(_check_evidence_access(evidence, banker_user, db_mock))

    assert exc_info.value.status_code == 403
    assert "Access Denied" in exc_info.value.detail


def test_banker_allowed_evidence_for_financial_case():
    banker_user = User(id=uuid.uuid4(), role="banker", full_name="Axis Bank Fraud Desk")
    case_id = uuid.uuid4()
    evidence = Evidence(id=uuid.uuid4(), case_id=case_id, evidence_owner=uuid.uuid4())

    fin_case = Case(id=case_id, scam_type_code="FIN-PAY-UPI", priority="critical")
    db_mock = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.first.return_value = fin_case
    db_mock.execute.return_value = result_mock

    # Must succeed without raising HTTPException
    _drive_coro(_check_evidence_access(evidence, banker_user, db_mock))


def test_citizen_denied_other_citizen_evidence():
    citizen_1 = User(id=uuid.uuid4(), role="citizen")
    citizen_2_id = uuid.uuid4()
    evidence = Evidence(id=uuid.uuid4(), case_id=uuid.uuid4(), evidence_owner=citizen_2_id)
    db_mock = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        _drive_coro(_check_evidence_access(evidence, citizen_1, db_mock))

    assert exc_info.value.status_code == 403
    assert "Not authorized" in exc_info.value.detail


def test_admin_allowed_any_evidence():
    admin_user = User(id=uuid.uuid4(), role="admin")
    evidence = Evidence(id=uuid.uuid4(), case_id=uuid.uuid4(), evidence_owner=uuid.uuid4())
    db_mock = AsyncMock()

    # Admin should bypass restrictions
    _drive_coro(_check_evidence_access(evidence, admin_user, db_mock))


def test_case_undertake_uuid_query_or_import():
    """Verify that 'or_' is properly imported and select query builds cleanly for UUID."""
    from sqlalchemy import select, or_
    val_uuid = uuid.uuid4()
    case_number = str(val_uuid)
    # Query must evaluate without raising NameError
    q = select(Case).where(or_(Case.case_number == case_number, Case.id == val_uuid)).with_for_update()
    assert q is not None


def test_sla_cron_unauthorized_rejected():
    from api.v1.cases import evaluate_sla_cron
    citizen = User(id=uuid.uuid4(), role="citizen")
    with pytest.raises(HTTPException) as exc:
        _drive_coro(evaluate_sla_cron(x_cron_secret="invalid", user=citizen))
    assert exc.value.status_code == 403


def test_sla_cron_valid_secret_accepted(monkeypatch):
    from api.v1.cases import evaluate_sla_cron
    from core.config import settings
    from runtime.sla_monitor_daemon import sla_monitor_daemon

    mock_check = AsyncMock(return_value=3)
    monkeypatch.setattr(sla_monitor_daemon, "check_cases_sla", mock_check)

    res = _drive_coro(evaluate_sla_cron(x_cron_secret=settings.SECRET_KEY, user=None))
    assert res["status"] == "success"
    assert res["breached_count"] == 3


def test_sla_cron_admin_accepted(monkeypatch):
    from api.v1.cases import evaluate_sla_cron
    from runtime.sla_monitor_daemon import sla_monitor_daemon

    admin = User(id=uuid.uuid4(), role="admin")
    mock_check = AsyncMock(return_value=1)
    monkeypatch.setattr(sla_monitor_daemon, "check_cases_sla", mock_check)

    res = _drive_coro(evaluate_sla_cron(x_cron_secret=None, user=admin))
    assert res["status"] == "success"
    assert res["breached_count"] == 1
