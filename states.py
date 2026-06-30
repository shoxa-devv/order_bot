from aiogram.fsm.state import State, StatesGroup

class CheckoutStates(StatesGroup):
    """FSM states for checkout flow."""
    waiting_for_address = State()
    waiting_for_phone = State()
    waiting_for_confirmation = State()

class AdminStates(StatesGroup):
    """FSM states for adding products by admin."""
    waiting_for_category = State()
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_price = State()
    waiting_for_photo = State()
