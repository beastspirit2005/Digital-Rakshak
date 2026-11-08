import pytest
import uuid
from core.security import verify_password, get_password_hash
from domain.models.case import Case, CaseStatus
from domain.models.user import User

def test_verify_password_safe_handling():
    # Valid hash
    pw = "Secret@123"
    hashed = get_password_hash(pw)
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

    # Invalid salt / garbage string (must NOT raise ValueError: Invalid salt)
    assert verify_password("Secret@123", "invalid_garbage_hash") is False
    assert verify_password("Secret@123", "") is False
    assert verify_password("", hashed) is False
    assert verify_password("Secret@123", None) is False

def test_safe_string_encrypted_type_decryption():
    from infrastructure.security.encryption import SafeStringEncryptedType
    enc_type = SafeStringEncryptedType()

    # Plain text value (legacy data)
    assert enc_type.process_result_value("9876543210", None) == "9876543210"
    assert enc_type.process_result_value(None, None) is None
    assert enc_type.process_result_value("", None) == ""

    # Valid encrypted value round-trip
    bound = enc_type.process_bind_param("+91-9876543210", None)
    assert bound is not None
    decrypted = enc_type.process_result_value(bound, None)
    assert decrypted == "+91-9876543210"
