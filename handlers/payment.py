from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from states import Payment
from keyboards import card_kb, leader_confirm_kb, receipt_admin_kb, main_menu_kb
from services.currency import usd_rate
from services.booking import make_booking_no

router = Router()


@router.callback_query(F.data.startswith("pay_card:"))
async def card(c: CallbackQuery, config):
    package = c.data.split(":", 1)[1]
    rate = await usd_rate()
    usd = 150 if package == "econom" else 250
    uzs = round(rate * usd)
    text = (
        f"💳 <b>ТЎЛОВ МАЪЛУМОТЛАРИ</b>\n\n"
        f"Пакет: {package.upper()}\n"
        f"Сумма: {usd}$ = <b>{uzs:,} сўм</b>\n"
        f"Карта: <code>{config.card_number}</code>\n"
        f"Қабул қилувчи: <b>{config.card_holder}</b>\n\n"
        "Ушбу тўлов фақат XJ Лидерлар Конгрессида иштирок этиш учун амалга оширилади."
    ).replace(",", " ")
    await c.message.answer(text, reply_markup=card_kb(package))
    await c.answer()


@router.callback_query(F.data.startswith("send_receipt:"))
async def ask_receipt(c: CallbackQuery, state: FSMContext):
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

    data = await state.get_data()
    package = data["package"]
    rate = await usd_rate()
    usd = 150 if package == "econom" else 250
    uzs = round(rate * usd)
    booking_no = make_booking_no()

    payment_id = await db.create_booking(
        user["id"], booking_no, package, usd, uzs, rate,
        "card", "receipt_pending", m.photo[-1].file_id,
    )
    await state.clear()
    await m.answer(
        "✅ Чек қабул қилинди.\n"
        f"Брон рақамингиз: <code>{booking_no}</code>\n"
        "Админ текширувидан кейин хабар берилади.",
        reply_markup=main_menu_kb(),
    )

    caption = (
        "💳 <b>ЯНГИ ТЎЛОВ ЧЕКИ</b>\n"
        f"👤 {user['full_name']}\n"
        f"🆔 {user['xj_id']}\n"
        f"📦 {package.upper()}\n"
        f"💵 {usd}$ / {uzs:,} сўм\n"
        f"🔖 {booking_no}"
    ).replace(",", " ")

    for admin_id in config.admin_ids:
        try:
            await m.bot.send_photo(
                admin_id,
                m.photo[-1].file_id,
                caption=caption,
                reply_markup=receipt_admin_kb(payment_id),
            )
        except Exception:
            pass


@router.message(Payment.waiting_receipt)
async def need_photo(m: Message):
    await m.answer("Илтимос, чекни расм сифатида юборинг.")


@router.callback_query(F.data.startswith("pay_leader:"))
async def leader(c: CallbackQuery):
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

    package = c.data.split(":", 1)[1]
    rate = await usd_rate()
    usd = 150 if package == "econom" else 250
    uzs = round(rate * usd)
    booking_no = make_booking_no()

    await db.create_booking(
        user["id"], booking_no, package, usd, uzs, rate,
        "leader", "leader_pending",
    )
    await c.message.answer(
        "✅ Жойингиз вақтинча брон қилинди.\n\n"
        f"Брон рақамингиз: <code>{booking_no}</code>\n"
        "Ушбу рақамни сақлаб қўйинг.",
        reply_markup=main_menu_kb(),
    )

    admin_text = (
        "👤 Лидер орқали янги брон\n"
        f"{user['full_name']}\n"
        f"XJ ID: {user['xj_id']}\n"
        f"Пакет: {package.upper()}\n"
        f"Брон: {booking_no}"
    )
    for admin_id in config.admin_ids:
        try:
            await c.bot.send_message(admin_id, admin_text)
        except Exception:
            pass
    await c.answer()

