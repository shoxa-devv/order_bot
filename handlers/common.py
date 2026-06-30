from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardRemove
from database import create_or_update_user, get_user_orders
import json

from keyboards import get_main_menu, get_categories_keyboard
from database import get_categories

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Start command handler. Registers user and shows main menu."""
    await state.clear()
    
    # Register/update user in the database
    user = await create_or_update_user(
        telegram_id=message.from_user.id,
        name=message.from_user.full_name
    )
    
    welcome_text = (
        f"Assalomu alaykum, {user.name or 'aziz mijoz'}! 👋\n\n"
        f"🤖 Bizning telegram do'konimizga xush kelibsiz!\n"
        f"Bu yerda siz o'zingizga yoqqan mahsulotlarni tanlashingiz va buyurtma berishingiz mumkin.\n\n"
        f"Boshlash uchun quyidagi **🛍 Katalog** tugmasini bosing."
    )
    
    await message.answer(welcome_text, reply_markup=get_main_menu())

@router.message(lambda message: message.text == "❌ Bekor qilish")
async def cancel_handler(message: Message, state: FSMContext):
    """Cancels any current state and redirects to main menu."""
    current_state = await state.get_state()
    if current_state:
        await state.clear()
    await message.answer("Amal bekor qilindi.", reply_markup=get_main_menu())

@router.message(lambda message: message.text == "⬅️ Asosiy menyuga qaytish")
async def back_to_main_menu(message: Message, state: FSMContext):
    """Redirects to main menu."""
    await state.clear()
    await message.answer("Siz asosiy menyudasiz.", reply_markup=get_main_menu())

@router.message(lambda message: message.text == "🛍 Katalog")
async def show_catalog(message: Message):
    """Triggered from main menu persistent keyboard."""
    categories = await get_categories()
    if not categories:
        await message.answer("Hozircha katalog bo'sh.")
        return
        
    await message.answer(
        "Kategoriyalardan birini tanlang:",
        reply_markup=get_categories_keyboard(categories)
    )

@router.message(lambda message: message.text == "📦 Buyurtmalarim")
async def show_my_orders(message: Message):
    """Displays order history for the user."""
    orders = await get_user_orders(message.from_user.id)
    if not orders:
        await message.answer("Sizda hali buyurtmalar mavjud emas. 🛍")
        return
    
    text = "📝 **Sizning buyurtmalaringiz ruyxati:**\n\n"
    for idx, order in enumerate(orders, start=1):
        # Format status
        status_map = {
            "yangi": "🆕 Yangi",
            "yakunlangan": "✅ Yakunlangan",
            "bekor_qilingan": "❌ Bekor qilingan"
        }
        status_txt = status_map.get(order.status, order.status)
        created_str = order.created_at.strftime("%Y-%m-%d %H:%M")
        
        text += (
            f"**Buyurtma #{order.id}** ({created_str})\n"
            f"Status: {status_txt}\n"
            f"Jami summa: {int(order.total_price):,} UZS\n"
            f"Manzil: {order.address}\n"
        )
        
        # Details of items
        try:
            items = json.loads(order.items_json)
            text += "Mahsulotlar:\n"
            for item in items:
                text += f" • {item['name']} x{item['quantity']} ({int(item['price']):,} UZS)\n"
        except Exception:
            pass
            
        text += "—" * 15 + "\n\n"
        
    await message.answer(text)
