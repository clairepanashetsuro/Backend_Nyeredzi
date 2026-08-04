import random

from datetime import datetime, timedelta, timezone

from ivhuRedu.models.otp import OTP


def generate_code():

    return str(random.randint(100000, 999999))


def create_otp(db, user, purpose):

    code = generate_code()

    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(minutes=10)
    )

    otp = OTP(
        user_id=user.id,
        code=code,
        purpose=purpose,
        expires_at=expires_at,
    )

    db.add(otp)
    db.commit()

    return otp