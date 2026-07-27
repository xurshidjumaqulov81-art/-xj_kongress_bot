import re

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile, ReplyKeyboardRemove

from states import Registration
from texts import WELCOME, PROGRAMS, PACKAGE_COMMON, OFFER
from keyboards import (
    start_kb,
    qualification_kb,
    phone_kb,
    regions_kb,
    gender_kb,
    confirm_kb,
    main_menu_kb,
    back_menu_kb,
    packages_kb,
    payment_method_kb,
)
from services.currency import usd_rate

router = Router()


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    try:
        await message.answer_photo(
            FSInputFile("assets/logo.png"),
            caption=WELCOME,
            reply_markup=start_kb(),
        )
    except Exception:
        await message.answer(WELCOME, reply_markup=start_kb())


@router.callback_query(F.data == "register")
async def registration_start(callback: CallbackQuery, state: FSMContext, db):
    if await db.user_by_tg(callback.from_user.id):
        await callback.message.answer(
            "✅ Сиз аввал рўйхатдан ўтгансиз.",
            reply_markup=main_menu_kb(),
        )
        await callback.answer()
        return

    if await db.count_users() >= await db.get_limit():
        await callback.answer("Бўш жой қолмаган", show_alert=True)
        return

    await state.set_state(Registration.full_name)
    await callback.message.answer("👤 Исм ва фамилиянгизни киритинг:")
    await callback.answer()


@router.message(Registration.full_name)
async def full_name(message: Message, state: FSMContext):
    value = (message.text or "").strip()
    if len(value) < 5:
        await message.answer("Исм-фамилияни тўлиқ киритинг.")
        return
    await state.update_data(full_name=value)
    await state.set_state(Registration.xj_id)
    await message.answer("🆔 XJ ID рақамингизни киритинг:")


@router.message(Registration.xj_id)
async def xj_id(message: Message, state: FSMContext, db):
    value = (message.text or "").strip().upper()
    if len(value) < 2:
        await message.answer("XJ ID нотўғри.")
        return
    if await db.user_by_xj(value):
        await message.answer("❌ Бу XJ ID аввал рўйхатдан ўтган.")
        return

    await state.update_data(xj_id=value)
    await state.set_state(Registration.qualification)
    await message.answer("⭐ Квалификациянгизни танланг:", reply_markup=qualification_kb())


@router.callback_query(Registration.qualification, F.data.startswith("qual:"))
async def qualification(callback: CallbackQuery, state: FSMContext):
    await state.update_data(qualification=callback.data.split(":", 1)[1])
    await state.set_state(Registration.phone)
    await callback.message.answer(
        "📱 Телефон рақамингизни тугма орқали юборинг:",
        reply_markup=phone_kb(),
    )
    await callback.answer()


@router.message(Registration.phone, F.contact)
async def phone(message: Message, state: FSMContext, db):
    if message.contact.user_id and message.contact.user_id != message.from_user.id:
        await message.answer("Ўз телефон рақамингизни юборинг.")
        return

    value = "+" + re.sub(r"\D", "", message.contact.phone_number)
    if await db.user_by_phone(value):
        await message.answer("❌ Бу телефон рақами аввал рўйхатдан ўтган.")
        return

    await state.update_data(phone=value)
    await state.set_state(Registration.region)
    await message.answer("📍 Вилоятингизни танланг:", reply_markup=ReplyKeyboardRemove())
    await message.answer("Вилоятлар:", reply_markup=regions_kb())


@router.message(Registration.phone)
async def phone_only_contact(message: Message):
    await message.answer("Пастдаги тугма орқали телефон рақамингизни юборинг.", reply_markup=phone_kb())


@router.callback_query(Registration.region, F.data.startswith("region:"))
async def region(callback: CallbackQuery, state: FSMContext):
    await state.update_data(region=callback.data.split(":", 1)[1])
    await state.set_state(Registration.gender)
    await callback.message.answer("🚻 Жинсингизни танланг:", reply_markup=gender_kb())
    await callback.answer()


@router.callback_query(Registration.gender, F.data.startswith("gender:"))
async def gender(callback: CallbackQuery, state: FSMContext):
    await state.update_data(gender=callback.data.split(":", 1)[1])
    data = await state.get_data()
    await state.set_state(Registration.confirm)
    text = (
        "<b>МАЪЛУМОТЛАРНИ ТЕКШИРИНГ</b>\n\n"
        f"👤 {data['full_name']}\n"
        f"🆔 {data['xj_id']}\n"
        f"⭐ {data['qualification']}\n"
        f"📱 {data['phone']}\n"
        f"📍 {data['region']}\n"
        f"🚻 {data['gender']}"
    )
    await callback.message.answer(text, reply_markup=confirm_kb())
    await callback.answer()


@router.callback_query(Registration.confirm, F.data == "reg_confirm")
async def confirm_registration(callback: CallbackQuery, state: FSMContext, db, config):
    if await db.count_users() >= await db.get_limit():
        await callback.answer("Бўш жой қолмаган", show_alert=True)
        return

    data = await state.get_data()
    try:
        await db.add_user(callback.from_user.id, callback.from_user.username, data)
    except Exception:
        await callback.answer("Маълумот такрорланган ёки хатолик юз берди", show_alert=True)
        return

    await state.clear()
    await callback.message.answer(
        "🎉 <b>ТАБРИКЛАЙМИЗ!</b>\n\n"
        "Сиз XJ Лидерлар Конгрессига муваффақиятли рўйхатдан ўтдингиз.",
        reply_markup=main_menu_kb(),
    )

    admin_text = (
        "🆕 Янги иштирокчи\n"
        f"👤 {data['full_name']}\n"
        f"🆔 {data['xj_id']}\n"
        f"⭐ {data['qualification']}\n"
        f"📱 {data['phone']}"
    )
    for admin_id in config.admin_ids:
        try:
            await callback.bot.send_message(admin_id, admin_text)
        except Exception:
            pass
    await callback.answer()


@router.callback_query(Registration.confirm, F.data == "reg_cancel")
async def cancel_registration(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Рўйхатдан ўтиш бекор қилинди.", reply_markup=start_kb())
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery, db):
    if not await db.user_by_tg(callback.from_user.id):
        await callback.answer("Аввал рўйхатдан ўтинг", show_alert=True)
        return
    await callback.message.answer("🏆 <b>XJ ЛИДЕРЛАР КОНГРЕССИ</b>", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("day:"))
async def show_day(callback: CallbackQuery):
    day_number = int(callback.data.split(":", 1)[1])
    await callback.message.answer(PROGRAMS[day_number], reply_markup=back_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "buy_ticket")
async def buy_ticket(callback: CallbackQuery, db):
    if not await db.user_by_tg(callback.from_user.id):
        await callback.answer("Аввал рўйхатдан ўтинг", show_alert=True)
        return

    try:
        rate = await usd_rate()
    except Exception:
        await callback.answer("Курсни олишда хатолик. Кейинроқ уриниб кўринг.", show_alert=True)
        return

    econom_uzs = round(rate * 150)
    business_uzs = round(rate * 250)
    text = (
        "🎟 <b>ПАКЕТНИ ТАНЛАНГ</b>\n\n"
        f"Марказий банк курси: 1$ = {rate:,.2f} сўм"
    ).replace(",", " ")
    await callback.message.answer(text, reply_markup=packages_kb(econom_uzs, business_uzs))
    await callback.answer()


@router.callback_query(F.data.startswith("package:"))
async def package_details(callback: CallbackQuery):
    package = callback.data.split(":", 1)[1]
    try:
        rate = await usd_rate()
    except Exception:
        await callback.answer("Курсни олишда хатолик", show_alert=True)
        return

    usd = 150 if package == "econom" else 250
    uzs = round(rate * usd)
    extra = ""
    if package == "business":
        extra = (
            "\n\n💎 <b>BUSINESS АФЗАЛЛИКЛАРИ</b>\n"
            "• Лидерлар билан транспорт\n"
            "• Лидерлар билан овқатланиш\n"
            "• Юқори комфортли хона"
        )

    text = (
        f"<b>{package.upper()} — {usd}$</b>\n"
        f"Сўмда: <b>{uzs:,} сўм</b>\n\n"
        f"{PACKAGE_COMMON}{extra}"
    ).replace(",", " ")
    await callback.message.answer(text, reply_markup=payment_method_kb(package))
    await callback.answer()


@router.callback_query(F.data == "offer")
async def show_offer(callback: CallbackQuery):
    await callback.message.answer(OFFER)
    await callback.answer()

