from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database import get_cart_items, update_cart_item_quantity, remove_from_cart, clear_cart
from keyboards import get_cart_keyboard, get_cancel_keyboard
from states import CheckoutStates

router = Router()

async def render_cart_message(telegram_id: int) -> tuple[str, bool, any]:
    """Helper function to load cart items and format the text and keyboard."""
    cart_items = await get_cart_items(telegram_id)
    if not cart_items:
        return "Sizning savatchangiz bo'sh. 🛒", False, None
    
    text = "🛒 **Sizning savatchangiz:**\n\n"
    total_price = 0.0
    
    for idx, (item, prod) in enumerate(cart_items, start=1):
        subtotal = prod.price * item.quantity
        total_price += subtotal
        text += f"{idx}. **{prod.name}**\n   {item.quantity} ta x {int(prod.price):,} UZS = {int(subtotal):,} UZS\n"
        
    text += f"\n**Jami summa: {int(total_price):,} UZS**"
    
    # Generate inline keyboard
    reply_markup = get_cart_keyboard(cart_items)
    return text, True, reply_markup

@router.message(lambda message: message.text == "🛒 Savatcha")
async def show_cart(message: Message):
    """Triggered from persistent reply keyboard."""
    text, has_items, reply_markup = await render_cart_message(message.from_user.id)
    if has_items:
        await message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await message.answer(text)

@router.callback_query(F.data.startswith("cart_inc:"))
async def process_cart_inc(call: CallbackQuery):
    """Increments item quantity by 1."""
    product_id = int(call.data.split(":")[1])
    await update_cart_item_quantity(call.from_user.id, product_id, 1)
    
    text, has_items, reply_markup = await render_cart_message(call.from_user.id)
    if has_items:
        await call.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await call.message.edit_text(text)
    await call.answer()

@router.callback_query(F.data.startswith("cart_dec:"))
async def process_cart_dec(call: CallbackQuery):
    """Decrements item quantity by 1. Deletes if quantity reaches 0."""
    product_id = int(call.data.split(":")[1])
    await update_cart_item_quantity(call.from_user.id, product_id, -1)
    
    text, has_items, reply_markup = await render_cart_message(call.from_user.id)
    if has_items:
        await call.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        # If cart became empty, edit to show empty cart text
        await call.message.edit_text(text)
    await call.answer()

@router.callback_query(F.data.startswith("cart_del:"))
async def process_cart_delete(call: CallbackQuery):
    """Removes product from cart completely."""
    product_id = int(call.data.split(":")[1])
    await remove_from_cart(call.from_user.id, product_id)
    
    text, has_items, reply_markup = await render_cart_message(call.from_user.id)
    if has_items:
        await call.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await call.message.edit_text(text)
    await call.answer("Mahsulot savatdan o'chirildi.")

@router.callback_query(F.data == "cart_clear")
async def process_cart_clear(call: CallbackQuery):
    """Clears all products in user's cart."""
    await clear_cart(call.from_user.id)
    await call.message.edit_text("Sizning savatchangiz bo'sh. 🛒")
    await call.answer("Savatchangiz bo'shatildi.")

@router.callback_query(F.data == "cart_checkout")
async def process_cart_checkout(call: CallbackQuery, state: FSMContext):
    """Initiates checkout FSM flow."""
    cart_items = await get_cart_items(call.from_user.id)
    if not cart_items:
        await call.answer("Savat bo'sh! Buyurtma berish uchun mahsulot qo'shing.", show_alert=True)
        return
        
    await state.set_state(CheckoutStates.waiting_for_address)
    await call.message.delete()
    await call.message.answer(
        "📍 Iltimos, yetkazib berish manzilini kiriting (masalan: Toshkent sh., Chilonzor tumani, 9-kvartal, 15-uy):\n\n"
        "_Buyurtmani bekor qilish uchun '❌ Bekor qilish' tugmasini bosing._",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    await call.answer()
