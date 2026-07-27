from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def start_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✨ РЎЙХАТДАН ЎТИШ", callback_data="register")
    ]])


def qualification_kb():
    values = ["ОДДИЙ ҲАМКОР", "XJ МАСТЕР", "XJ МЕНЕЖЕРИ", "XJ БРОНЗА МЕНЕЖЕРИ"]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=value, callback_data=f"qual:{value}")]
        for value in values
    ])


def phone_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 ТЕЛЕФОН РАҚАМНИ ЮБОРИШ", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def regions_kb():
    regions = [
        "Тошкент шаҳри", "Тошкент вилояти", "Андижон", "Бухоро", "Жиззах",
        "Қашқадарё", "Навоий", "Наманган", "Самарқанд", "Сирдарё",
        "Сурхондарё", "Фарғона", "Хоразм", "Қорақалпоғистон",
    ]
    builder = InlineKeyboardBuilder()
    for region in regions:
        builder.button(text=region, callback_data=f"region:{region}")
    builder.adjust(2)
    return builder.as_markup()


def gender_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[ 
        InlineKeyboardButton(text="👨 ЭРКАК", callback_data="gender:Эркак"),
        InlineKeyboardButton(text="👩 АЁЛ", callback_data="gender:Аёл"),
    ]])


def confirm_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ ТАСДИҚЛАЙМАН", callback_data="reg_confirm")],
        [InlineKeyboardButton(text="❌ БЕКОР ҚИЛИШ", callback_data="reg_cancel")],
    ])


def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 1-КУН", callback_data="day:1"), InlineKeyboardButton(text="📅 2-КУН", callback_data="day:2")],
        [InlineKeyboardButton(text="📅 3-КУН", callback_data="day:3"), InlineKeyboardButton(text="📅 4-КУН", callback_data="day:4")],
        [InlineKeyboardButton(text="🎟 БИЛЕТ СОТИБ ОЛИШ", callback_data="buy_ticket")],
    ])


def back_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎟 БИЛЕТ СОТИБ ОЛИШ", callback_data="buy_ticket")],
        [InlineKeyboardButton(text="⬅️ ОРҚАГА", callback_data="main_menu")],
    ])


def packages_kb(econom_uzs: int, business_uzs: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🎫 ECONOM • 150$ • {econom_uzs:,} сўм".replace(",", " "), callback_data="package:econom")],
        [InlineKeyboardButton(text=f"💎 BUSINESS • 250$ • {business_uzs:,} сўм".replace(",", " "), callback_data="package:business")],
        [InlineKeyboardButton(text="⬅️ ОРҚАГА", callback_data="main_menu")],
    ])


def payment_method_kb(package: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 ҲОЗИР КАРТА ОРҚАЛИ", callback_data=f"pay_card:{package}")],
        [InlineKeyboardButton(text="👤 ЮҚОРИ ЛИДЕР ОРҚАЛИ", callback_data=f"pay_leader:{package}")],
        [InlineKeyboardButton(text="🔄 ПАКЕТНИ АЛМАШТИРИШ", callback_data="buy_ticket")],
    ])


def card_kb(package: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📜 ОММАВИЙ ОФЕРТА", callback_data="offer")],
        [InlineKeyboardButton(text="📸 ТЎЛОВ ЧЕКИНИ ЮБОРИШ", callback_data=f"send_receipt:{package}")],
        [InlineKeyboardButton(text="⬅️ ОРҚАГА", callback_data=f"package:{package}")],
    ])


def leader_confirm_kb(package: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ ШАРТЛАРГА РОЗИМАН", callback_data=f"leader_confirm:{package}")],
        [InlineKeyboardButton(text="⬅️ ОРҚАГА", callback_data=f"package:{package}")],
    ])


def admin_kb(registration_open: bool = True):
    toggle_text = "🔒 РЎЙХАТДАН ЎТИШНИ ТЎХТАТИШ" if registration_open else "🔓 РЎЙХАТДАН ЎТИШНИ ОЧИШ"
    toggle_action = "admin:close_registration" if registration_open else "admin:open_registration"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 СТАТИСТИКА", callback_data="admin:stats"), InlineKeyboardButton(text="👥 ИШТИРОКЧИЛАР", callback_data="admin:users")],
        [InlineKeyboardButton(text="💳 ТЎЛОВ ВА БРОНЛАР", callback_data="admin:payments")],
        [InlineKeyboardButton(text="📢 ҲАММАГА ХАБАР", callback_data="admin:broadcast"), InlineKeyboardButton(text="👤 АЛОҲИДА ХАБАР", callback_data="admin:personal")],
        [InlineKeyboardButton(text="🎟 ЛИМИТНИ ЎЗГАРТИРИШ", callback_data="admin:limit")],
        [InlineKeyboardButton(text=toggle_text, callback_data=toggle_action)],
        [InlineKeyboardButton(text="📥 EXCEL ЮКЛАШ", callback_data="admin:excel")],
    ])


def receipt_admin_kb(payment_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[[ 
        InlineKeyboardButton(text="✅ ТАСДИҚЛАШ", callback_data=f"receipt_ok:{payment_id}"),
        InlineKeyboardButton(text="❌ БЕКОР ҚИЛИШ", callback_data=f"receipt_no:{payment_id}"),
    ]])


def personal_user_kb(user_id: int, booking_id: int | None = None):
    rows = [[InlineKeyboardButton(text="✉️ ХАБАР ЁЗИШ", callback_data=f"personal_write:{user_id}")]]
    if booking_id:
        rows.append([
            InlineKeyboardButton(text="✅ ТЎЛОВНИ ТАСДИҚЛАШ", callback_data=f"receipt_ok:{booking_id}"),
            InlineKeyboardButton(text="❌ БРОННИ БЕКОР ҚИЛИШ", callback_data=f"receipt_no:{booking_id}"),
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

