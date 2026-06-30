from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
import json

from states import CheckoutStates
from keyboards import get_phone_keyboard, get_checkout_confirm_keyboard, get_main_menu
from database import create_order, get_cart_items
from config import ADMIN_ID

router = Router()

@router.message(CheckoutStates.waiting_for_address)
async def process_address(message: Message, state: FSMContext):
    """Saves address and prompts user for their phone number."""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Buyurtma bekor qilindi.", reply_markup=get_main_menu())
        return
        
    await state.update_data(address=message.text)
    await state.set_state(CheckoutStates.waiting_for_phone)
    await message.answer(
        "📞 Iltimos, telefon raqamingizni yuboring.\n"
        "Quyidagi tugmani bosish orqali kontakt raqamingizni osongina ulashishingiz mumkin yoki raqamingizni yozib yuboring (Masalan: +998901234567):",
        reply_markup=get_phone_keyboard()
    )

@router.message(CheckoutStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    """Processes contact share or manual phone text input, then prints order summary."""
    phone = None
    if message.contact:
        phone = message.contact.phone_number
    elif message.text:
        if message.text == "❌ Bekor qilish":
            await state.clear()
            await message.answer("Buyurtma bekor qilindi.", reply_markup=get_main_menu())
            return
        
        # Simple phone validation check
        clean_text = "".join(filter(str.isdigit, message.text))
        if len(clean_text) >= 9:
            phone = message.text
        else:
            await message.answer("Iltimos, telefon raqamini to'g'ri formatda kiriting.")
            return

    if not phone:
        await message.answer("Telefon raqamingizni jo'nating yoki kiriting.")
        return

    await state.update_data(phone=phone)
    await state.set_state(CheckoutStates.waiting_for_confirmation)
    
    # Retrieve address from state
    data = await state.get_data()
    address = data.get("address")
    
    # Load cart items to format summary
    cart_items = await get_cart_items(message.from_user.id)
    if not cart_items:
        await state.clear()
        await message.answer("Savat bo'shab qolganligi sababli buyurtma to'xtatildi.", reply_markup=get_main_menu())
        return
        
    summary_text = (
        "📝 **Buyurtmangiz tafsilotlari:**\n\n"
        f"👤 Buyurtmachi: {message.from_user.full_name}\n"
        f"📞 Telefon: {phone}\n"
        f"📍 Yetkazib berish manzili: {address}\n\n"
        "**Mahsulotlar:**\n"
    )
    
    total_price = 0.0
    for idx, (item, prod) in enumerate(cart_items, start=1):
        subtotal = prod.price * item.quantity
        total_price += subtotal
        summary_text += f" • {prod.name} x{item.quantity} ({int(subtotal):,} UZS)\n"
        
    summary_text += f"\n💰 **Jami summa: {int(total_price):,} UZS**\n\n"
    summary_text += "Buyurtmani tasdiqlaysizmi?"
    
    # Hide reply keyboard when showing confirmation
    await message.answer("Tafsilotlar tayyorlandi.", reply_markup=ReplyKeyboardRemove())
    await message.answer(
        text=summary_text,
        reply_markup=get_checkout_confirm_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "cancel_checkout")
async def process_cancel_checkout(call: CallbackQuery, state: FSMContext):
    """Cancels checkout flow via inline button."""
    await state.clear()
    await call.message.delete()
    await call.message.answer("Buyurtma bekor qilindi.", reply_markup=get_main_menu())
    await call.answer()

@router.callback_query(F.data == "confirm_order")
async def process_confirm_order(call: CallbackQuery, state: FSMContext, bot: Bot):
    """Finalizes order creation in database and clears cart."""
    data = await state.get_data()
    address = data.get("address")
    phone = data.get("phone")
    
    if not address or not phone:
        await call.answer("Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.", show_alert=True)
        await state.clear()
        return
        
    order = await create_order(
        telegram_id=call.from_user.id,
        address=address,
        phone=phone
    )
    
    if not order:
        await call.answer("Savatchangiz bo'sh. Buyurtma berib bo'lmadi.", show_alert=True)
        await state.clear()
        return
        
    await state.clear()
    await call.message.delete()
    await call.message.answer(
        f"✅ **Buyurtmangiz muvaffaqiyatli qabul qilindi!**\n\n"
        f"Buyurtma ID: `#ORD-{order.id}`\n"
        f"Jami summa: {int(order.total_price):,} UZS\n\n"
        f"Yaqin orada operatorlarimiz siz bilan bog'lanishadi. Rahmat! 😊",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )
    await call.answer()
    
    # Notify Admin if ADMIN_ID is set
    if ADMIN_ID:
        try:
            admin_text = (
                f"🆕 **YANGI BUYURTMA KELDI!**\n\n"
                f"Buyurtma ID: `#ORD-{order.id}`\n"
                f"Mijoz: {call.from_user.full_name} (@{call.from_user.username or 'yoq'})\n"
                f"Tel: {phone}\n"
                f"Manzil: {address}\n"
                f"Summa: {int(order.total_price):,} UZS\n\n"
                f"Batafsil ko'rish uchun /admin buyrug'ini bosing."
            )
            await bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode="Markdown")
        except Exception as e:
            print(f"Adminga xabar yuborishda xatolik: {e}")
