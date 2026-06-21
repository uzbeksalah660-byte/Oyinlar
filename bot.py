import asyncio
import logging
import sqlite3
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web

# ================= SOZLAMALAR =================
TOKEN = "8853488093:AAG799kEMJe9MfJzk3j9udHeCXHoZtxlBYw"
ADMINS = [8057184376, 8526661272, 8148767301]
KANAL_LINK = "https://t.me/SizningKanal_ID" # To'lovlar tarixi kanali ssilkasi
ADMIN_USER = "@AzartnikMir"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# ================= BAZA (SQLITE) =================
def execute_query(query, params=(), fetchone=False, fetchall=False):
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetchone:
            return cursor.fetchone()
        if fetchall:
            return cursor.fetchall()
        conn.commit()

def init_db():
    execute_query('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, full_name TEXT, phone TEXT DEFAULT 'Kiritilmagan',
        balance INTEGER DEFAULT 0, refs_count INTEGER DEFAULT 0, withdrawn INTEGER DEFAULT 0, invited_by INTEGER DEFAULT 0)''')
    execute_query('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value INTEGER)''')
    execute_query('''CREATE TABLE IF NOT EXISTS promocodes (code TEXT PRIMARY KEY, reward INTEGER, uses INTEGER)''')
    execute_query('''CREATE TABLE IF NOT EXISTS used_promos (user_id INTEGER, code TEXT, PRIMARY KEY (user_id, code))''')
    execute_query("INSERT OR IGNORE INTO settings VALUES ('ref_price', 1000)")

def get_ref_price():
    res = execute_query("SELECT value FROM settings WHERE key='ref_price'", fetchone=True)
    return res[0] if res else 1000

# ================= KLAVIATURALAR =================
def main_menu(user_id):
    kb = [
        [KeyboardButton(text="💰 Pul ishlash"), KeyboardButton(text="💳 Hisobim")],
        [KeyboardButton(text="🏆 TOP 10"), KeyboardButton(text="💳 Pul yechish")],
        [KeyboardButton(text="🎁 Promokod"), KeyboardButton(text="🧾 To'lovlar tarixi")],
        [KeyboardButton(text="☎️ Murojaat")]
    ]
    if user_id in ADMINS:
        kb.append([KeyboardButton(text="🔐 Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🏷 Referal narxi"), KeyboardButton(text="🎁 Promokod yaratish")],
        [KeyboardButton(text="📊 Barcha statistika"), KeyboardButton(text="🗣 Xabar yuborish")],
        [KeyboardButton(text="⬅️ Bosh menyu")]
    ], resize_keyboard=True
)

withdraw_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="MELBET", callback_data="w_MELBET"), InlineKeyboardButton(text="WOWBET", callback_data="w_WOWBET")],
    [InlineKeyboardButton(text="LILBET", callback_data="w_LILBET"), InlineKeyboardButton(text="FASTPARI", callback_data="w_FASTPARI")],
    [InlineKeyboardButton(text="DBBET", callback_data="w_DBBET"), InlineKeyboardButton(text="WINWINBET", callback_data="w_WINWINBET")]
])

# ================= HOLATLAR (FSM) =================
class BotStates(StatesGroup):
    new_ref_price = State()
    promo_name, promo_reward, promo_uses = State(), State(), State()
    broadcast_msg = State()
    enter_promo = State()
    withdraw_prop, withdraw_amount = State(), State()

# ================= ASOSIY MENU LOBBISI =================
@dp.message(Command("cancel"))
async def cancel_action(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Bosh menyu:", reply_markup=main_menu(message.from_user.id))

@dp.message(CommandStart())
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    
    parts = message.text.split()
    invited_by = 0
    if len(parts) > 1 and parts[1].startswith("ref_"):
        try:
            inv = int(parts[1].replace("ref_", ""))
            if inv != user_id: invited_by = inv
        except ValueError: pass

    user = execute_query("SELECT user_id FROM users WHERE user_id=?", (user_id,), fetchone=True)
    if not user:
        execute_query("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", (user_id, full_name, "Kiritilmagan", 0, 0, 0, invited_by))
        if invited_by:
            r_price = get_ref_price()
            execute_query("UPDATE users SET balance=balance+?, refs_count=refs_count+1 WHERE user_id=?", (r_price, invited_by))
            try:
                await bot.send_message(invited_by, f"🎉 Havolangiz orqali <b>{full_name}</b> ro'yxatdan o'tdi!\n💰 Hisobingizga <b>{r_price} so'm</b> qo'shildi.")
            except Exception: pass

    await message.answer(f"👋 Xush kelibsiz, <b>{full_name}</b>!\n\nQuyidagi menyudan tanlang:", reply_markup=main_menu(user_id))

@dp.message(F.text == "💰 Pul ishlash")
async def get_ref_link(message: types.Message):
    bot_user = await bot.me()
    ref_link = f"https://t.me/{bot_user.username}?start=ref_{message.from_user.id}"
    await message.answer(f"🔗 <b>Sizning taklif havolangiz:</b>\n\n{ref_link}\n\nYuqoridagi havolani tarqating. Har bir to'liq o'tgan taklif uchun <b>{get_ref_price():,} so'm</b> beriladi.")

@dp.message(F.text == "💳 Hisobim")
async def my_account(message: types.Message):
    u = execute_query("SELECT phone, balance, refs_count, withdrawn FROM users WHERE user_id=?", (message.from_user.id,), fetchone=True)
    if u:
        await message.answer(f"💳 <b>Hisobim:</b>\n\n👤 ID: <code>{message.from_user.id}</code>\n📱 Tel: {u[0]}\n💰 Balans: <b>{u[1]:,} so'm</b>\n👥 Referallar: {u[2]} ta\n💸 Yechilgan: {u[3]:,} so'm")

@dp.message(F.text == "🏆 TOP 10")
async def top_users(message: types.Message):
    users = execute_query("SELECT full_name, balance FROM users ORDER BY balance DESC LIMIT 10", fetchall=True)
    text = "🏆 <b>TOP 10 - Foydalanuvchilar:</b>\n\n"
    for i, u in enumerate(users, 1): text += f"<b>{i}.</b> {u[0]} — {u[1]:,} so'm\n"
    
    my_bal = execute_query("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,), fetchone=True)[0]
    rank = execute_query("SELECT COUNT(*)+1 FROM users WHERE balance > ?", (my_bal,), fetchone=True)[0]
    await message.answer(text + f"\n📍 Siz <b>{rank}-o'rindasiz</b>")

@dp.message(F.text == "🧾 To'lovlar tarixi")
async def history_btn(message: types.Message):
    ikb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💸 Kanalga o'tish", url=KANAL_LINK)]])
    await message.answer("📊 Barcha to'lovlar rasmiy kanalga joylanadi:", reply_markup=ikb)

@dp.message(F.text == "☎️ Murojaat")
async def contact_btn(message: types.Message):
    await message.answer(f"📞 <b>Murojaat markazi:</b>\n\n👨‍💻 Admin: {ADMIN_USER}\n⏰ Vaqt: 09:00 - 21:00")

# ================= PUL YECHISH TIZIMI =================
@dp.message(F.text == "💳 Pul yechish")
async def withdraw_start(message: types.Message):
    u = execute_query("SELECT phone FROM users WHERE user_id=?", (message.from_user.id,), fetchone=True)
    if u and u[0] == "Kiritilmagan":
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📲 Raqamni yuborish", request_contact=True)]], resize_keyboard=True)
        await message.answer("⚠️ Pul yechish uchun avval telefon raqamingizni tasdiqlang:", reply_markup=kb)
    else:
        await message.answer("💳 <b>Pul yechish tizimini tanlang:</b>", reply_markup=withdraw_kb)

@dp.message(F.contact)
async def catch_contact(message: types.Message):
    execute_query("UPDATE users SET phone=? WHERE user_id=?", (message.contact.phone_number, message.from_user.id))
    await message.answer("✅ Raqamingiz saqlandi!", reply_markup=main_menu(message.from_user.id))
    await withdraw_start(message)

@dp.callback_query(F.data.startswith("w_"))
async def withdraw_system_chosen(call: CallbackQuery, state: FSMContext):
    system = call.data.split("_")[1]
    bal = execute_query("SELECT balance FROM users WHERE user_id=?", (call.from_user.id,), fetchone=True)[0]
    if bal < 10000:
        await call.answer("❌ Minimal yechish: 10 000 so'm. Balansingiz yetarli emas.", show_alert=True)
        return
    await state.update_data(system=system, balance=bal)
    await call.message.answer(f"📝 <b>{system}</b> hisob ID raqamingizni kiriting:\n<i>(Bekor qilish -> /cancel)</i>")
    await state.set_state(BotStates.withdraw_prop)
    await call.answer()

@dp.message(BotStates.withdraw_prop)
async def w_prop_step(message: types.Message, state: FSMContext):
    await state.update_data(account_id=message.text)
    bal = (await state.get_data())['balance']
    await message.answer(f"💰 Summani yozing. (Balans: {bal:,} so'm):")
    await state.set_state(BotStates.withdraw_amount)

@dp.message(BotStates.withdraw_amount)
async def w_amount_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try: amount = int(message.text)
    except ValueError:
        await message.answer("❌ Faqat raqam yozing!")
        return

    if amount < 10000 or amount > data['balance']:
        await message.answer(f"❌ Xato summa. Minimal: 10,000 so'm. Mavjud: {data['balance']:,} so'm")
        return

    execute_query("UPDATE users SET balance=balance-?, withdrawn=withdrawn+? WHERE user_id=?", (amount, amount, message.from_user.id))
    u_phone = execute_query("SELECT phone FROM users WHERE user_id=?", (message.from_user.id,), fetchone=True)[0]
    
    adm_txt = f"🚨 <b>YANGI ZAYAVKA</b>\n\n👤 <a href='tg://user?id={message.from_user.id}'>{message.from_user.full_name}</a>\n🆔 ID: <code>{message.from_user.id}</code>\n📱 Tel: {u_phone}\n💳 Tizim: <b>{data['system']}</b>\n🔢 Rekvizit: <code>{data['account_id']}</code>\n💰 Summa: <b>{amount:,} so'm</b>"
    for adm in ADMINS:
        try: await bot.send_message(adm, adm_txt)
        except Exception: pass

    await message.answer("✅ So'rov adminga ketdi. 24 soat ichida tushirib beriladi.", reply_markup=main_menu(message.from_user.id))
    await state.clear()

# ================= PROMOKOD (USER) =================
@dp.message(F.text == "🎁 Promokod")
async def user_promo_start(message: types.Message, state: FSMContext):
    await message.answer("🎁 Promokodni yozing:\n<i>(Bekor qilish -> /cancel)</i>")
    await state.set_state(BotStates.enter_promo)

@dp.message(BotStates.enter_promo)
async def check_promo_user(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    p = execute_query("SELECT reward, uses FROM promocodes WHERE code=?", (code,), fetchone=True)
    if not p or p[1] <= 0:
        await message.answer("❌ Promokod xato yoki limiti tugagan.", reply_markup=main_menu(message.from_user.id))
    elif execute_query("SELECT 1 FROM used_promos WHERE user_id=? AND code=?", (message.from_user.id, code), fetchone=True):
        await message.answer("❌ Siz bundan avval foydalangansiz!", reply_markup=main_menu(message.from_user.id))
    else:
        execute_query("UPDATE promocodes SET uses=uses-1 WHERE code=?", (code,))
        execute_query("UPDATE users SET balance=balance+? WHERE user_id=?", (p[0], message.from_user.id))
        execute_query("INSERT INTO used_promos VALUES (?, ?)", (message.from_user.id, code))
        await message.answer(f"🎉 <b>Promokod ishladi!</b> Balansga {p[0]:,} so'm qo'shildi.", reply_markup=main_menu(message.from_user.id))
    await state.clear()

# ================= ADMIN PANEL =================
@dp.message(F.text == "🔐 Admin Panel", F.from_user.id.in_(ADMINS))
async def admin_lobby(message: types.Message):
    await message.answer("🔐 Admin panel:", reply_markup=admin_kb)

@dp.message(F.text == "⬅️ Bosh menyu", F.from_user.id.in_(ADMINS))
async def back_to_m(message: types.Message):
    await message.answer("Bosh menyu:", reply_markup=main_menu(message.from_user.id))

@dp.message(F.text == "🏷 Referal narxi", F.from_user.id.in_(ADMINS))
async def ref_p_start(message: types.Message, state: FSMContext):
    await message.answer(f"Hozirgi narx: {get_ref_price()} so'm.\nYangi narxni yozing:")
    await state.set_state(BotStates.new_ref_price)

@dp.message(BotStates.new_ref_price, F.from_user.id.in_(ADMINS))
async def ref_p_save(message: types.Message, state: FSMContext):
    try:
        execute_query("INSERT OR REPLACE INTO settings VALUES ('ref_price', ?)", (int(message.text),))
        await message.answer("✅ Saqlandi!", reply_markup=admin_kb)
    except ValueError: await message.answer("Faqat raqam!")
    await state.clear()

@dp.message(F.text == "🎁 Promokod yaratish", F.from_user.id.in_(ADMINS))
async def new_pr_1(message: types.Message, state: FSMContext):
    await message.answer("Promokod nomini yozing (Masalan: SALOM):")
    await state.set_state(BotStates.promo_name)

@dp.message(BotStates.promo_name, F.from_user.id.in_(ADMINS))
async def new_pr_2(message: types.Message, state: FSMContext):
    await state.update_data(code=message.text.strip().upper())
    await message.answer("Qancha bonus beradi? (Masalan: 5000):")
    await state.set_state(BotStates.promo_reward)

@dp.message(BotStates.promo_reward, F.from_user.id.in_(ADMINS))
async def new_pr_3(message: types.Message, state: FSMContext):
    try:
        await state.update_data(reward=int(message.text))
        await message.answer("Necha kishi ishlata oladi? (Limit):")
        await state.set_state(BotStates.promo_uses)
    except ValueError: await message.answer("Raqam yozing!")

@dp.message(BotStates.promo_uses, F.from_user.id.in_(ADMINS))
async def new_pr_4(message: types.Message, state: FSMContext):
    try:
        d = await state.get_data()
        execute_query("INSERT OR REPLACE INTO promocodes VALUES (?, ?, ?)", (d['code'], d['reward'], int(message.text)))
        await message.answer(f"✅ Promokod tayyor!\nKod: <code>{d['code']}</code>\nBonus: {d['reward']} so'm", reply_markup=admin_kb)
        await state.clear()
    except ValueError: await message.answer("Raqam yozing!")

@dp.message(F.text == "📊 Barcha statistika", F.from_user.id.in_(ADMINS))
async def get_all_stats(message: types.Message):
    users_c = execute_query("SELECT COUNT(*) FROM users", fetchone=True)[0]
    bal_sum = execute_query("SELECT SUM(balance) FROM users", fetchone=True)[0] or 0
    w_sum = execute_query("SELECT SUM(withdrawn) FROM users", fetchone=True)[0] or 0
    await message.answer(f"📊 <b>Statistika:</b>\n\n👥 Jami a'zolar: {users_c} ta\n💰 A'zolardagi pul: {bal_sum:,} so'm\n💸 To'langan summa: {w_sum:,} so'm")

@dp.message(F.text == "🗣 Xabar yuborish", F.from_user.id.in_(ADMINS))
async def bc_1(message: types.Message, state: FSMContext):
    await message.answer("Tarqatmoqchi bo'lgan xabaringizni yuboring:")
    await state.set_state(BotStates.broadcast_msg)

@dp.message(BotStates.broadcast_msg, F.from_user.id.in_(ADMINS))
async def bc_2(message: types.Message, state: FSMContext):
    users = execute_query("SELECT user_id FROM users", fetchall=True)
    c = 0
    await message.answer("⏳ Xabar tarqatilmoqda...")
    for u in users:
        try:
            await message.copy_to(u[0])
            c += 1
            await asyncio.sleep(0.05)
        except Exception: pass
    await message.answer(f"✅ Xabar {c} kishiga bordi!", reply_markup=admin_kb)
    await state.clear()

# ================= RENDER WEBSERVER =================
async def handle_ping(request):
    return web.Response(text="Bot is running inside Render!")

async def start_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    init_db()
    await start_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

