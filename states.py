from aiogram.fsm.state import State, StatesGroup

class Registration(StatesGroup):
    full_name = State()
    xj_id = State()
    qualification = State()
    phone = State()
    region = State()
    gender = State()
    confirm = State()

class Payment(StatesGroup):
    waiting_receipt = State()

class AdminState(StatesGroup):
    set_limit = State()
    broadcast = State()
    cancel_booking = State()

