import os
import tempfile
from datetime import datetime, timedelta
from unittest import mock

import jwt
import pytest
from fastapi import HTTPException, Request

from bec_atlas.authentication import (
    OptionalOAuth2PasswordBearer,
    create_access_token,
    decode_token,
    get_current_user,
    get_current_user_sync,
    get_password_hash,
    get_secret_key,
    verify_password,
)
from bec_atlas.model import UserInfo


@pytest.fixture
def mock_request():
    """Create a mock FastAPI Request object."""
    request = mock.Mock(spec=Request)
    request.headers = {}
    request.cookies = {}
    return request


@pytest.fixture
def valid_token():
    """Create a valid JWT token for testing."""
    test_payload = {
        "email": "test@example.com",
        "exp": (datetime.now() + timedelta(hours=1)).timestamp(),
    }
    return jwt.encode(test_payload, get_secret_key(), algorithm="HS256")


@pytest.fixture
def expired_token():
    """Create an expired JWT token for testing."""
    test_payload = {
        "email": "test@example.com",
        "exp": (datetime.now() - timedelta(hours=1)).timestamp(),
    }
    return jwt.encode(test_payload, get_secret_key(), algorithm="HS256")


@pytest.fixture
def invalid_token():
    """Create an invalid JWT token for testing."""
    return "invalid.jwt.token"


@pytest.fixture
def token_without_email():
    """Create a JWT token without email field."""
    test_payload = {
        "username": "testuser",
        "exp": (datetime.now() + timedelta(hours=1)).timestamp(),
    }
    return jwt.encode(test_payload, get_secret_key(), algorithm="HS256")


class TestGetCurrentUser:
    """Test cases for get_current_user function."""

    @pytest.mark.timeout(60)
    @mock.patch("bec_atlas.authentication.optional_oauth2_scheme")
    async def test_get_current_user_with_auth_header_success(
        self, mock_oauth2_scheme, mock_request, valid_token
    ):
        """Test successful authentication with Authorization header."""
        mock_oauth2_scheme.return_value = valid_token

        user_info = await get_current_user(mock_request, valid_token)

        assert isinstance(user_info, UserInfo)
        assert user_info.email == "test@example.com"
        assert user_info.token == valid_token

    @pytest.mark.timeout(60)
    @mock.patch("bec_atlas.authentication.optional_oauth2_scheme")
    async def test_get_current_user_with_cookie_success(
        self, mock_oauth2_scheme, mock_request, valid_token
    ):
        """Test successful authentication with cookie."""
        mock_oauth2_scheme.return_value = None  # No Authorization header
        mock_request.cookies = {"access_token": valid_token}

        user_info = await get_current_user(mock_request, None)

        assert isinstance(user_info, UserInfo)
        assert user_info.email == "test@example.com"
        assert user_info.token == valid_token

    @pytest.mark.timeout(60)
    @mock.patch("bec_atlas.authentication.optional_oauth2_scheme")
    async def test_get_current_user_no_token_found(self, mock_oauth2_scheme, mock_request):
        """Test authentication failure when no token is found."""
        mock_oauth2_scheme.return_value = None  # No Authorization header
        mock_request.cookies = {}  # No cookie

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, None)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials - no token found" in exc_info.value.detail
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

    @pytest.mark.timeout(60)
    @mock.patch("bec_atlas.authentication.optional_oauth2_scheme")
    async def test_get_current_user_invalid_token_in_header(
        self, mock_oauth2_scheme, mock_request, invalid_token
    ):
        """Test authentication failure with invalid token in Authorization header."""
        mock_oauth2_scheme.return_value = invalid_token

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, invalid_token)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

    @pytest.mark.timeout(60)
    @mock.patch("bec_atlas.authentication.optional_oauth2_scheme")
    async def test_get_current_user_invalid_token_in_cookie(
        self, mock_oauth2_scheme, mock_request, invalid_token
    ):
        """Test authentication failure with invalid token in cookie."""
        mock_oauth2_scheme.return_value = None
        mock_request.cookies = {"access_token": invalid_token}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, None)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

    @pytest.mark.timeout(60)
    @mock.patch("bec_atlas.authentication.optional_oauth2_scheme")
    async def test_get_current_user_expired_token(
        self, mock_oauth2_scheme, mock_request, expired_token
    ):
        """Test authentication failure with expired token."""
        mock_oauth2_scheme.return_value = expired_token

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, expired_token)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail

    @pytest.mark.timeout(60)
    @mock.patch("bec_atlas.authentication.optional_oauth2_scheme")
    async def test_get_current_user_token_without_email(
        self, mock_oauth2_scheme, mock_request, token_without_email
    ):
        """Test authentication failure with token missing email field."""
        mock_oauth2_scheme.return_value = token_without_email

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, token_without_email)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail

    @pytest.mark.timeout(60)
    @mock.patch("bec_atlas.authentication.optional_oauth2_scheme")
    async def test_get_current_user_prefers_auth_header_over_cookie(
        self, mock_oauth2_scheme, mock_request, valid_token
    ):
        """Test that Authorization header takes precedence over cookie."""
        header_token = valid_token
        cookie_token = "different_token"

        mock_oauth2_scheme.return_value = header_token
        mock_request.cookies = {"access_token": cookie_token}

        user_info = await get_current_user(mock_request, header_token)

        # Should use the header token, not the cookie token
        assert user_info.token == header_token

    @pytest.mark.timeout(60)
    @mock.patch("bec_atlas.authentication.optional_oauth2_scheme")
    async def test_get_current_user_empty_string_token(self, mock_oauth2_scheme, mock_request):
        """Test authentication failure with empty string token."""
        mock_oauth2_scheme.return_value = ""
        mock_request.cookies = {}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, "")

        assert exc_info.value.status_code == 401


class TestGetCurrentUserSync:
    """Test cases for get_current_user_sync function."""

    @pytest.mark.timeout(60)
    def test_get_current_user_sync_success(self, valid_token):
        """Test successful synchronous authentication."""
        user_info = get_current_user_sync(valid_token)

        assert isinstance(user_info, UserInfo)
        assert user_info.email == "test@example.com"
        assert user_info.token == valid_token

    @pytest.mark.timeout(60)
    def test_get_current_user_sync_invalid_token(self, invalid_token):
        """Test synchronous authentication failure with invalid token."""
        with pytest.raises(HTTPException) as exc_info:
            get_current_user_sync(invalid_token)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

    @pytest.mark.timeout(60)
    def test_get_current_user_sync_expired_token(self, expired_token):
        """Test synchronous authentication failure with expired token."""
        with pytest.raises(HTTPException) as exc_info:
            get_current_user_sync(expired_token)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail

    @pytest.mark.timeout(60)
    def test_get_current_user_sync_token_without_email(self, token_without_email):
        """Test synchronous authentication failure with token missing email."""
        with pytest.raises(HTTPException) as exc_info:
            get_current_user_sync(token_without_email)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail

    @pytest.mark.timeout(60)
    def test_get_current_user_sync_malformed_token(self):
        """Test synchronous authentication failure with malformed token."""
        malformed_token = "not.a.valid.jwt.structure"

        with pytest.raises(HTTPException) as exc_info:
            get_current_user_sync(malformed_token)

        assert exc_info.value.status_code == 401

    @pytest.mark.timeout(60)
    def test_get_current_user_sync_empty_token(self):
        """Test synchronous authentication failure with empty token."""
        with pytest.raises(HTTPException) as exc_info:
            get_current_user_sync("")

        assert exc_info.value.status_code == 401


class TestOptionalOAuth2PasswordBearer:
    """Test cases for OptionalOAuth2PasswordBearer class."""

    @pytest.mark.timeout(60)
    async def test_oauth2_with_valid_bearer_token(self, mock_request):
        """Test extraction of valid bearer token."""
        mock_request.headers = {"Authorization": "Bearer valid_token_123"}

        oauth2 = OptionalOAuth2PasswordBearer(tokenUrl="/test")
        token = await oauth2(mock_request)

        assert token == "valid_token_123"

    @pytest.mark.timeout(60)
    async def test_oauth2_with_no_authorization_header(self, mock_request):
        """Test handling of missing Authorization header."""
        mock_request.headers = {}

        oauth2 = OptionalOAuth2PasswordBearer(tokenUrl="/test")
        token = await oauth2(mock_request)

        assert token is None

    @pytest.mark.timeout(60)
    async def test_oauth2_with_non_bearer_scheme(self, mock_request):
        """Test handling of non-Bearer authorization scheme."""
        mock_request.headers = {"Authorization": "Basic dXNlcjpwYXNz"}

        oauth2 = OptionalOAuth2PasswordBearer(tokenUrl="/test")
        token = await oauth2(mock_request)

        assert token is None

    @pytest.mark.timeout(60)
    async def test_oauth2_with_malformed_authorization_header(self, mock_request):
        """Test handling of malformed Authorization header."""
        mock_request.headers = {"Authorization": "Bearer"}  # Missing token

        oauth2 = OptionalOAuth2PasswordBearer(tokenUrl="/test")
        token = await oauth2(mock_request)

        assert token == ""  # Returns empty string for malformed header

    @pytest.mark.timeout(60)
    async def test_oauth2_with_empty_authorization_header(self, mock_request):
        """Test handling of empty Authorization header."""
        mock_request.headers = {"Authorization": ""}

        oauth2 = OptionalOAuth2PasswordBearer(tokenUrl="/test")
        token = await oauth2(mock_request)

        assert token is None


class TestTokenOperations:
    """Test cases for token creation and decoding."""

    @pytest.mark.timeout(60)
    def test_create_access_token_default_expiry(self):
        """Test token creation with default expiry."""
        data = {"email": "test@example.com"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token can be decoded
        payload = decode_token(token)
        assert payload["email"] == "test@example.com"
        assert "exp" in payload

    @pytest.mark.timeout(60)
    def test_create_access_token_custom_expiry(self):
        """Test token creation with custom expiry."""
        data = {"email": "test@example.com"}
        expires_delta = timedelta(hours=2)
        token = create_access_token(data, expires_delta)

        assert isinstance(token, str)
        payload = decode_token(token)
        assert payload["email"] == "test@example.com"

        # Check expiry is approximately 2 hours from now (as timestamp)
        exp_timestamp = payload["exp"]
        expected_timestamp = (datetime.now() + timedelta(hours=2)).timestamp()
        time_diff = abs(exp_timestamp - expected_timestamp)
        assert time_diff < 60  # Should be within 1 minute

    @pytest.mark.timeout(60)
    def test_decode_token_expired(self, expired_token):
        """Test token decoding with expired token."""
        with pytest.raises(HTTPException) as exc_info:
            decode_token(expired_token)

        assert exc_info.value.status_code == 401

    @pytest.mark.timeout(60)
    def test_decode_token_success(self, valid_token):
        """Test successful token decoding."""
        payload = decode_token(valid_token)

        assert isinstance(payload, dict)
        assert "email" in payload
        assert "exp" in payload

    @pytest.mark.timeout(60)
    def test_decode_token_invalid(self, invalid_token):
        """Test token decoding with invalid token."""
        with pytest.raises(HTTPException) as exc_info:
            decode_token(invalid_token)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail

    @pytest.mark.timeout(60)
    def test_decode_token_wrong_secret(self):
        """Test token decoding with wrong secret."""
        # Create token with different secret
        wrong_secret_token = jwt.encode(
            {"email": "test@example.com", "exp": (datetime.now() + timedelta(hours=1)).timestamp()},
            "wrong_secret",
            algorithm="HS256",
        )

        with pytest.raises(HTTPException) as exc_info:
            decode_token(wrong_secret_token)

        assert exc_info.value.status_code == 401


class TestPasswordOperations:
    """Test cases for password hashing and verification."""

    @pytest.mark.timeout(60)
    def test_password_hash_and_verify_success(self):
        """Test successful password hashing and verification."""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password  # Should be hashed, not plain text

        # Verify the password
        assert verify_password(password, hashed) is True

    @pytest.mark.timeout(60)
    def test_password_verify_wrong_password(self):
        """Test password verification with wrong password."""
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False

    @pytest.mark.timeout(60)
    def test_password_hash_different_each_time(self):
        """Test that hashing the same password produces different hashes."""
        password = "test_password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2  # Salted hashes should be different
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    @pytest.mark.timeout(60)
    def test_verify_password_with_invalid_hash(self):
        """Test password verification with invalid hash format."""
        from pwdlib.exceptions import UnknownHashError

        password = "test_password"
        invalid_hash = "not_a_valid_hash"

        # pwdlib raises UnknownHashError for invalid hashes
        with pytest.raises(UnknownHashError):
            verify_password(password, invalid_hash)

    @pytest.mark.timeout(60)
    def test_password_operations_with_empty_strings(self):
        """Test password operations with empty strings."""
        # Hash empty password
        empty_hash = get_password_hash("")
        assert isinstance(empty_hash, str)
        assert len(empty_hash) > 0

        # Verify empty password
        assert verify_password("", empty_hash) is True
        assert verify_password("not_empty", empty_hash) is False

    @pytest.mark.timeout(60)
    def test_password_operations_with_special_characters(self):
        """Test password operations with special characters."""
        special_password = "test@#$%^&*()_+{}|:<>?[];',./"
        hashed = get_password_hash(special_password)

        assert verify_password(special_password, hashed) is True
        assert verify_password("different", hashed) is False


class TestSecretKey:
    """Test cases for secret key handling."""

    @pytest.mark.timeout(60)
    def test_get_secret_key_default(self):
        """Test getting default secret key when no file exists."""
        # Clear cache first
        get_secret_key.cache_clear()
        with mock.patch("os.path.exists", return_value=False):
            secret = get_secret_key()
            assert secret == "test_secret"

    @pytest.mark.timeout(60)
    def test_get_secret_key_from_file(self):
        """Test getting secret key from file."""
        # Clear cache first
        get_secret_key.cache_clear()
        test_secret = "file_based_secret_key"

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write(test_secret)
            temp_file = f.name

        try:
            with mock.patch("os.path.join", return_value=temp_file):
                with mock.patch("os.path.exists", return_value=True):
                    secret = get_secret_key()
                    assert secret == test_secret
        finally:
            os.unlink(temp_file)

    @pytest.mark.timeout(60)
    def test_get_secret_key_from_file_with_whitespace(self):
        """Test getting secret key from file with surrounding whitespace."""
        # Clear cache first
        get_secret_key.cache_clear()
        test_secret = "secret_with_whitespace"

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write(f"  {test_secret}  \n")
            temp_file = f.name

        try:
            with mock.patch("os.path.join", return_value=temp_file):
                with mock.patch("os.path.exists", return_value=True):
                    secret = get_secret_key()
                    assert secret == test_secret  # Should be stripped
        finally:
            os.unlink(temp_file)

    @pytest.mark.timeout(60)
    def test_get_secret_key_caching(self):
        """Test that secret key is cached using @lru_cache."""
        # Clear cache first
        get_secret_key.cache_clear()
        with mock.patch("os.path.exists", return_value=False) as mock_exists:
            # Call multiple times
            secret1 = get_secret_key()
            secret2 = get_secret_key()
            secret3 = get_secret_key()

            # Should all return the same value
            assert secret1 == secret2 == secret3 == "test_secret"

            # os.path.exists should only be called once due to caching
            assert mock_exists.call_count == 1


class TestErrorEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.timeout(60)
    async def test_get_current_user_with_none_token_parameter(self, mock_request):
        """Test get_current_user when token parameter is explicitly None."""
        with mock.patch("bec_atlas.authentication.optional_oauth2_scheme") as mock_oauth2:
            mock_oauth2.return_value = None
            mock_request.cookies = {}

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_request, None)

            assert exc_info.value.status_code == 401

    @pytest.mark.timeout(60)
    def test_decode_token_with_none(self):
        """Test decode_token with None token."""
        with pytest.raises((HTTPException, TypeError)):
            decode_token(None)  # type: ignore

    @pytest.mark.timeout(60)
    def test_get_current_user_sync_with_token_containing_null_bytes(self):
        """Test get_current_user_sync with token containing null bytes."""
        token_with_nulls = "valid.token\x00.here"

        with pytest.raises(HTTPException) as exc_info:
            get_current_user_sync(token_with_nulls)

        assert exc_info.value.status_code == 401

    @pytest.mark.timeout(60)
    def test_create_access_token_with_none_data(self):
        """Test create_access_token with None data."""
        with pytest.raises((AttributeError, TypeError)):
            create_access_token(None)  # type: ignore

    @pytest.mark.timeout(60)
    def test_create_access_token_with_negative_expiry(self):
        """Test create_access_token with negative expiry delta."""
        data = {"email": "test@example.com"}
        negative_delta = timedelta(hours=-1)

        # Should create an already-expired token
        token = create_access_token(data, negative_delta)

        # Token should be created but immediately expired when decoded
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)

        assert exc_info.value.status_code == 401

    @pytest.mark.timeout(60)
    @mock.patch("builtins.open", side_effect=IOError("Permission denied"))
    def test_get_secret_key_file_read_error(self, mock_open):
        """Test get_secret_key when file exists but cannot be read."""
        # Clear cache first
        get_secret_key.cache_clear()
        with mock.patch("os.path.exists", return_value=True):
            with pytest.raises(IOError):
                get_secret_key()
