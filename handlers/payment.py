from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards import booked_menu_kb, card_kb, leader_confirm_kb, main_menu_kb, receipt_admin_kb
from services.booking import make_booking_no
from services.currency import usd_rate
from states import Payment

router = Router()


def status_text(status: str) -> str:
    return {
        "leader_pending": "Лидер орқали брон қилинган",
        "receipt_pending": "Чек текширилмоқда",
        "approved": "Тўлов тасдиқланган",
        "rejected": "Рад этилган",
        "cancelled": "Брон бекор қилинган",
    }.get(status, status)


def full_admin_text(user, package: str, usd: int, uzs: int, rate: float, method: str, booking_no: str) -> str:
    username = f"@{user['username']}" if user["username"] else "Йўқ"
    return (
        "👤 <b>ЯНГИ БРОН / ТЎЛОВ</b>\n\n"
        f"Ф.И.Ш: <b>{user['full_name']}</b>\n"
        f"Telegram ID: <code>{user['telegram_id']}</code>\n"
        f"Username: {username}\n"
        f"XJ ID: <code>{user['xj_id']}</code>\n"
        f"Квалификация: {user['qualification']}\n"
        f"Телефон: {user['phone']}\n"
        f"Вилоят: {user['region']}\n"
        f"Жинси: {user['gender']}\n\n"
        f"Пакет: <b>{package.upper()}</b>\n"
        f"Нархи: {usd}$ / {uzs:,} сўм\n"
        f"USD курси: {rate:,.2f} сўм\n"
        f"Тўлов усули: {method}\n"
        f"Брон рақами: <code>{booking_no}</code>\n"
        "Ҳолати: <b>Тасдиқ кутилмоқда</b>"
    ).replace(",", " ")


async def existing_order(c: CallbackQuery, db, user) -> bool:
    booking = await db.booking_by_user(user["id"])
    if not booking:
        return False
    await c.message.answer(
        "⚠️ Сиз аввал билет буюртмасини расмийлаштиргансиз.\n\n"
        f"📦 Пакет: <b>{booking['package'].upper()}</b>\n"
        f"📌 Ҳолати: <b>{status_text(booking['status'])}</b>\n"
        f"🔖 Брон рақами: <code>{booking['booking_no']}</code>\n\n"
        "Бир иштирокчи фақат битта билет олиши мумкин.",
        reply_markup=booked_menu_kb(),
    )
    await c.answer()
    return True


@router.callback_query(F.data.startswith("pay_card:"))
async def card(c: CallbackQuery, db, config):
    user = await db.user_by_tg(c.from_user.id)
    if not user:
        await c.answer("Аввал рўйхатдан ўтинг", show_alert=True)
        return
    if await existing_order(c, db, user):
        return
    package = c.data.split(":", 1)[1]
    rate = await usd_rate(config.fallback_usd_rate)
    usd = 150 if package == "econom" else 250
    uzs = round(rate * usd)
    text = (
        "💳 <b>ТЎЛОВ МАЪЛУМОТЛАРИ</b>\n\n"
        f"Пакет: {package.upper()}\nСумма: {usd}$ = <b>{uzs:,} сўм</b>\n"
        f"Карта: <code>{config.card_number}</code>\n"
        f"Қабул қилувчи: <b>{config.card_holder}</b>\n\n"
        "Ушбу тўлов фақат XJ Лидерлар Конгрессида иштирок этиш учун амалга оширилади."
    ).replace(",", " ")
    await c.message.answer(text, reply_markup=card_kb(package))
    await c.answer()


@router.callback_query(F.data.startswith("send_receipt:"))
async def ask_receipt(c: CallbackQuery, state: FSMContext, db):
    user = await db.user_by_tg(c.from_user.id)
    if not user:
        await c.answer("Аввал рўйхатдан ўтинг", show_alert=True)
        return
    if await existing_order(c, db, user):
        return
    await state.set_state(Payment.waiting_receipt)
    await state.update_data(package=c.data.split(":", 1)[1])
    await c.message.answer("📸 Тўлов чекини расм кўринишида юборинг.")
    await c.answer()


@router.message(Payment.waiting_receipt, F.photo)
async def receipt(m: Message, state: FSMContext, db, config):
    user = await db.user_by_tg(m.from_user.id)
    if not user:
        await m.answer("Аввал рўйхатдан ўтинг.")
        return
    old = await db.booking_by_user(user["id"])
    if old:
        await state.clear()
        await m.answer(
            f"⚠️ Сизда аввалдан буюртма бор.\nБрон рақами: <code>{old['booking_no']}</code>",
            reply_markup=booked_menu_kb(),
        )
        return
    data = await state.get_data()
    package = data["package"]
    rate = await usd_rate(config.fallback_usd_rate)
    usd = 150 if package == "econom" else 250
    uzs = round(rate * usd)
    booking_no = await make_booking_no(db)
    payment_id = await db.create_booking(
        user["id"], booking_no, package, usd, uzs, rate,
        "card", "receipt_pending", m.photo[-1].file_id,
    )
    await state.clear()
    if not payment_id:
        old = await db.booking_by_user(user["id"])
        await m.answer(
            f"⚠️ Буюртма аввал яратилган.\nБрон рақами: <code>{old['booking_no']}</code>",
            reply_markup=booked_menu_kb(),
        )
        return
    await m.answer(
        "✅ Чек қабул қилинди.\n"
        f"Брон рақамингиз: <code>{booking_no}</code>\n"
        "Админ текширувидан кейин хабар берилади.",
        reply_markup=booked_menu_kb(),
    )
    caption = full_admin_text(user, package, usd, uzs, rate, "Карта орқали", booking_no)
    for admin_id in config.admin_ids:
        try:
            await m.bot.send_photo(admin_id, m.photo[-1].file_id, caption=caption, reply_markup=receipt_admin_kb(payment_id))
        except Exception:
            pass


@router.message(Payment.waiting_receipt)
async def need_photo(m: Message):
    await m.answer("Илтимос, чекни расм сифатида юборинг.")


@router.callback_query(F.data.startswith("pay_leader:"))
async def leader(c: CallbackQuery, db):
    user = await db.user_by_tg(c.from_user.id)
    if not user:
        await c.answer("Аввал рўйхатдан ўтинг", show_alert=True)
        return
    if await existing_order(c, db, user):
        return
    package = c.data.split(":", 1)[1]
    text = """🔐 <b>ЛИДЕР ОРҚАЛИ БРОН</b>

Тўлов юқори лидерингиз орқали <b>31 июль 2026</b> гача амалга оширилиши керак.

Тўлов тасдиқланмаса, админ бронни бекор қилади. Бекор қилинган бронни қайта расмийлаштириб бўлмайди.

Билет бот орқали юборилмайди. Билет брон рақами асосида кетиш куни ёки юқори лидер орқали берилади."""
    await c.message.answer(text, reply_markup=leader_confirm_kb(package))
    await c.answer()


@router.callback_query(F.data.startswith("leader_confirm:"))
async def leader_ok(c: CallbackQuery, db, config):
    user = await db.user_by_tg(c.from_user.id)
    if not user:
        await c.answer("Аввал рўйхатдан ўтинг", show_alert=True)
        return
    if await existing_order(c, db, user):
        return
    package = c.data.split(":", 1)[1]
    rate = await usd_rate(config.fallback_usd_rate)
    usd = 150 if package == "econom" else 250
    uzs = round(rate * usd)
    booking_no = await make_booking_no(db)
    booking_id = await db.create_booking(
        user["id"], booking_no, package, usd, uzs, rate,
        "leader", "leader_pending",
    )
    if not booking_id:
        old = await db.booking_by_user(user["id"])
        await c.message.answer(
            f"⚠️ Сизда аввалдан буюртма бор.\nБрон рақами: <code>{old['booking_no']}</code>",
            reply_markup=booked_menu_kb(),
        )
        await c.answer()
        return
    await c.message.answer(
        "🎉 <b>ТАБРИКЛАЙМИЗ!</b>\n\n"
        "Сиз XJ Лидерлар Конгрессига муваффақиятли рўйхатдан ўтдингиз.\n\n"
        "✅ Жойингиз расмий равишда брон қилинди.\n\n"
        "🎟 <b>Брон рақамингиз:</b>\n"
        f"<code>{booking_no}</code>\n\n"
        "⚠️ Ушбу брон рақамини йўқотманг ва эҳтиёт қилиб сақланг. "
        "Конгрессда иштирок этишингиз ҳамда билетингизни кетиш куни ёки "
        "юқори лидерингиз орқали олишингиз учун шу рақам керак бўлади.\n\n"
        "🏆 XJ Лидерлар Конгрессида янги куч, янги мақсад ва янги натижалар билан "
        "янада кучли лидер бўлиб қайта туғилишингизни тилаймиз!\n\n"
        "XJ оиласига бўлган ишончингиз учун раҳмат!",
        reply_markup=booked_menu_kb(),
    )
    admin_text = full_admin_text(user, package, usd, uzs, rate, "Юқори лидер орқали", booking_no)
    for admin_id in config.admin_ids:
        try:
            await c.bot.send_message(admin_id, admin_text, reply_markup=receipt_admin_kb(booking_id))
        except Exception:
            pass
    await c.answer()

