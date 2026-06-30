from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, Filter
from aiogram.utils.keyboard import ReplyKeyboardBuilder
import json

from config import ADMIN_ID
from states import AdminStates
from database import (
    get_all_orders, get_order_by_id, update_order_status, 
    add_product, get_categories
)
from keyboards import (
    get_admin_menu, get_admin_orders_keyboard, 
    get_admin_order_detail_keyboard, get_cancel_keyboard, get_main_menu
)

router = Router()

# Custom Filter to check if user is the Admin
class IsAdmin(Filter):
    async def __call__(self, message: Message) -> bool:
        return ADMIN_ID is not None and message.from_user.id == ADMIN_ID

class IsAdminCall(Filter):
    async def __call__(self, call: CallbackQuery) -> bool:
        return ADMIN_ID is not None and call.from_user.id == ADMIN_ID

@router.message(IsAdmin(), Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Admin command handler. Opens admin control panel."""
    await state.clear()
    await message.answer(
        "👋 Admin paneliga xush kelibsiz! Boshqarish uchun quyidagi tugmalardan foydalaning:",
        reply_markup=get_admin_menu()
    )

# Fallback for non-admin command
@router.message(Command("admin"))
async def cmd_non_admin(message: Message):
    await message.answer("Ushbu buyruq faqat bot adminstratori uchun ochiq. ❌")

@router.message(IsAdmin(), F.text == "⬅️ Asosiy menyuga qaytish")
async def process_admin_back_to_user(message: Message, state: FSMContext):
    """Exits admin view and shows regular user menu."""
    await state.clear()
    await message.answer("Siz foydalanuvchi rejimidan foydalanyapsiz.", reply_markup=get_main_menu())

@router.message(IsAdmin(), F.text == "📦 Yangi buyurtmalar")
async def process_admin_show_orders(message: Message):
    """Loads list of new orders from the database."""
    orders = await get_all_orders(status="yangi")
    if not orders:
        await message.answer("Hozircha yangi buyurtmalar mavjud emas. 👍")
        return
        
    await message.answer(
        "🆕 Yangi buyurtmalar ro'yxati:",
        reply_markup=get_admin_orders_keyboard(orders)
    )

@router.callback_query(IsAdminCall(), F.data == "admin_orders_back")
async def process_admin_orders_back(call: CallbackQuery):
    """Goes back to list of orders in the inline view."""
    orders = await get_all_orders(status="yangi")
    if not orders:
        await call.message.edit_text("Hozircha yangi buyurtmalar mavjud emas. 👍", reply_markup=None)
        await call.answer()
        return
        
    await call.message.edit_text(
        "🆕 Yangi buyurtmalar ro'yxati:",
        reply_markup=get_admin_orders_keyboard(orders)
    )
    await call.answer()

@router.callback_query(IsAdminCall(), F.data.startswith("admin_order:"))
async def process_admin_order_detail(call: CallbackQuery):
    """Shows full details of a specific order to the admin."""
    order_id = int(call.data.split(":")[1])
    order_details = await get_order_by_id(order_id)
    
    if not order_details:
        await call.answer("Buyurtma topilmadi.", show_alert=True)
        return
        
    order, user = order_details
    created_str = order.created_at.strftime("%Y-%m-%d %H:%M")
    
    user_name = user.name or "Noma'lum"
    text = (
        f"📦 **Buyurtma #{order.id}**\n"
        f"📅 Sana: {created_str}\n"
        f"👤 Mijoz: {user_name} (ID: {user.telegram_id})\n"
        f"📞 Tel: {user.phone or 'Mavjud emas'}\n"
        f"📍 Manzil: {order.address}\n"
        f"⚙️ Status: {order.status.upper()}\n\n"
        f"**Mahsulotlar:**\n"
    )
    
    try:
        items = json.loads(order.items_json)
        for item in items:
            text += f" • {item['name']} x{item['quantity']} ({int(item['price']):,} UZS)\n"
    except Exception:
        text += " (Xatolik: mahsulotlar ruyxati yuklanmadi)\n"
        
    text += f"\n💰 **Jami summa: {int(order.total_price):,} UZS**"
    
    await call.message.edit_text(
        text=text,
        reply_markup=get_admin_order_detail_keyboard(order.id),
        parse_mode="Markdown"
    )
    await call.answer()

@router.callback_query(IsAdminCall(), F.data.startswith("admin_complete:"))
async def process_admin_complete(call: CallbackQuery, bot: Bot):
    """Marks order status as Completed and notifies customer."""
    order_id = int(call.data.split(":")[1])
    order_details = await get_order_by_id(order_id)
    
    if not order_details:
        await call.answer("Buyurtma topilmadi.", show_alert=True)
        return
        
    order, user = order_details
    success = await update_order_status(order_id, "yakunlangan")
    
    if success:
        await call.answer("Buyurtma yakunlandi! ✅", show_alert=True)
        # Re-render with new status (no actions since completed)
        await call.message.edit_text(
            f"✅ **Buyurtma #{order.id} yakunlangan statusiga o'tkazildi.**\n\nJami: {int(order.total_price):,} UZS",
            reply_markup=None
        )
        
        # Notify User
        try:
            user_msg = (
                f"🔔 **Sizning buyurtmangiz tayyor!**\n\n"
                f"Sizning `#ORD-{order.id}`-raqamli buyurtmangiz muvaffaqiyatli yakunlandi va yetkazib berildi. "
                f"Xaridingiz uchun rahmat! 😊"
            )
            await bot.send_message(chat_id=user.telegram_id, text=user_msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Foydalanuvchiga bildirishnoma yuborishda xatolik: {e}")
    else:
        await call.answer("Xatolik: Status yangilanmadi.", show_alert=True)

@router.callback_query(IsAdminCall(), F.data.startswith("admin_cancel:"))
async def process_admin_cancel(call: CallbackQuery, bot: Bot):
    """Marks order status as Cancelled and notifies customer."""
    order_id = int(call.data.split(":")[1])
    order_details = await get_order_by_id(order_id)
    
    if not order_details:
        await call.answer("Buyurtma topilmadi.", show_alert=True)
        return
        
    order, user = order_details
    success = await update_order_status(order_id, "bekor_qilingan")
    
    if success:
        await call.answer("Buyurtma bekor qilindi. ❌", show_alert=True)
        # Re-render
        await call.message.edit_text(
            f"❌ **Buyurtma #{order.id} bekor qilindi.**",
            reply_markup=None
        )
        
        # Notify User
        try:
            user_msg = (
                f"🔔 **Buyurtma bekor qilindi.**\n\n"
                f"Afsuski, sizning `#ORD-{order.id}`-raqamli buyurtmangiz bekor qilindi.\n"
                f"Batafsil ma'lumot olish uchun operatorimiz bilan bog'lanishingiz mumkin."
            )
            await bot.send_message(chat_id=user.telegram_id, text=user_msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Foydalanuvchiga bildirishnoma yuborishda xatolik: {e}")
    else:
        await call.answer("Xatolik: Status yangilanmadi.", show_alert=True)

# ----------------- Add Product FSM Flow -----------------

@router.message(IsAdmin(), F.text == "➕ Yangi mahsulot qo'shish")
async def admin_add_product_start(message: Message, state: FSMContext):
    """Starts the add product FSM flow. Requests category."""
    await state.set_state(AdminStates.waiting_for_category)
    
    # Get existing categories to help admin input easily
    categories = await get_categories()
    
    # Setup suggestion reply keyboard
    builder = ReplyKeyboardBuilder()
    for cat in categories:
        builder.add(KeyboardButton(text=cat))
    builder.row(KeyboardButton(text="❌ Bekor qilish"))
    
    await message.answer(
        "🗂 Mahsulot kategoriyasini kiriting (yoki quyidagilardan tanlang):",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

@router.message(AdminStates.waiting_for_category)
async def admin_process_category(message: Message, state: FSMContext):
    """Processes category and requests product name."""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=get_admin_menu())
        return
        
    await state.update_data(category=message.text)
    await state.set_state(AdminStates.waiting_for_name)
    await message.answer(
        "✏️ Mahsulot nomini kiriting:",
        reply_markup=get_cancel_keyboard()
    )

@router.message(AdminStates.waiting_for_name)
async def admin_process_name(message: Message, state: FSMContext):
    """Processes name and requests product description."""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=get_admin_menu())
        return
        
    await state.update_data(name=message.text)
    await state.set_state(AdminStates.waiting_for_description)
    await message.answer(
        "📝 Mahsulot tavsifini kiriting (Description):",
        reply_markup=get_cancel_keyboard()
    )

@router.message(AdminStates.waiting_for_description)
async def admin_process_description(message: Message, state: FSMContext):
    """Processes description and requests price."""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=get_admin_menu())
        return
        
    await state.update_data(description=message.text)
    await state.set_state(AdminStates.waiting_for_price)
    await message.answer(
        "💰 Mahsulot narxini kiriting (faqat raqamlar bilan, masalan: 28000):",
        reply_markup=get_cancel_keyboard()
    )

@router.message(AdminStates.waiting_for_price)
async def admin_process_price(message: Message, state: FSMContext):
    """Processes price and requests product photo."""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=get_admin_menu())
        return
        
    try:
        price = float(message.text.replace(" ", ""))
        if price <= 0:
            await message.answer("Narx musbat son bo'lishi kerak. Qayta kiriting:")
            return
    except ValueError:
        await message.answer("Iltimos, faqat raqam kiriting. Masalan: 25000")
        return
        
    await state.update_data(price=price)
    await state.set_state(AdminStates.waiting_for_photo)
    
    # Option to skip photo or send it
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="⏩ Rasm yuklamaslik"),
        KeyboardButton(text="❌ Bekor qilish")
    )
    await message.answer(
        "📸 Mahsulot rasmini yuboring (Yoki quyidagi skip tugmasini bosing):",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

@router.message(AdminStates.waiting_for_photo)
async def admin_process_photo(message: Message, state: FSMContext):
    """Processes product photo, inserts into database, and ends FSM."""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=get_admin_menu())
        return
        
    photo_url = ""
    
    if message.photo:
        # Save the largest size photo file ID
        photo_url = message.photo[-1].file_id
    elif message.text == "⏩ Rasm yuklamaslik":
        photo_url = ""
    else:
        await message.answer("Iltimos, rasm yuboring yoki '⏩ Rasm yuklamaslik' tugmasini bosing.")
        return
        
    # Add product to DB
    data = await state.get_data()
    
    product = await add_product(
        name=data["name"],
        price=data["price"],
        category=data["category"],
        photo_url=photo_url,
        description=data["description"]
    )
    
    await state.clear()
    await message.answer(
        f"✅ **Yangi mahsulot katalogga qo'shildi!**\n\n"
        f"ID: {product.id}\n"
        f"Nom: {product.name}\n"
        f"Kategoriya: {product.category}\n"
        f"Narx: {int(product.price):,} UZS\n"
        f"Tavsif: {product.description}",
        reply_markup=get_admin_menu(),
        parse_mode="Markdown"
    )
