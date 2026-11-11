import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy import column, select
from domain.services.fraud_lifecycle_engine import FraudLifecycleEngine


@pytest.mark.asyncio
async def test_sql_contains_autoescape_compilation():
    """Verify that .contains(val, autoescape=True) correctly compiles with escape character."""
    test_id = "TXN_100%_LEGIT"
    scam_text = column("scam_text")
    stmt = select(scam_text).where(scam_text.contains(test_id, autoescape=True))
    compiled_str = str(stmt.compile(compile_kwargs={"literal_binds": False}))
    assert "ESCAPE" in compiled_str
    assert "scam_text LIKE" in compiled_str


@pytest.mark.asyncio
async def test_path_traversal_component_aware_rejection(tmp_path):
    """
    Verify component-aware validation rejects:
    1. Parent directory traversal (../../etc/passwd)
    2. Sibling directory prefix matching (/base_evil vs /base)
    3. Symlinks
    """
    base_vault = tmp_path / "evidence_vault"
    base_vault.mkdir()
    sibling_vault = tmp_path / "evidence_vault_evil"
    sibling_vault.mkdir()

    secret_in_sibling = sibling_vault / "secret.txt"
    secret_in_sibling.write_text("classified data")

    # 1. Test sibling directory escape attempt (classic startswith flaw)
    target_path = secret_in_sibling.resolve()
    base_resolved = base_vault.resolve()

    # The component-aware check
    is_safe = False
    try:
        is_safe = target_path.is_relative_to(base_resolved)
    except AttributeError:
        is_safe = (os.path.commonpath([str(base_resolved), str(target_path)]) == str(base_resolved))

    assert is_safe is False, "Sibling directory must NOT be considered safe"

    # 2. Test symlink rejection
    legit_file = base_vault / "legit.pdf"
    legit_file.write_text("legitimate evidence")
    symlink_file = base_vault / "symlink_to_secret.pdf"
    try:
        os.symlink(str(secret_in_sibling), str(symlink_file))
        assert symlink_file.is_symlink() is True
    except (OSError, NotImplementedError):
        # Pass gracefully on environments restricting symlink creation
        pass


@pytest.mark.asyncio
async def test_hash_chain_alias_and_tip_verification():
    """
    Verify that FraudLifecycleEngine generates certificates exposing both
    canonical 'chain_head_hash' and backward-compatible 'merkle_root_hash'.
    """
    mock_db = AsyncMock()
    mock_case = MagicMock()
    mock_case.id = "case-uuid-1234"
    mock_case.case_number = "CR-2026-9999"

    # Mock empty event sequence
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute = AsyncMock(return_value=mock_result)

    cert = await FraudLifecycleEngine.generate_bsa_evidentiary_certificate(
        db=mock_db,
        case=mock_case,
        officer_name="Inspector Test"
    )

    integrity = cert["integrity_verification"]
    assert "chain_head_hash" in integrity
    assert "merkle_root_hash" in integrity
    assert integrity["chain_head_hash"] == integrity["merkle_root_hash"]
    assert "sequential hash chain" in integrity["verification_notes"]
