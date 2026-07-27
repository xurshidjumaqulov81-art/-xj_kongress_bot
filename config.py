from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: set[int]
    card_number: str
    card_holder: str
    default_limit: int
    database_path: str
    fallback_usd_rate: float


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token or token == "PASTE_YOUR_BOT_TOKEN_HERE":
        raise RuntimeError("BOT_TOKEN .env файлида киритилмаган")

    admin_ids = {
        int(value.strip())
        for value in os.getenv("ADMIN_IDS", "199169309").split(",")
        if value.strip()
    }

    return Config(
        bot_token=token,
        admin_ids=admin_ids,
        card_number=os.getenv("CARD_NUMBER", "9860600432588041").strip(),
        card_holder=os.getenv("CARD_HOLDER", "JUMAQULOV SHUHRAT").strip(),
        default_limit=int(os.getenv("DEFAULT_LIMIT", "100")),
        database_path=os.getenv("DATABASE_PATH", "data/congress.db").strip(),
        fallback_usd_rate=float(os.getenv("FALLBACK_USD_RATE", "12500")),
    )

