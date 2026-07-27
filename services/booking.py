import secrets
from datetime import datetime


async def make_booking_no(db) -> str:
    """Базада такрорланмайдиган брон рақами яратади."""
    year = datetime.now().year
    for _ in range(30):
        number = f"XJ-{year}-{secrets.randbelow(900000) + 100000}"
        if not await db.booking_by_no(number):
            return number
    raise RuntimeError("Уникал брон рақами яратиб бўлмади")

