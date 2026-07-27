from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from keyboards import admin_kb, personal_user_kb, receipt_admin_kb
from services.export import make_excel
from states import AdminState

router = Router()


def is_admin(user_id: int, config) -> bool:
    return user_id in config.admin_ids


def status_name(status: str | None) -> str:
    return {
        None: "Билет олинмаган",
        "leader_pending": "Лидер орқали тўлов кутилмоқда",
        "receipt_pending": "Чек текширилмоқда",
        "approved": "Тасдиқланган",
        "rejected": "Рад этилган",
        "cancelled": "Бекор қилинган",
    }.get(status, status or "Номаълум")


def person_text(row) -> str:
    username = f"@{row['username']}" if row["username"] else "Йўқ"
    booking = row["booking_no"] or "Йўқ"
    package = row["package"].upper() if row["package"] else "Йўқ"
    return (
        "👤 <b>ИШТИРОКЧИ МАЪЛУМОТЛАРИ</b>\n\n"
        f"Ф.И.Ш: <b>{row['full_name']}</b>\n"
        f"Telegram ID: <code>{row['telegram_id']}</code>\n"
        f"Username: {username}\n"
        f"XJ ID: <code>{row['xj_id']}</code>\n"
        f"Квалификация: {row['qualification']}\n"
        f"Телефон: {row['phone']}\n"
        f"Вилоят: {row['region']}\n"
        f"Жинси: {row['gender']}\n"
        f"Рўйхат санаси: {row['created_at']}\n\n"
        f"Пакет: {package}\n"
        f"Брон рақами: <code>{booking}</code>\n"
        f"Ҳолати: <b>{status_name(row['status'])}</b>"
    )


async def panel_markup(db):
    return admin_kb(await db.registration_is_open())


@router.message(Command("admin"))
async def panel(m: Message, config, db):
    if not is_admin(m.from_user.id, config):
        return
    await m.answer("⚙️ <b>АДМИН ПАНЕЛ</b>", reply_markup=await panel_markup(db))


@router.callback_query(F.data.startswith("admin:"))
async def admin_actions(c: CallbackQuery, state: FSMContext, db, config):
    if not is_admin(c.from_user.id, config):
        await c.answer("Рухсат йўқ", show_alert=True)
        return
    action = c.data.split(":", 1)[1]

    if action == "stats":
        stats = await db.stats()
        limit = await db.get_limit()
        remaining = max(limit - stats["users"], 0)
        registration = "ОЧИҚ ✅" if await db.registration_is_open() else "ЁПИҚ 🔒"
        text = (
            "📊 <b>СТАТИСТИКА</b>\n\n"
            f"Рўйхатдан ўтиш: <b>{registration}</b>\n"
            f"👥 Рўйхатдан ўтган: {stats['users']} / {limit}\n"
            f"🟢 Бўш жой: {remaining}\n"
            f"🎟 Жами буюртма: {stats['bookings']}\n"
            f"✅ Тасдиқланган: {stats['approved']}\n"
            f"🟡 Лидер орқали: {stats['leader_pending']}\n"
            f"📸 Чек текширувда: {stats['receipt_pending']}\n"
            f"❌ Бекор/рад: {stats['cancelled']}\n\n"
            f"🎫 ECONOM: {stats['econom']}\n💎 BUSINESS: {stats['business']}\n"
            f"👨 Эркак: {stats['male']}\n👩 Аёл: {stats['female']}\n\n"
            f"👤 Оддий ҳамкор: {stats['partner']}\n⭐ XJ Мастер: {stats['master']}\n"
            f"💼 XJ Менежери: {stats['manager']}\n🥉 XJ Бронза менежери: {stats['bronze']}"
        )
        await c.message.answer(text)

    elif action == "users":
        rows = await db.export_rows()
        if not rows:
            await c.message.answer("Ҳали иштирокчилар йўқ.")
        else:
            lines = [f"{r['id']}. {r['full_name']} — <code>{r['xj_id']}</code>" for r in rows[-50:]]
            await c.message.answer("👥 <b>ОХИРГИ ИШТИРОКЧИЛАР</b>\n\n" + "\n".join(lines))

    elif action == "payments":
        rows = await db.pending()
        if not rows:
            await c.message.answer("Кутилаётган тўлов ва бронлар йўқ.")
        for row in rows:
            caption = (
                f"👤 <b>{row['full_name']}</b>\n"
                f"Telegram ID: <code>{row['telegram_id']}</code>\n"
                f"XJ ID: <code>{row['xj_id']}</code>\n"
                f"Квалификация: {row['qualification']}\n"
                f"Телефон: {row['phone']}\nВилоят: {row['region']}\nЖинси: {row['gender']}\n"
                f"Пакет: {row['package'].upper()}\nБрон: <code>{row['booking_no']}</code>\n"
                f"Ҳолати: {status_name(row['status'])}"
            )
            if row["receipt_file_id"]:
                await c.message.answer_photo(row["receipt_file_id"], caption=caption, reply_markup=receipt_admin_kb(row["id"]))
            else:
                await c.message.answer(caption, reply_markup=receipt_admin_kb(row["id"]))

    elif action == "limit":
        await state.set_state(AdminState.set_limit)
        await c.message.answer(f"Жорий лимит: {await db.get_limit()}\nЯнги лимитни рақамда киритинг:")

    elif action == "excel":
        path = "data/xj_ishtirokchilar.xlsx"
        await make_excel(await db.export_rows(), path)
        await c.message.answer_document(FSInputFile(path), caption="📄 Иштирокчилар рўйхати")

    elif action == "broadcast":
        await state.set_state(AdminState.broadcast)
        await c.message.answer("Барча иштирокчиларга юбориладиган хабар, расм ёки файлни юборинг:")

    elif action == "personal":
        await state.set_state(AdminState.search_person)
        await c.message.answer("XJ ID, телефон, Telegram ID ёки брон рақамини киритинг:")

    elif action == "close_registration":
        await db.set_registration_open(False)
        await c.message.answer("🔒 Рўйхатдан ўтиш тўхтатилди.", reply_markup=await panel_markup(db))

    elif action == "open_registration":
        await db.set_registration_open(True)
        await c.message.answer("🔓 Рўйхатдан ўтиш очилди.", reply_markup=await panel_markup(db))

    await c.answer()


@router.message(AdminState.set_limit)
async def set_limit(m: Message, state: FSMContext, db, config):
    if not is_admin(m.from_user.id, config):
        return
    try:
        new_limit = int((m.text or "").strip())
        if not 1 <= new_limit <= 100000:
            raise ValueError
        current_users = await db.count_users()
        if new_limit < current_users:
            await m.answer(f"Лимит рўйхатдан ўтганлар сонидан ({current_users}) кам бўлмаслиги керак.")
            return
    except ValueError:
        await m.answer("1 дан 100000 гача бутун рақам киритинг.")
        return
    await db.set_limit(new_limit)
    await state.clear()
    await m.answer(f"✅ Лимит {new_limit} тага ўзгартирилди.", reply_markup=await panel_markup(db))


@router.message(AdminState.broadcast)
async def broadcast(m: Message, state: FSMContext, db, config):
    if not is_admin(m.from_user.id, config):
        return
    rows = await db.export_rows()
    sent = failed = 0
    telegram_ids = {row["telegram_id"] for row in rows}
    for telegram_id in telegram_ids:
        try:
            await m.bot.copy_message(telegram_id, m.chat.id, m.message_id)
            sent += 1
        except Exception:
            failed += 1
    await state.clear()
    await m.answer(f"✅ Юборилди: {sent}\n❌ Хато: {failed}", reply_markup=await panel_markup(db))


@router.message(AdminState.search_person)
async def search_person(m: Message, state: FSMContext, db, config):
    if not is_admin(m.from_user.id, config):
        return
    row = await db.find_user(m.text or "")
    if not row:
        await m.answer("❌ Иштирокчи топилмади. Қайта киритинг ёки /admin босинг.")
        return
    await state.clear()
    await m.answer(person_text(row), reply_markup=personal_user_kb(row["id"], row["booking_id"]))


@router.callback_query(F.data.startswith("personal_write:"))
async def personal_write(c: CallbackQuery, state: FSMContext, config):
    if not is_admin(c.from_user.id, config):
        await c.answer("Рухсат йўқ", show_alert=True)
        return
    await state.set_state(AdminState.personal_message)
    await state.update_data(target_user_id=int(c.data.split(":", 1)[1]))
    await c.message.answer("Ушбу иштирокчига юбориладиган хабар, расм ёки файлни юборинг:")
    await c.answer()


@router.message(AdminState.personal_message)
async def send_personal(m: Message, state: FSMContext, db, config):
    if not is_admin(m.from_user.id, config):
        return
    data = await state.get_data()
    row = await db.one("SELECT * FROM users WHERE id=?", (data["target_user_id"],))
    if not row:
        await state.clear()
        await m.answer("Иштирокчи топилмади.")
        return
    try:
        await m.bot.copy_message(row["telegram_id"], m.chat.id, m.message_id)
        await m.answer("✅ Хабар юборилди.")
    except Exception:
        await m.answer("❌ Хабарни юбориб бўлмади.")
    await state.clear()


@router.callback_query(F.data.startswith("receipt_ok:") | F.data.startswith("receipt_no:"))
async def receipt_decision(c: CallbackQuery, db, config):
    if not is_admin(c.from_user.id, config):
        await c.answer("Рухсат йўқ", show_alert=True)
        return
    approved = c.data.startswith("receipt_ok:")
    payment_id = int(c.data.split(":", 1)[1])
    payment = await db.payment(payment_id)
    if not payment:
        await c.answer("Тўлов топилмади", show_alert=True)
        return
    if payment["status"] in ("approved", "rejected", "cancelled"):
        await c.answer("Бу буюртма аввал кўриб чиқилган", show_alert=True)
        return
    await db.set_booking_status(payment_id, "approved" if approved else "cancelled")
    if approved:
        user_text = (
            "✅ Тўловингиз тасдиқланди!\n"
            f"Брон рақамингиз: <code>{payment['booking_no']}</code>\n"
            "Билетни кетиш куни ёки юқори лидерингиз орқали оласиз."
        )
        mark = "\n\n✅ ТАСДИҚЛАНДИ"
    else:
        user_text = (
            "❌ Бронингиз админ томонидан бекор қилинди.\n"
            "Бекор қилинган бронни қайта расмийлаштириш мумкин эмас."
        )
        mark = "\n\n❌ БЕКОР ҚИЛИНДИ"
    try:
        await c.bot.send_message(payment["telegram_id"], user_text)
    except Exception:
        pass
    try:
        if c.message.photo:
            await c.message.edit_caption(caption=(c.message.caption or "") + mark)
        else:
            await c.message.edit_text((c.message.text or "") + mark)
    except Exception:
        pass
    await c.answer("Бажарилди")

