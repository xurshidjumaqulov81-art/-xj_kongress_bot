import aiosqlite
from datetime import datetime

class Database:
    def __init__(self,path:str,default_limit:int=100): self.path=path; self.default_limit=default_limit
    async def init(self):
        async with aiosqlite.connect(self.path) as db:
            await db.executescript("""
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS users(
              id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER UNIQUE NOT NULL, username TEXT,
              full_name TEXT NOT NULL, xj_id TEXT UNIQUE NOT NULL, qualification TEXT NOT NULL, phone TEXT UNIQUE NOT NULL,
              region TEXT NOT NULL, gender TEXT NOT NULL, blocked INTEGER DEFAULT 0, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS bookings(
              id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE NOT NULL, booking_no TEXT UNIQUE NOT NULL,
              package TEXT NOT NULL, amount_usd INTEGER NOT NULL, amount_uzs INTEGER NOT NULL, usd_rate REAL NOT NULL,
              payment_method TEXT NOT NULL, status TEXT NOT NULL, receipt_file_id TEXT, created_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id));
            """)
            await db.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('limit',?)",(str(self.default_limit),))
            await db.commit()
    async def one(self,q,p=()):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory=aiosqlite.Row
            async with db.execute(q,p) as c: return await c.fetchone()
    async def all(self,q,p=()):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory=aiosqlite.Row
            async with db.execute(q,p) as c: return await c.fetchall()
    async def execute(self,q,p=()):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute(q,p); await db.commit(); return cur.lastrowid
    async def get_limit(self): return int((await self.one("SELECT value FROM settings WHERE key='limit'"))[0])
    async def set_limit(self,n): await self.execute("UPDATE settings SET value=? WHERE key='limit'",(str(n),))
    async def count_users(self): return (await self.one("SELECT COUNT(*) c FROM users"))['c']
    async def add_user(self,tg,username,data):
        return await self.execute("INSERT INTO users(telegram_id,username,full_name,xj_id,qualification,phone,region,gender,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
          (tg,username,data['full_name'],data['xj_id'],data['qualification'],data['phone'],data['region'],data['gender'],datetime.now().isoformat(timespec='seconds')))
    async def user_by_tg(self,tg): return await self.one("SELECT * FROM users WHERE telegram_id=?",(tg,))
    async def user_by_xj(self,xj): return await self.one("SELECT * FROM users WHERE lower(xj_id)=lower(?)",(xj,))
    async def user_by_phone(self,p): return await self.one("SELECT * FROM users WHERE phone=?",(p,))
    async def create_booking(self,user_id,no,package,usd,uzs,rate,method,status,receipt=None):
        old=await self.one("SELECT * FROM bookings WHERE user_id=?",(user_id,))
        if old:
            await self.execute("UPDATE bookings SET booking_no=?,package=?,amount_usd=?,amount_uzs=?,usd_rate=?,payment_method=?,status=?,receipt_file_id=?,created_at=? WHERE user_id=?",
              (no,package,usd,uzs,rate,method,status,receipt,datetime.now().isoformat(timespec='seconds'),user_id)); return old['id']
        return await self.execute("INSERT INTO bookings(user_id,booking_no,package,amount_usd,amount_uzs,usd_rate,payment_method,status,receipt_file_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
          (user_id,no,package,usd,uzs,rate,method,status,receipt,datetime.now().isoformat(timespec='seconds')))
    async def booking_by_user(self,user_id): return await self.one("SELECT * FROM bookings WHERE user_id=?",(user_id,))
    async def payment(self,pid): return await self.one("SELECT b.*,u.telegram_id,u.full_name,u.xj_id,u.phone FROM bookings b JOIN users u ON u.id=b.user_id WHERE b.id=?",(pid,))
    async def pending(self): return await self.all("SELECT b.*,u.telegram_id,u.full_name,u.xj_id FROM bookings b JOIN users u ON u.id=b.user_id WHERE b.status='receipt_pending' ORDER BY b.id")
    async def set_booking_status(self,pid,status): await self.execute("UPDATE bookings SET status=? WHERE id=?",(status,pid))
    async def stats(self):
        return await self.one("""SELECT (SELECT COUNT(*) FROM users) users, (SELECT COUNT(*) FROM bookings WHERE status='approved') approved,
        (SELECT COUNT(*) FROM bookings WHERE status='leader_pending') leader_pending,(SELECT COUNT(*) FROM bookings WHERE status='receipt_pending') receipt_pending,
        (SELECT COUNT(*) FROM bookings WHERE package='econom') econom,(SELECT COUNT(*) FROM bookings WHERE package='business') business""")
    async def export_rows(self): return await self.all("SELECT u.*,b.booking_no,b.package,b.amount_usd,b.amount_uzs,b.payment_method,b.status FROM users u LEFT JOIN bookings b ON b.user_id=u.id ORDER BY u.id")

