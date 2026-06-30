from aiogram import Router, F
from aiogram.types import CallbackQuery, InputMediaPhoto
from database import get_categories, get_products_by_category, get_product_by_id, add_to_cart
from keyboards import get_categories_keyboard, get_products_keyboard, get_product_detail_keyboard

router = Router()

@router.callback_query(F.data == "cat_back")
async def process_cat_back(call: CallbackQuery):
    """Back button handler to return to categories list."""
    categories = await get_categories()
    
    # If the previous message has media, delete it and send a new text message.
    # Otherwise, edit the text.
    if call.message.photo:
        await call.message.delete()
        await call.message.answer(
            "Kategoriyalardan birini tanlang:",
            reply_markup=get_categories_keyboard(categories)
        )
    else:
        await call.message.edit_text(
            "Kategoriyalardan birini tanlang:",
            reply_markup=get_categories_keyboard(categories)
        )
    await call.answer()

@router.callback_query(F.data.startswith("cat:"))
async def process_category_selection(call: CallbackQuery):
    """Shows products list in the selected category."""
    category_name = call.data.split(":", 1)[1]
    products = await get_products_by_category(category_name)
    
    if not products:
        await call.answer("Ushbu kategoriyada mahsulotlar topilmadi.", show_alert=True)
        return

    text = f"**{category_name}** kategoriyasidagi mahsulotlar:"
    reply_markup = get_products_keyboard(products, category_name)

    if call.message.photo:
        await call.message.delete()
        await call.message.answer(
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await call.message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    await call.answer()

@router.callback_query(F.data.startswith("prod:"))
async def process_product_selection(call: CallbackQuery):
    """Shows detailed information of the selected product."""
    product_id = int(call.data.split(":", 1)[1])
    product = await get_product_by_id(product_id)
    
    if not product:
        await call.answer("Mahsulot topilmadi.", show_alert=True)
        return
        
    caption = (
        f"🍏 **{product.name}**\n\n"
        f"💰 Narxi: {int(product.price):,} UZS\n\n"
        f"📝 Tavsif:\n{product.description or 'Tavsif mavjud emas.'}"
    )
    
    reply_markup = get_product_detail_keyboard(product.id, product.category)
    
    # Delete the previous text message to send a fresh one with or without photo
    await call.message.delete()
    
    if product.photo_url and product.photo_url.strip() and not product.photo_url.startswith("AgACAgIAAxkBAAMKZD0AAYgO-1"):
        # If it has a photo URL / file ID (excluding placeholder example)
        try:
            await call.message.answer_photo(
                photo=product.photo_url,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            # Fallback to text message if photo sending fails (e.g. invalid file id)
            await call.message.answer(
                text=caption,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
    else:
        # Text only
        await call.message.answer(
            text=caption,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    await call.answer()

@router.callback_query(F.data.startswith("add_to_cart:"))
async def process_add_to_cart(call: CallbackQuery):
    """Adds selected product to the cart database."""
    product_id = int(call.data.split(":", 1)[1])
    product = await get_product_by_id(product_id)
    
    if not product:
        await call.answer("Xatolik: mahsulot topilmadi.", show_alert=True)
        return
        
    await add_to_cart(telegram_id=call.from_user.id, product_id=product_id, quantity=1)
    await call.answer(f"{product.name} savatga qo'shildi! 🛒", show_alert=False)
