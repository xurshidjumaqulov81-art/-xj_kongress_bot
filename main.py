import asyncio,logging
from pathlib import Path
from aiogram import Bot,Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from config import load_config
from database import Database
from handlers import user,payment,admin

async def main():
    logging.basicConfig(level=logging.INFO,format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
    config=load_config(); Path(config.database_path).parent.mkdir(parents=True,exist_ok=True)
    db=Database(config.database_path,config.default_limit); await db.init()
    bot=Bot(config.bot_token,default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp=Dispatcher(storage=MemoryStorage())
    dp['db']=db; dp['config']=config
    dp.include_router(admin.router); dp.include_router(payment.router); dp.include_router(user.router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot,allowed_updates=dp.resolve_used_update_types())

if __name__=='__main__':
    try: asyncio.run(main())
    except (KeyboardInterrupt,SystemExit): pass

