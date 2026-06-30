import json
from datetime import datetime
from typing import List, Optional, Tuple, Dict
from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, Integer, String, Text, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship

from config import DATABASE_URL

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Declarative base
class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)

    # Relationships
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    cart_items = relationship("CartItem", back_populates="user", cascade="all, delete-orphan")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    category = Column(String(100), nullable=False)
    photo_url = Column(String(500), nullable=True)  # Can store file_id or link
    description = Column(Text, nullable=True)

    # Relationships
    cart_items = relationship("CartItem", back_populates="product", cascade="all, delete-orphan")

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    items_json = Column(Text, nullable=False)  # JSON string of items ordered
    total_price = Column(Float, nullable=False)
    status = Column(String(50), default="yangi")  # yangi, yakunlangan, bekor_qilingan
    address = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="orders")

class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)

    # Relationships
    user = relationship("User", back_populates="cart_items")
    product = relationship("Product", back_populates="cart_items")

# ----------------- DB Initialization & Seeding -----------------

async def init_db():
    """Create tables and seed initial data if empty."""
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    # Seed data if empty
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Product).limit(1))
        product_exists = result.scalar_one_or_none()
        
        if not product_exists:
            # Seed categories and products
            initial_products = [
                Product(
                    name="Lavash",
                    price=30000.0,
                    category="Fast Food",
                    photo_url="AgACAgIAAxkBAAMKZD0AAYgO-1...", # placeholder or user will upload
                    description="Klassik lavash, mol go'shti, pomidor, bodring, chipslar va maxsus sous bilan."
                ),
                Product(
                    name="Gamburger",
                    price=25000.0,
                    category="Fast Food",
                    photo_url="",
                    description="Sershira kotlet, yangi salat barglari, pomidor, marinadlangan bodring va burger sousi."
                ),
                Product(
                    name="Coca-Cola 0.5L",
                    price=8000.0,
                    category="Ichimliklar",
                    photo_url="",
                    description="Muzdek tetiklantiruvchi alkogolsiz gazlangan ichimlik."
                ),
                Product(
                    name="Ko'k choy",
                    price=5000.0,
                    category="Ichimliklar",
                    photo_url="",
                    description="An'anaviy o'zbek ko'k choyi, shinam choynakda."
                ),
                Product(
                    name="Napoleon Pirogi",
                    price=18000.0,
                    category="Shirinliklar",
                    photo_url="",
                    description="Katlama xamir va mayin qaymoqli kremdan tayyorlangan shirinlik."
                )
            ]
            session.add_all(initial_products)
            await session.commit()
            print("Ma'lumotlar bazasi muvaffaqiyatli boshlang'ich mahsulotlar bilan to'ldirildi.")

# ----------------- User DB Operations -----------------

async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
    """Retrieve user by Telegram ID."""
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()

async def create_or_update_user(telegram_id: int, name: str = None, phone: str = None) -> User:
    """Create a user if they don't exist, or update their contact info."""
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            user = User(telegram_id=telegram_id, name=name, phone=phone)
            session.add(user)
        else:
            if name:
                user.name = name
            if phone:
                user.phone = phone
        await session.commit()
        await session.refresh(user)
        return user

# ----------------- Product Operations -----------------

async def get_categories() -> List[str]:
    """Get list of unique product categories."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Product.category).distinct())
        categories = [row[0] for row in result.all()]
        return categories

async def get_products_by_category(category: str) -> List[Product]:
    """Get all products inside a category."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Product).where(Product.category == category))
        return list(result.scalars().all())

async def get_product_by_id(product_id: int) -> Optional[Product]:
    """Get product details by ID."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()

async def add_product(name: str, price: float, category: str, photo_url: str, description: str) -> Product:
    """Add a new product to catalog (admin tool)."""
    async with AsyncSessionLocal() as session:
        product = Product(
            name=name,
            price=price,
            category=category,
            photo_url=photo_url,
            description=description
        )
        session.add(product)
        await session.commit()
        await session.refresh(product)
        return product

# ----------------- Cart Operations -----------------

async def add_to_cart(telegram_id: int, product_id: int, quantity: int = 1):
    """Add product to cart or increment quantity if already exists."""
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            # Register user dynamically if not registered
            user = User(telegram_id=telegram_id)
            session.add(user)
            await session.flush()

        # Check if item already exists in user's cart
        result = await session.execute(
            select(CartItem).where(CartItem.user_id == user.id, CartItem.product_id == product_id)
        )
        cart_item = result.scalar_one_or_none()

        if cart_item:
            cart_item.quantity += quantity
        else:
            cart_item = CartItem(user_id=user.id, product_id=product_id, quantity=quantity)
            session.add(cart_item)
        
        await session.commit()

async def get_cart_items(telegram_id: int) -> List[Tuple[CartItem, Product]]:
    """Retrieve all cart items with product details for a user."""
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            return []
        
        result = await session.execute(
            select(CartItem, Product)
            .join(Product, CartItem.product_id == Product.id)
            .where(CartItem.user_id == user.id)
        )
        return [(row[0], row[1]) for row in result.all()]

async def update_cart_item_quantity(telegram_id: int, product_id: int, delta: int) -> int:
    """Increment/decrement cart item quantity. Delete if quantity <= 0. Returns remaining quantity."""
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            return 0
        
        result = await session.execute(
            select(CartItem).where(CartItem.user_id == user.id, CartItem.product_id == product_id)
        )
        cart_item = result.scalar_one_or_none()

        if not cart_item:
            return 0

        new_quantity = cart_item.quantity + delta
        if new_quantity <= 0:
            await session.delete(cart_item)
            new_quantity = 0
        else:
            cart_item.quantity = new_quantity
        
        await session.commit()
        return new_quantity

async def remove_from_cart(telegram_id: int, product_id: int):
    """Delete item from cart completely."""
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            return
        
        await session.execute(
            delete(CartItem).where(CartItem.user_id == user.id, CartItem.product_id == product_id)
        )
        await session.commit()

async def clear_cart(telegram_id: int):
    """Clear all items in user's cart."""
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            return
        
        await session.execute(
            delete(CartItem).where(CartItem.user_id == user.id)
        )
        await session.commit()

# ----------------- Order Operations -----------------

async def create_order(telegram_id: int, address: str, phone: str) -> Optional[Order]:
    """Move cart items to a new Order, clear cart, update user data, and return Order."""
    async with AsyncSessionLocal() as session:
        # 1. Fetch user
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            return None
        
        # Update name/phone details if they are provided
        if phone:
            user.phone = phone
        
        # 2. Get cart items
        result = await session.execute(
            select(CartItem, Product)
            .join(Product, CartItem.product_id == Product.id)
            .where(CartItem.user_id == user.id)
        )
        rows = result.all()
        if not rows:
            return None # empty cart

        # 3. Create JSON serialized cart list
        cart_details = []
        total_price = 0.0
        for cart_item, product in rows:
            subtotal = product.price * cart_item.quantity
            total_price += subtotal
            cart_details.append({
                "product_id": product.id,
                "name": product.name,
                "price": product.price,
                "quantity": cart_item.quantity,
                "subtotal": subtotal
            })
        
        items_json = json.dumps(cart_details, ensure_ascii=False)
        
        # 4. Insert Order
        order = Order(
            user_id=user.id,
            items_json=items_json,
            total_price=total_price,
            status="yangi",
            address=address
        )
        session.add(order)
        
        # 5. Clear cart
        await session.execute(
            delete(CartItem).where(CartItem.user_id == user.id)
        )
        
        await session.commit()
        await session.refresh(order)
        return order

async def get_user_orders(telegram_id: int) -> List[Order]:
    """Retrieve all orders placed by a specific user."""
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            return []
        
        result = await session.execute(
            select(Order)
            .where(Order.user_id == user.id)
            .order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())

async def get_all_orders(status: Optional[str] = None) -> List[Tuple[Order, User]]:
    """Admin feature: Retrieve all orders and their placing user details, optionally filtered by status."""
    async with AsyncSessionLocal() as session:
        query = select(Order, User).join(User, Order.user_id == User.id)
        if status:
            query = query.where(Order.status == status)
        query = query.order_by(Order.created_at.desc())
        
        result = await session.execute(query)
        return [(row[0], row[1]) for row in result.all()]

async def get_order_by_id(order_id: int) -> Optional[Tuple[Order, User]]:
    """Retrieve a single order and user by ID."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Order, User)
            .join(User, Order.user_id == User.id)
            .where(Order.id == order_id)
        )
        row = result.first()
        return (row[0], row[1]) if row else None

async def update_order_status(order_id: int, status: str) -> bool:
    """Admin feature: Update order status to Completed/Cancelled."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            return False
        
        order.status = status
        await session.commit()
        return True
