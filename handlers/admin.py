from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile

from states import AdminState
from keyboards import admin_kb, receipt_admin_kb
from services.export import make_excel

router = Router()


def is_admin(user_id: int, config) -> bool:
    return user_id in config.admin_ids


@router.message(Command("admin"))
async def panel(m: Message, config):
    if not is_admin(m.from_user.id, config):
        return
    await m.answer("⚙️ <b>АДМИН ПАНЕЛ</b>", reply_markup=admin_kb())


@router.callback_query(F.data.startswith("admin:"))
async def admin_actions(c: CallbackQuery, state: FSMContext, db, config):
    if not is_admin(c.from_user.id, config):
        await c.answer("Рухсат йўқ", show_alert=True)
        return

    action = c.data.split(":", 1)[1]

    if action == "stats":
        stats = await db.stats()
        limit = await db.get_limit()
        text = (
            "📊 <b>СТАТИСТИКА</b>\n\n"
            f"👥 Рўйхатдан ўтган: {stats['users']} / {limit}\n"
            f"✅ Тасдиқланган: {stats['approved']}\n"
            f"🟡 Лидер орқали: {stats['leader_pending']}\n"
            f"📸 Чек кутилмоқда: {stats['receipt_pending']}\n"
            f"🎫 Econom: {stats['econom']}\n"
            f"💎 Business: {stats['business']}"
        )
        await c.message.answer(text)

    elif action == "users":
        rows = await db.export_rows()
        lines = [f"{r['id']}. {r['full_name']} — {r['xj_id']}" for r in rows[-30:]]
        await c.message.answer("👥 <b>ОХИРГИ ИШТИРОКЧИЛАР</b>\n\n" + ("\n".join(lines) or "Ҳали иштирокчилар йўқ."))

    elif action == "payments":
        rows = await db.pending()
        if not rows:
            await c.message.answer("Кутилаётган чеклар йўқ.")
        for row in rows:
            await c.message.answer_photo(
                row["receipt_file_id"],
                caption=(
                    f"👤 {row['full_name']}\n"
                    f"🆔 {row['xj_id']}\n"
                    f"📦 {row['package']}\n"
                    f"🔖 {row['booking_no']}"
                ),
                reply_markup=receipt_admin_kb(row["id"]),
            )

    elif action == "limit":
        await state.set_state(AdminState.set_limit)
        await c.message.answer(
            f"Жорий лимит: {await db.get_limit()}\n"
            "Янги лимитни рақамда киритинг:"
        )

    elif action == "excel":
        path = "data/xj_ishtirokchilar.xlsx"
        await make_excel(await db.export_rows(), path)
        await c.message.answer_document(FSInputFile(path), caption="📄 Иштирокчилар рўйхати")

    elif action == "broadcast":
        await state.set_state(AdminState.broadcast)
        await c.message.answer("Барча иштирокчиларга юбориладиган хабарни киритинг:")

    await c.answer()


@router.message(AdminState.set_limit)
async def set_limit(m: Message, state: FSMContext, db, config):
    if not is_admin(m.from_user.id, config):
        return
    try:
        new_limit = int(m.text)
        if not 1 <= new_limit <= 100000:
            raise ValueError
    except (TypeError, ValueError):
        await m.answer("1 дан 100000 гача рақам киритинг.")
        return

    await db.set_limit(new_limit)
    await state.clear()
    await m.answer(f"✅ Лимит {new_limit} тага ўзгартирилди.", reply_markup=admin_kb())


@router.message(AdminState.broadcast)
async def broadcast(m: Message, state: FSMContext, db, config):
    if not is_admin(m.from_user.id, config):
        return

    rows = await db.export_rows()
    sent = failed = 0
    for row in rows:
        try:
            await m.bot.copy_message(row["telegram_id"], m.chat.id, m.message_id)
            sent += 1
        except Exception:
            failed += 1

    await state.clear()
    await m.answer(f"✅ Юборилди: {sent}\n❌ Хато: {failed}", reply_markup=admin_kb())


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

    await db.set_booking_status(payment_id, "approved" if approved else "rejected")
    if approved:
        user_text = (
            "✅ Тўловингиз тасдиқланди!\n"
            f"Брон рақамингиз: <code>{payment['booking_no']}</code>\n"
            "Билетни кетиш куни ёки юқори лидерингиз орқали оласиз."
        )
        mark = "\n\n✅ ТАСДИҚЛАНДИ"
    else:
        user_text = "❌ Тўлов чеки рад этилди. Маълумотни текшириб, админ билан боғланинг."
        mark = "\n\n❌ РАД ЭТИЛДИ"

    try:
        await c.bot.send_message(payment["telegram_id"], user_text)
    except Exception:
        pass

    try:
        await c.message.edit_caption(caption=(c.message.caption or "") + mark)
    except Exception:
        pass
    await c.answer("Бажарилди")

