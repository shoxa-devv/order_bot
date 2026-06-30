from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from database import Product, CartItem, Order, User
from typing import List, Tuple

# ----------------- Reply Keyboards -----------------

def get_main_menu() -> ReplyKeyboardMarkup:
    """Persistent main keyboard in Uzbek."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🛍 Katalog"),
        KeyboardButton(text="🛒 Savatcha")
    )
    builder.row(
        KeyboardButton(text="📦 Buyurtmalarim")
    )
    return builder.as_markup(resize_keyboard=True, persistent=True)

def get_phone_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard requesting phone number via Telegram contact sharing."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📞 Telefon raqamini jo'natish", request_contact=True)
    )
    builder.row(
        KeyboardButton(text="❌ Bekor qilish")
    )
    return builder.as_markup(resize_keyboard=True)

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard to cancel active FSM states."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="❌ Bekor qilish")
    )
    return builder.as_markup(resize_keyboard=True)

def get_admin_menu() -> ReplyKeyboardMarkup:
    """Admin panel main control keyboard."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📦 Yangi buyurtmalar"),
        KeyboardButton(text="➕ Yangi mahsulot qo'shish")
    )
    builder.row(
        KeyboardButton(text="⬅️ Asosiy menyuga qaytish")
    )
    return builder.as_markup(resize_keyboard=True)

# ----------------- Inline Keyboards -----------------

def get_categories_keyboard(categories: List[str]) -> InlineKeyboardMarkup:
    """List of product categories."""
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=cat, callback_data=f"cat:{cat}")
    builder.adjust(2)  # 2 columns
    return builder.as_markup()

def get_products_keyboard(products: List[Product], category_name: str) -> InlineKeyboardMarkup:
    """List of products in a selected category."""
    builder = InlineKeyboardBuilder()
    for prod in products:
        builder.button(text=f"{prod.name} - {int(prod.price):,} UZS", callback_data=f"prod:{prod.id}")
    builder.button(text="⬅️ Orqaga", callback_data="cat_back")
    builder.adjust(1)  # 1 column for product list
    return builder.as_markup()

def get_product_detail_keyboard(product_id: int, category_name: str) -> InlineKeyboardMarkup:
    """Actions on product page: Add to Cart and Go Back."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Savatga qo'shish", callback_data=f"add_to_cart:{product_id}")
    builder.button(text="⬅️ Orqaga", callback_data=f"cat:{category_name}")
    builder.adjust(1)
    return builder.as_markup()

def get_cart_keyboard(cart_items: List[Tuple[CartItem, Product]]) -> InlineKeyboardMarkup:
    """
    Generate inline keyboard for cart.
    Contains decrement/increment buttons for each product, checkout button, and clear button.
    """
    builder = InlineKeyboardBuilder()
    
    for item, prod in cart_items:
        # Limit item name to fit Telegram button width limits
        name_short = prod.name[:12] + ".." if len(prod.name) > 12 else prod.name
        
        # Row layout: ➖ | Product Name: Qty | ➕ | ❌
        builder.row(
            InlineKeyboardButton(text="➖", callback_data=f"cart_dec:{prod.id}"),
            InlineKeyboardButton(text=f"{name_short} ({item.quantity} ta)", callback_data=f"prod:{prod.id}"),
            InlineKeyboardButton(text="➕", callback_data=f"cart_inc:{prod.id}"),
            InlineKeyboardButton(text="❌", callback_data=f"cart_del:{prod.id}")
        )
        
    # Actions row
    builder.row(
        InlineKeyboardButton(text="🚖 Buyurtma berish (Checkout)", callback_data="cart_checkout"),
        InlineKeyboardButton(text="🗑 Savatni bo'shatish", callback_data="cart_clear")
    )
    
    return builder.as_markup()

def get_checkout_confirm_keyboard() -> InlineKeyboardMarkup:
    """Final checkout confirmation keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Buyurtmani tasdiqlash", callback_data="confirm_order"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_checkout")
    )
    return builder.as_markup()

def get_admin_orders_keyboard(orders: List[Tuple[Order, User]]) -> InlineKeyboardMarkup:
    """List of orders for admin viewing."""
    builder = InlineKeyboardBuilder()
    for order, user in orders:
        created_str = order.created_at.strftime("%H:%M %d-%m")
        # Example: #ORD-12 | Shoxjaxon (14:30 30-06)
        text = f"#ORD-{order.id} | {user.name or 'User'} ({created_str})"
        builder.button(text=text, callback_data=f"admin_order:{order.id}")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_order_detail_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Action buttons for a specific order inside the Admin Panel."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Yakunlash (Completed)", callback_data=f"admin_complete:{order_id}"),
        InlineKeyboardButton(text="❌ Bekor qilish (Cancelled)", callback_data=f"admin_cancel:{order_id}")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_orders_back")
    )
    return builder.as_markup()
