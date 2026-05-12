import pytest
from bot.utils.auth import hash_pin, verify_pin, validate_pin, generate_recovery_code
from bot.utils.validators import validate_phone, validate_name


class TestAuth:
    def test_hash_and_verify_pin(self):
        pin = "123456"
        hashed = hash_pin(pin)
        assert hashed != pin
        assert verify_pin(pin, hashed)
        assert not verify_pin("000000", hashed)

    def test_invalid_pin_format(self):
        valid, msg = validate_pin("")
        assert not valid

        valid, msg = validate_pin("123")
        assert not valid

        valid, msg = validate_pin("1234567")
        assert not valid

        valid, msg = validate_pin("abc123")
        assert not valid

        valid, msg = validate_pin("1234")
        assert valid

        valid, msg = validate_pin("123456")
        assert valid

    def test_recovery_code_format(self):
        code = generate_recovery_code()
        assert len(code) == 8
        assert code.isalnum()
        assert code.isupper()


class TestValidators:
    def test_valid_nigerian_phone(self):
        valid, msg, formatted = validate_phone("+2348012345678")
        assert valid
        assert formatted == "+2348012345678"

    def test_valid_phone_no_prefix(self):
        valid, msg, formatted = validate_phone("08012345678")
        assert not valid

    def test_invalid_phone(self):
        valid, msg, formatted = validate_phone("123")
        assert not valid

    def test_valid_name(self):
        valid, msg = validate_name("John Doe")
        assert valid

    def test_invalid_empty_name(self):
        valid, msg = validate_name("")
        assert not valid

    def test_invalid_short_name(self):
        valid, msg = validate_name("A")
        assert not valid
