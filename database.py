import os
from datetime import datetime
from typing import Optional

import aiosqlite


class Database:
    def __init__(self, path: str, default_limit: int = 100):
        self.path = path
        self.default_limit = default_limit

    async def init(self):
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            await db.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings(
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS users(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    full_name TEXT NOT NULL,
                    xj_id TEXT UNIQUE NOT NULL,
                    qualification TEXT NOT NULL,
                    phone TEXT UNIQUE NOT NULL,
                    region TEXT NOT NULL,
                    gender TEXT NOT NULL,
                    blocked INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS bookings(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    booking_no TEXT UNIQUE NOT NULL,
                    package TEXT NOT NULL,
                    amount_usd INTEGER NOT NULL,
                    amount_uzs INTEGER NOT NULL,
                    usd_rate REAL NOT NULL,
                    payment_method TEXT NOT NULL,
                    status TEXT NOT NULL,
                    receipt_file_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                );
                """
            )
            await db.execute(
                "INSERT OR IGNORE INTO settings(key,value) VALUES('limit', ?)",
                (str(self.default_limit),),
            )
            await db.execute(
                "INSERT OR IGNORE INTO settings(key,value) VALUES('registration_open', '1')"
            )

            # Эски база учун енгил миграция.
            columns = await db.execute_fetchall("PRAGMA table_info(bookings)")
            names = {row[1] for row in columns}
            if "updated_at" not in names:
                await db.execute("ALTER TABLE bookings ADD COLUMN updated_at TEXT")

            await db.commit()

    async def one(self, query: str, params=()):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                return await cursor.fetchone()

    async def all(self, query: str, params=()):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                return await cursor.fetchall()

    async def execute(self, query: str, params=()):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            cursor = await db.execute(query, params)
            await db.commit()
            return cursor.lastrowid

    async def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        row = await self.one("SELECT value FROM settings WHERE key=?", (key,))
        return row["value"] if row else default

    async def set_setting(self, key: str, value: str):
        await self.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    async def get_limit(self) -> int:
        return int(await self.get_setting("limit", str(self.default_limit)))

    async def set_limit(self, number: int):
        await self.set_setting("limit", str(number))

    async def registration_is_open(self) -> bool:
        return await self.get_setting("registration_open", "1") == "1"

    async def set_registration_open(self, is_open: bool):
        await self.set_setting("registration_open", "1" if is_open else "0")

    async def count_users(self) -> int:
        row = await self.one("SELECT COUNT(*) AS count FROM users")
        return row["count"]

    async def add_user(self, telegram_id: int, username: Optional[str], data: dict):
        return await self.execute(
            """
            INSERT INTO users(
                telegram_id, username, full_name, xj_id, qualification,
                phone, region, gender, created_at
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                telegram_id,
                username,
                data["full_name"],
                data["xj_id"],
                data["qualification"],
                data["phone"],
                data["region"],
                data["gender"],
                datetime.now().isoformat(timespec="seconds"),
            ),
        )

    async def user_by_tg(self, telegram_id: int):
        return await self.one("SELECT * FROM users WHERE telegram_id=?", (telegram_id,))

    async def user_by_xj(self, xj_id: str):
        return await self.one("SELECT * FROM users WHERE xj_id=?", (xj_id,))

    async def user_by_phone(self, phone: str):
        return await self.one("SELECT * FROM users WHERE phone=?", (phone,))

    async def find_user(self, value: str):
        value = value.strip()
        digits = "".join(ch for ch in value if ch.isdigit())
        phone = f"+{digits}" if digits else value
        booking_value = value.upper()
        return await self.one(
            """
            SELECT DISTINCT u.*, b.id AS booking_id, b.booking_no, b.package,
                   b.amount_usd, b.amount_uzs, b.usd_rate, b.payment_method,
                   b.status, b.created_at AS booking_created_at
            FROM users u
            LEFT JOIN bookings b ON b.user_id=u.id
            WHERE u.xj_id=? OR u.phone=? OR CAST(u.telegram_id AS TEXT)=?
               OR upper(b.booking_no)=?
            LIMIT 1
            """,
            (value, phone, value, booking_value),
        )

    async def booking_by_user(self, user_id: int):
        return await self.one("SELECT * FROM bookings WHERE user_id=?", (user_id,))

    async def booking_by_no(self, booking_no: str):
        return await self.one("SELECT * FROM bookings WHERE booking_no=?", (booking_no,))

    async def create_booking(
        self,
        user_id: int,
        booking_no: str,
        package: str,
        amount_usd: int,
        amount_uzs: int,
        usd_rate: float,
        payment_method: str,
        status: str,
        receipt: Optional[str] = None,
    ):
        """Бир иштирокчига фақат битта буюртма яратади."""
        now = datetime.now().isoformat(timespec="seconds")
        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            db.row_factory = aiosqlite.Row
            await db.execute("BEGIN IMMEDIATE")
            old = await (
                await db.execute("SELECT * FROM bookings WHERE user_id=?", (user_id,))
            ).fetchone()
            if old:
                await db.rollback()
                return None
            try:
                cursor = await db.execute(
                    """
                    INSERT INTO bookings(
                        user_id, booking_no, package, amount_usd, amount_uzs,
                        usd_rate, payment_method, status, receipt_file_id,
                        created_at, updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        user_id,
                        booking_no,
                        package,
                        amount_usd,
                        amount_uzs,
                        usd_rate,
                        payment_method,
                        status,
                        receipt,
                        now,
                        now,
                    ),
                )
                await db.commit()
                return cursor.lastrowid
            except aiosqlite.IntegrityError:
                await db.rollback()
                return None

    async def payment(self, payment_id: int):
        return await self.one(
            """
            SELECT b.*, u.telegram_id, u.username, u.full_name, u.xj_id,
                   u.qualification, u.phone, u.region, u.gender
            FROM bookings b
            JOIN users u ON u.id=b.user_id
            WHERE b.id=?
            """,
            (payment_id,),
        )

    async def pending(self):
        return await self.all(
            """
            SELECT b.*, u.telegram_id, u.username, u.full_name, u.xj_id,
                   u.qualification, u.phone, u.region, u.gender
            FROM bookings b
            JOIN users u ON u.id=b.user_id
            WHERE b.status IN ('receipt_pending','leader_pending')
            ORDER BY b.id
            """
        )

    async def set_booking_status(self, payment_id: int, status: str):
        await self.execute(
            "UPDATE bookings SET status=?, updated_at=? WHERE id=?",
            (status, datetime.now().isoformat(timespec="seconds"), payment_id),
        )

    async def stats(self):
        return await self.one(
            """
            SELECT
              (SELECT COUNT(*) FROM users) AS users,
              (SELECT COUNT(*) FROM bookings) AS bookings,
              (SELECT COUNT(*) FROM bookings WHERE status='approved') AS approved,
              (SELECT COUNT(*) FROM bookings WHERE status='leader_pending') AS leader_pending,
              (SELECT COUNT(*) FROM bookings WHERE status='receipt_pending') AS receipt_pending,
              (SELECT COUNT(*) FROM bookings WHERE status IN ('rejected','cancelled')) AS cancelled,
              (SELECT COUNT(*) FROM bookings WHERE package='econom') AS econom,
              (SELECT COUNT(*) FROM bookings WHERE package='business') AS business,
              (SELECT COUNT(*) FROM users WHERE gender='Эркак') AS male,
              (SELECT COUNT(*) FROM users WHERE gender='Аёл') AS female,
              (SELECT COUNT(*) FROM users WHERE qualification='ОДДИЙ ҲАМКОР') AS partner,
              (SELECT COUNT(*) FROM users WHERE qualification='XJ МАСТЕР') AS master,
              (SELECT COUNT(*) FROM users WHERE qualification='XJ МЕНЕЖЕРИ') AS manager,
              (SELECT COUNT(*) FROM users WHERE qualification='XJ БРОНЗА МЕНЕЖЕРИ') AS bronze
            """
        )

    async def export_rows(self):
        return await self.all(
            """
            SELECT u.*, b.id AS booking_id, b.booking_no, b.package,
                   b.amount_usd, b.amount_uzs, b.usd_rate, b.payment_method,
                   b.status, b.created_at AS booking_created_at
            FROM users u
            LEFT JOIN bookings b ON b.user_id=u.id
            ORDER BY u.id
            """
        )

