import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from ivhuRedu.models.field_report import IssueType, StatusEnum, SyncStatus
from ivhuRedu.models.user import UserType
from ivhuRedu.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    Token,
    VerifyResetOTPRequest,
)
from ivhuRedu.schemas.field_report import FieldReportCreate, FieldReportUpdate
from ivhuRedu.schemas.location import (
    LocationCreate,
    LocationUpdate,
    LocationGeocodeRequest,
)
from ivhuRedu.schemas.sms import AlertSendRequest
from ivhuRedu.schemas.user import UserCreate, UserUpdate, UserRead


@pytest.mark.parametrize(
    "pw, ok", [("a" * 7, False), ("a" * 8, True), ("a" * 128, True), ("a" * 129, False)]
)
def test_change_password_new_password_length_bounds(pw, ok):
    if ok:
        assert ChangePasswordRequest(old_password="x", new_password=pw)
    else:
        with pytest.raises(ValidationError):
            ChangePasswordRequest(old_password="x", new_password=pw)


@pytest.mark.parametrize(
    "phone, ok",
    [("1234567", True), ("1" * 20, True), ("123456", False), ("1" * 21, False)],
)
def test_forgot_password_phone_length_bounds(phone, ok):
    if ok:
        assert ForgotPasswordRequest(phone_number=phone)
    else:
        with pytest.raises(ValidationError):
            ForgotPasswordRequest(phone_number=phone)


@pytest.mark.parametrize("code", ["12345", "1234567", "12345a", "abcdef", "12 456"])
def test_verify_reset_otp_rejects_non_six_digit_codes(code):
    with pytest.raises(ValidationError):
        VerifyResetOTPRequest(phone_number="+263771234567", otp_code=code)


def test_verify_reset_otp_accepts_six_digits_with_leading_zero():
    assert (
        VerifyResetOTPRequest(phone_number="+263771234567", otp_code="001234").otp_code
        == "001234"
    )


def test_reset_password_requires_token_and_min_length():
    with pytest.raises(ValidationError):
        ResetPasswordRequest(reset_token="", new_password="longenough")
    with pytest.raises(ValidationError):
        ResetPasswordRequest(reset_token="t", new_password="short")
    assert ResetPasswordRequest(reset_token="t", new_password="longenough")


def test_token_schema_defaults_optional_fields_to_none():
    t = Token(
        access_token="a",
        refresh_token="r",
        token_type="bearer",
        role="admin",
        must_change_password=False,
    )
    assert t.offline_token is None and t.worker_id is None


BASE = dict(first_name="Tendai", last_name="Moyo", phone_number="+263771234567")


@pytest.mark.parametrize(
    "phone", ["+263771234567", "0771234567", "1234567", "123456789012345"]
)
def test_user_create_accepts_valid_phone_numbers(phone):
    assert UserCreate(**{**BASE, "phone_number": phone}).phone_number == phone


@pytest.mark.parametrize(
    "phone",
    [
        "",
        "12345",
        "+12",
        "abc1234567",
        "077 123 4567",
        "+263-771-234567",
        "1" * 16,
        "++263771234567",
    ],
)
def test_user_create_rejects_invalid_phone_numbers(phone):
    with pytest.raises(ValidationError):
        UserCreate(**{**BASE, "phone_number": phone})


@pytest.mark.parametrize("field", ["first_name", "last_name"])
@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_user_create_rejects_blank_names(field, blank):
    with pytest.raises(ValidationError):
        UserCreate(**{**BASE, field: blank})


def test_user_create_password_is_optional_but_min_8_when_given():
    assert UserCreate(**BASE).password is None
    assert UserCreate(**BASE, password="12345678").password == "12345678"
    with pytest.raises(ValidationError):
        UserCreate(**BASE, password="1234567")


def test_user_create_validates_email_format():
    assert UserCreate(**BASE, email="a@b.co").email == "a@b.co"
    with pytest.raises(ValidationError):
        UserCreate(**BASE, email="not-an-email")


def test_user_update_all_fields_optional_and_validated():
    assert UserUpdate().model_dump(exclude_none=True) == {}
    with pytest.raises(ValidationError):
        UserUpdate(phone_number="bad")
    with pytest.raises(ValidationError):
        UserUpdate(password="short")


def test_user_read_from_attributes_and_enum_parsing():
    class Obj:
        id = uuid.uuid4()
        first_name = "A"
        last_name = "B"
        email = None
        phone_number = "+263771234567"
        user_type = "farmer"
        created_at = updated_at = datetime.now(timezone.utc)
        extension_worker = None
        farmer = None

    assert UserRead.model_validate(Obj()).user_type is UserType.FARMER


def test_user_read_rejects_unknown_user_type():
    with pytest.raises(ValidationError):
        UserRead(
            id=uuid.uuid4(),
            first_name="A",
            last_name="B",
            phone_number="1234567",
            user_type="superuser",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )


@pytest.mark.parametrize(
    "lat, lon, ok",
    [
        (0, 0, True),
        (90, 180, True),
        (-90, -180, True),
        (90.0001, 0, False),
        (-90.0001, 0, False),
        (0, 180.0001, False),
        (0, -180.0001, False),
    ],
)
def test_location_coordinate_bounds(lat, lon, ok):
    if ok:
        assert LocationCreate(latitude=lat, longitude=lon, address="x")
    else:
        with pytest.raises(ValidationError):
            LocationCreate(latitude=lat, longitude=lon, address="x")


def test_location_address_max_length_250():
    assert LocationCreate(latitude=0, longitude=0, address="a" * 250)
    with pytest.raises(ValidationError):
        LocationCreate(latitude=0, longitude=0, address="a" * 251)


def test_location_update_partial_and_bounds():
    assert LocationUpdate().model_dump(exclude_none=True) == {}
    with pytest.raises(ValidationError):
        LocationUpdate(latitude=100)


def test_geocode_request_requires_non_empty_address():
    with pytest.raises(ValidationError):
        LocationGeocodeRequest(address="")


def test_field_report_create_defaults():
    r = FieldReportCreate(worker_id=uuid.uuid4(), description_type="pest")
    assert r.sync_status is SyncStatus.PENDING_SYNC and r.status is StatusEnum.PENDING
    assert r.farmer_id is None and r.issue_type is None


def test_field_report_create_requires_worker_and_description_type():
    with pytest.raises(ValidationError):
        FieldReportCreate(description_type="x")
    with pytest.raises(ValidationError):
        FieldReportCreate(worker_id=uuid.uuid4())


@pytest.mark.parametrize("issue", [i.value for i in IssueType])
def test_field_report_accepts_every_issue_type(issue):
    assert (
        FieldReportCreate(
            worker_id=uuid.uuid4(), description_type="x", issue_type=issue
        ).issue_type.value
        == issue
    )


def test_field_report_rejects_unknown_issue_type_and_bad_uuid():
    with pytest.raises(ValidationError):
        FieldReportCreate(
            worker_id=uuid.uuid4(), description_type="x", issue_type="Alien Invasion"
        )
    with pytest.raises(ValidationError):
        FieldReportCreate(worker_id="not-a-uuid", description_type="x")


def test_field_report_update_is_fully_optional():
    assert FieldReportUpdate().model_dump(exclude_none=True) == {}


def test_alert_send_request_requires_at_least_one_phone_number():
    with pytest.raises(ValidationError):
        AlertSendRequest(message="hi", phone_numbers=[])
    assert AlertSendRequest(message="hi", phone_numbers=["+263771234567"])
