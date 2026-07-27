import secrets
from datetime import datetime

def make_booking_no()->str:
    return f"XJ-{datetime.now().year}-{secrets.randbelow(900000)+100000}"

