# XJ Лидерлар Конгресси Telegram боти

Aiogram 3 асосида тайёрланган рўйхатдан ўтиш, дастур, пакет, тўлов ва админ панели боти.

## Локал ишга тушириш

1. Python 3.11+ ўрнатинг.
2. `.env.example` файлини `.env` номи билан нусхаланг.
3. `.env` ичига BotFather берган `BOT_TOKEN`ни киритинг.
4. Пакетларни ўрнатинг: `pip install -r requirements.txt`
5. Ишга туширинг: `python main.py`

## Railway

GitHub репозиторийга барча файлларни юкланг. Railway'да New Project → Deploy from GitHub танланг. Variables бўлимига қуйидагиларни қўшинг:

- `BOT_TOKEN`
- `ADMIN_IDS=199169309`
- `CARD_NUMBER=9860600432588041`
- `CARD_HOLDER=JUMAQULOV SHUHRAT`
- `DEFAULT_LIMIT=100`
- `DATABASE_PATH=data/congress.db`

Эслатма: Railway'да SQLite файл доимий сақланиши учун Volume улаш тавсия этилади. Volume mount path: `/app/data`. Катта ишлаб чиқариш муҳити учун PostgreSQL яхшироқ.

## Админ

Telegram'да `/admin` буйруғи. Админ ID: `199169309`.

