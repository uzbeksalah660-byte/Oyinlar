import asyncio
import logging
import sqlite3
import os
import random
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web

# ================= ASOSIY SOZLAMALAR =================
TOKEN = "8853488093:AAG799kEMJe9MfJzk3j9udHeCXHoZtxlBYw"
ADMINS = [8057184376, 8526661272, 8148767301]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# ================= BAZA (SQLITE) =================
def init_db():
    with sqlite3.connect("database.db") as conn:
        cur = conn.cursor()
        # Foydalanuvchilar jadvali
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT,
                phone TEXT DEFAULT 'none',
                balance INTEGER DEFAULT 0,
                refs_count INTEGER DEFAULT 0,
                withdrawn INTEGER DEFAULT 0,
                invited_by INTEGER DEFAULT 0,
                passed_captcha INTEGER DEFAULT 0,
                passed_phone INTEGER DEFAULT 0
            )
        ''')
        # Dinamik sozlamalar jadvali
        cur.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                val TEXT
            )
        ''')
        # Promokodlar jadvali
        cur.execute('''
            CREATE TABLE IF NOT EXISTS promocodes (
                code TEXT PRIMARY KEY,
                reward INTEGER,
                uses INTEGER
            )
        ''')
        # Ishlatilgan promokodlar hisobi
        cur.execute('''
            CREATE TABLE IF NOT EXISTS used_promos (
                user_id INTEGER,
                code TEXT,
                PRIMARY KEY (user_id, code)
            )
        ''')
        # Boshlang'ich standart sozlamalarni kiritish
        cur.executemany("INSERT OR IGNORE INTO settings VALUES (?, ?)", [
            ('ref_price', '1000'),
            ('admin_contact', '@AzartnikMir'),
            ('history_channel', 'https://t.me/SizningKanal_ID')
        ])
        conn.commit()

def get_setting(key, default_val=""):
    with sqlite3.connect("database.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT val FROM settings WHERE key=?", (key,))
        res = cur.fetchone()
        return res[0] if res else default_val

def set_setting(key, val):
    with sqlite3.connect("database.db") as conn:
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO settings VALUES (?, ?)", (str(key), str(val)))
        conn.commit()

def get_ref_price():
    try: return int(get_setting('ref_price', '1000'))
    except ValueError: return 1000

# ================= KLAVIATURALAR =================
def phone_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📲 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )

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
        [KeyboardButton(text="👤 Admin lichkasi"), KeyboardButton(text="📢 To'lov kanali")],
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
class RegStates(StatesGroup):
    captcha = State()
    phone = State()

class AdminStates(StatesGroup):
    new_ref_price = State()
    new_admin_contact = State()
    new_history_channel = State()
    promo_name, promo_reward, promo_uses = State(), State(), State()
    broadcast = State()

class UserStates(StatesGroup):
    enter_promo = State()
    withdraw_sys, withdraw_acc, withdraw_amount = State(), State(), State()

# ================= TEKSHIRUVCHILAR =================
def make_captcha():
    n1 = random.randint(10, 49)
    n2 = random.randint(10, 49)
    return n1, n2, n1 + n2

async def is_fully_verified(message: types.Message) -> bool:
    with sqlite3.connect("database.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT passed_phone FROM users WHERE user_id=?", (message.from_user.id,))
        res = cur.fetchone()
        if not res or not res[0]:
            await message.answer("⚠️ Botdan foydalanish uchun /start buyrug'ini bosing va ro'yxatdan o'ting!")
            return False
        return True

# ================= BOSHLANG'ICH RO'YXATDAN O'TISH =================
@dp.message(Command("cancel"))
async def cancel_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    if await is_fully_verified(message):
        await message.answer("Bosh menyu:", reply_markup=main_menu(message.from_user.id))

@dp.message(CommandStart())
async def start_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    
    # Referal ID ni aniqlash
    parts = message.text.split()
    invited_by = 0
    if len(parts) > 1 and parts[1].startswith("ref_"):
        try:
            inv = int(parts[1].replace("ref_", ""))
            if inv != user_id: invited_by = inv
        except ValueError: pass

    with sqlite3.connect("database.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT passed_captcha, passed_phone FROM users WHERE user_id=?", (user_id,))
        u = cur.fetchone()

        if not u:
            cur.execute("INSERT INTO users (user_id, full_name, invited_by) VALUES (?, ?, ?)", 
                        (user_id, full_name, invited_by))
            conn.commit()
            p_cap, p_phone = 0, 0
        else:
            p_cap, p_phone = u[0], u[1]

    # 1-BOSQICH: CAPTCHA
    if not p_cap:
        n1, n2, ans = make_captcha()
        await state.set_state(RegStates.captcha)
        await state.update_data(captcha_ans=ans)
        await message.answer(
            f"🤖 <b>Xavfsizlik tekshiruvi (Captcha):</b>\n\n"
            f"Botdan foydalanish uchun quyidagi misolni yeching:\n\n"
            f"👉 <b>{n1} + {n2} = ?</b>\n\n"
            f"<i>(Javobni faqat raqam ko'rinishida yozib yuboring)</i>",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    # 2-BOSQICH: TELEFON RAQAM
    if not p_phone:
        await state.set_state(RegStates.phone)
        await message.answer(
            "⚠️ <b>Hisobni tasdiqlash:</b>\n\n"
            "Botdan to'liq foydalanish va xavfsizlik uchun pastdagi <b>«📲 Telefon raqamni yuborish»</b> tugmasini bosing.",
            reply_markup=phone_kb()
        )
        return

    # 3-BOSQICH: ALLAQACHON O'TGAN
    await state.clear()
    await message.answer(f"👋 Xush kelibsiz, <b>{full_name}</b>!", reply_markup=main_menu(user_id))

@dp.message(RegStates.captcha)
async def catch_captcha(message: types.Message, state: FSMContext):
    data = await state.get_data()
    correct_ans = data.get("captcha_ans")

    if not message.text or not message.text.isdigit():
        await message.answer("❌ Iltimos, faqat raqam kiriting!")
        return

    if int(message.text) == correct_ans:
        with sqlite3.connect("database.db") as conn:
            conn.cursor().execute("UPDATE users SET passed_captcha=1 WHERE user_id=?", (message.from_user.id,))
            conn.commit()

        await state.set_state(RegStates.phone)
        await message.answer(
            "✅ <b>Qoyil, tekshiruvdan o'tdingiz!</b>\n\n"
            "Endi nakrutkaga qarshi tizimni faollashtirish uchun pastdagi <b>«📲 Telefon raqamni yuborish»</b> tugmasini bosing.",
            reply_markup=phone_kb()
        )
    else:
        n1, n2, ans = make_captcha()
        await state.update_data(captcha_ans=ans)
        await message.answer(f"❌ <b>Noto'g'ri javob!</b> Qaytadan hisoblang:\n\n👉 <b>{n1} + {n2} = ?</b>")

@dp.message(F.contact)
async def catch_phone_step(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    phone = message.contact.phone_number
    if not phone.startswith("+"): phone = "+" + phone

    with sqlite3.connect("database.db") as conn:
        cur = conn.cursor()
        
        # ANTI-FRAUD: Boshqa odam bu raqamni ishlatganmi?
        cur.execute("SELECT user_id FROM users WHERE phone=? AND user_id!=?", (phone, user_id))
        if cur.fetchone():
            await message.answer(
                "🚫 <b>XATOLIK!</b>\n\nBu telefon raqamidan avval ro'yxatdan o'tilgan! Bitta raqam orqali faqat 1 marta foydalanish mumkin.",
                reply_markup=ReplyKeyboardRemove()
            )
            return

        cur.execute("SELECT passed_phone, invited_by FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        if not row: return

        is_ph_passed, inviter = row[0], row[1]

        if not is_ph_passed:
            cur.execute("UPDATE users SET phone=?, passed_phone=1 WHERE user_id=?", (phone, user_id))
            
            # CRITICAL: REFERAL PULINI SHU YERDA BERAMIZ!
            if inviter != 0:
                bonus = get_ref_price()
                cur.execute("UPDATE users SET balance=balance+?, refs_count=refs_count+1 WHERE user_id=?", (bonus, inviter))
                try:
                    await bot.send_message(inviter, f"🎉 Havolangiz orqali do'stingiz ro'yxatdan o'tdi!\n💰 Balansingizga <b>{bonus:,} so'm</b> qo'shildi.")
                except Exception: pass

        conn.commit()

    await state.clear()
    await message.answer("🎉 <b>Tabriklaymiz! Ro'yxatdan muvaffaqiyatli o'tdingiz.</b>", reply_markup=main_menu(user_id))

# ================= ASOSIY MENYU TUGMALARI =================
@dp.message(F.text == "💰 Pul ishlash")
async def menu_ref_link(message: types.Message):
    if not await is_fully_verified(message): return
    bot_me = await bot.me()
    link = f"https://t.me/{bot_me.username}?start=ref_{message.from_user.id}"
    await message.answer(f"🔗 <b>Sizning taklif havolangiz:</b>\n\n{link}\n\nYuqoridagi havolani tarqating. Har bir to'liq o'tgan taklif uchun <b>{get_ref_price():,} so'm</b> beriladi.")

@dp.message(F.text == "💳 Hisobim")
async def menu_account(message: types.Message):
    if not await is_fully_verified(message): return
    with sqlite3.connect("database.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT phone, balance, refs_count, withdrawn FROM users WHERE user_id=?", (message.from_user.id,))
        u = cur.fetchone()
    if u:
        await message.answer(f"💳 <b>Hisobim:</b>\n\n👤 ID: <code>{message.from_user.id}</code>\n📱 Tel: {u[0]}\n💰 Balans: <b>{u[1]:,} so'm</b>\n👥 Referallar: {u[2]} ta\n💸 Yechilgan: {u[3]:,} so'm")

@dp.message(F.text == "🏆 TOP 10")
async def menu_top(message: types.Message):
    if not await is_fully_verified(message): return
    with sqlite3.connect("database.db") as conn:
        cur = conn.cursor()
        users = cur.execute("SELECT full_name, balance FROM users ORDER BY balance DESC LIMIT 10").fetchall()
        my_bal = cur.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,)).fetchone()[0]
        my_rank = cur.execute("SELECT COUNT(*)+1 FROM users WHERE balance > ?", (my_bal,)).fetchone()[0]

    txt = "🏆 <b>TOP 10 - Foydalanuvchilar:</b>\n\n"
    for i, u in enumerate(users, 1): txt += f"<b>{i}.</b> {u[0]} — {u[1]:,} so'm\n"
    await message.answer(txt + f"\n📍 Siz <b>{my_rank}-o'rindasiz</b>")

@dp.message(F.text == "🧾 To'lovlar tarixi")
async def menu_history(message: types.Message):
    if not await is_fully_verified(message): return
    channel_url = get_setting('history_channel', 'https://t.me/')
    ikb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💸 Kanalga o'tish", url=channel_url)]])
    await message.answer("📊 Barcha to'lovlar rasmiy kanalga joylanadi:", reply_markup=ikb)

@dp.message(F.text == "☎️ Murojaat")
async def menu_contact(message: types.Message):
    if not await is_fully_verified(message): return
    adm_nick = get_setting('admin_contact', '@AzartnikMir')
    await message.answer(f"📞 <b>Murojaat markazi:</b>\n\n👨‍💻 Admin: {adm_nick}\n⏰ Vaqt: 09:00 - 21:00")

# ================= PUL YECHISH =================
@dp.message(F.text == "💳 Pul yechish")
async def withdraw_init(message: types.Message):
    if not await is_fully_verified(message): return
    await message.answer("💳 <b>Pul yechish tizimini tanlang:</b>", reply_markup=withdraw_kb)

@dp.callback_query(F.data.startswith("w_"))
async def w_sys_selected(call: CallbackQuery, state: FSMContext):
    sys_name = call.data.split("_")[1]
    with sqlite3.connect("database.db") as conn:
        bal = conn.cursor().execute("SELECT balance FROM users WHERE user_id=?", (call.from_user.id,)).fetchone()[0]
    
    if bal < 10000:
        await call.answer("❌ Minimal yechish summasi: 10 000 so'm.", show_alert=True)
        return

    await state.set_state(UserStates.withdraw_acc)
    await state.update_data(sys=sys_name, bal=bal)
    await call.message.answer(f"📝 <b>{sys_name}</b> hisob raqamingizni (ID) kiriting:\n<i>(Bekor qilish -> /cancel)</i>")
    await call.answer()

@dp.message(UserStates.withdraw_acc)
async def w_acc_step(message: types.Message, state: FSMContext):
    await state.update_data(acc_id=message.text.strip())
    bal = (await state.get_data())['bal']
    await state.set_state(UserStates.withdraw_amount)
    await message.answer(f"💰 Summani yozing. (Mavjud: {bal:,} so'm):")

@dp.message(UserStates.withdraw_amount)
async def w_amt_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try: amt = int(message.text)
    except ValueError:
        await message.answer("❌ Faqat raqam yozing!")
        return

    if amt < 10000 or amt > data['bal']:
        await message.answer(f"❌ Xato summa. Minimal: 10 000, Maksimal: {data['bal']:,} so'm")
        return

    user_id = message.from_user.id
    with sqlite3.connect("database.db") as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET balance=balance-?, withdrawn=withdrawn+? WHERE user_id=?", (amt, amt, user_id))
        phone = cur.execute("SELECT phone FROM users WHERE user_id=?", (user_id,)).fetchone()[0]
        conn.commit()

    adm_msg = f"🚨 <b>PUL YECHISH SO'ROVI</b>\n\n👤 User: <a href='tg://user?id={user_id}'>{message.from_user.full_name}</a>\n🆔 ID: <code>{user_id}</code>\n📱 Tel: {phone}\n💳 Tizim: <b>{data['sys']}</b>\n🔢 Rekvizit: <code>{data['acc_id']}</code>\n💰 Summa: <b>{amt:,} so'm</b>"
    for admin_id in ADMINS:
        try: await bot.send_message(admin_id, adm_msg)
        except Exception: pass

    await message.answer("✅ So'rov adminga yuborildi. 24 soat ichida to'lab beriladi.", reply_markup=main_menu(user_id))
    await state.clear()

# ================= PROMOKOD (USER) =================
@dp.message(F.text == "🎁 Promokod")
async def promo_init(message: types.Message, state: FSMContext):
    if not await is_fully_verified(message): return
    await state.set_state(UserStates.enter_promo)
    await message.answer("🎁 Promokodni yozing:\n<i>(Bekor qilish -> /cancel)</i>")

@dp.message(UserStates.enter_promo)
async def promo_enter(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    user_id = message.from_user.id

    with sqlite3.connect("database.db") as conn:
        cur = conn.cursor()
        promo = cur.execute("SELECT reward, uses FROM promocodes WHERE code=?", (code,)).fetchone()
        
        if not promo or promo[1] <= 0:
            await message.answer("❌ Promokod xato yoki limiti tugagan.", reply_markup=main_menu(user_id))
        elif cur.execute("SELECT 1 FROM used_promos WHERE user_id=? AND code=?", (user_id, code)).fetchone():
            await message.answer("❌ Siz bu promokodni avval ishlatingiz!", reply_markup=main_menu(user_id))
        else:
            cur.execute("UPDATE promocodes SET uses=uses-1 WHERE code=?", (code,))
            cur.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (promo[0], user_id))
            cur.execute("INSERT INTO used_promos VALUES (?, ?)", (user_id, code))
            conn.commit()
            await message.answer(f"🎉 <b>Promokod ishladi!</b> Balansga {promo[0]:,} so'm qo'shildi.", reply_markup=main_menu(user_id))
            
    await state.clear()

# ================= ADMIN PANEL =================
@dp.message(F.text == "🔐 Admin Panel", F.from_user.id.in_(ADMINS))
async def adm_menu(message: types.Message):
    await message.answer("🔐 Admin panel sozlamalari:", reply_markup=admin_kb)

@dp.message(F.text == "⬅️ Bosh menyu", F.from_user.id.in_(ADMINS))
async def adm_back(message: types.Message):
    await message.answer("Bosh menyu:", reply_markup=main_menu(message.from_user.id))

@dp.message(F.text == "🏷 Referal narxi", F.from_user.id.in_(ADMINS))
async def adm_ref_p(message: types.Message, state: FSMContext):
    await state.set_state(AdminStates.new_ref_price)
    await message.answer(f"Hozirgi narx: {get_ref_price()} so'm.\nYangi narxni yozing:")

@dp.message(AdminStates.new_ref_price, F.from_user.id.in_(ADMINS))
async def adm_ref_save(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        set_setting('ref_price', message.text)
        await message.answer("✅ Referal narxi yangilandi!", reply_markup=admin_kb)
    else: await message.answer("❌ Faqat raqam!")
    await state.clear()

@dp.message(F.text == "👤 Admin lichkasi", F.from_user.id.in_(ADMINS))
async def adm_nick_init(message: types.Message, state: FSMContext):
    await state.set_state(AdminStates.new_admin_contact)
    await message.answer(f"Hozirgi lichka: {get_setting('admin_contact')}\nYangi username yozing (Masalan: @AzartnikMir):")

@dp.message(AdminStates.new_admin_contact, F.from_user.id.in_(ADMINS))
async def adm_nick_save(message: types.Message, state: FSMContext):
    set_setting('admin_contact', message.text.strip())
    await message.answer("✅ Murojaat lichkasi o'zgardi!", reply_markup=admin_kb)
    await state.clear()
@dp.message(F.text == "📢 To'lov kanali", F.from_user.id.in_(ADMINS))
async def adm_chan_init(message: types.Message, state: FSMContext):
    await state.set_state(AdminStates.new_history_channel)
    await message.answer(f"Hozirgi kanal: {get_setting('history_channel')}\nYangi kanal ssilkasini yuboring (https://...):")

@dp.message(AdminStates.new_history_channel, F.from_user.id.in_(ADMINS))
async def adm_chan_save(message: types.Message, state: FSMContext):
    if message.text.startswith("http"):
        set_setting('history_channel', message.text.strip())
        await message.answer("✅ To'lovlar tarixi kanali yangilandi!", reply_markup=admin_kb)
    else: await message.answer("❌ Ssilka http bilan boshlanishi kerak!")
    await state.clear()

@dp.message(F.text == "🎁 Promokod yaratish", F.from_user.id.in_(ADMINS))
async def adm_pr_1(message: types.Message, state: FSMContext):
    await state.set_state(AdminStates.promo_name)
    await message.answer("Promokod so'zini kiriting (Masalan: BONUS50):")

@dp.message(AdminStates.promo_name, F.from_user.id.in_(ADMINS))
async def adm_pr_2(message: types.Message, state: FSMContext):
    await state.update_data(code=message.text.strip().upper())
    await state.set_state(AdminStates.promo_reward)
    await message.answer("Qancha bonus beradi? (Masalan: 5000):")

@dp.message(AdminStates.promo_reward, F.from_user.id.in_(ADMINS))
async def adm_pr_3(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        await state.update_data(reward=int(message.text))
        await state.set_state(AdminStates.promo_uses)
        await message.answer("Necha kishi ishlata oladi? (Masalan: 100):")
    else: await message.answer("❌ Raqam yozing!")

@dp.message(AdminStates.promo_uses, F.from_user.id.in_(ADMINS))
async def adm_pr_4(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        data = await state.get_data()
        with sqlite3.connect("database.db") as conn:
            conn.cursor().execute("INSERT OR REPLACE INTO promocodes VALUES (?, ?, ?)", (data['code'], data['reward'], int(message.text)))
            conn.commit()
        await message.answer(f"✅ Promokod tayyor!\nKod: <code>{data['code']}</code>\nBonus: {data['reward']} so'm\nLimit: {message.text} ta", reply_markup=admin_kb)
        await state.clear()
    else: await message.answer("❌ Raqam yozing!")

@dp.message(F.text == "📊 Barcha statistika", F.from_user.id.in_(ADMINS))
async def adm_stats(message: types.Message):
    with sqlite3.connect("database.db") as conn:
        cur = conn.cursor()
        total_u = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        sum_bal = cur.execute("SELECT SUM(balance) FROM users").fetchone()[0] or 0
        sum_w = cur.execute("SELECT SUM(withdrawn) FROM users").fetchone()[0] or 0
    await message.answer(f"📊 <b>Umumiy statistika:</b>\n\n👥 Bot a'zolari: {total_u} ta\n💰 A'zolardagi jami pul: {sum_bal:,} so'm\n💸 To'lab berilgan: {sum_w:,} so'm")

@dp.message(F.text == "🗣 Xabar yuborish", F.from_user.id.in_(ADMINS))
async def adm_bc_1(message: types.Message, state: FSMContext):
    await state.set_state(AdminStates.broadcast)
    await message.answer("Tarqatmoqchi bo'lgan xabaringizni yuboring (Rasm, video yoki matn):")

@dp.message(AdminStates.broadcast, F.from_user.id.in_(ADMINS))
async def adm_bc_2(message: types.Message, state: FSMContext):
    with sqlite3.connect("database.db") as conn:
        users = conn.cursor().execute("SELECT user_id FROM users").fetchall()
    
    await message.answer("⏳ Xabar tarqatish boshlandi...")
    sent = 0
    for u in users:
        try:
            await message.copy_to(u[0])
            sent += 1
            await asyncio.sleep(0.05)
        except Exception: pass
    
    await message.answer(f"✅ Xabar {sent} ta foydalanuvchiga muvaffaqiyatli yetkazildi!", reply_markup=admin_kb)
    await state.clear()

# ================= RENDER WEBSERVER =================
async def ping_handler(request):
    return web.Response(text="Bot is running and kept alive by UptimeRobot!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', ping_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    init_db()
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
