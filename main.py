# ============================================================
#  🤖 ANIMATED TELEGRAM BOT  —  Render Ready
#  File: bot.py
#  Features:
#   ✅ Purane host ka webhook auto-remove (delete_webhook)
#   ✅ Animated buttons / loading frames
#   ✅ Admin Panel (Stats, Broadcast, Users)
#   ✅ SQLite user database
#   ✅ Render Web Service compatible (PORT binding)
# ============================================================

import asyncio
import html
import logging
import os
import sqlite3
from datetime import datetime

from aiohttp import web

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

# ============================================================
#  ⚙️  CONFIG  (Render → Environment Variables me daalna)
# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8473093687:AAGf4cWInGJsPgtPlchg-VmKEqXMVp8Ypwo")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8388115033"))
DB_PATH = os.getenv("DB_PATH", "bot_data.db")

# Yahan apne channel / support link daal do
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/telegram")
SUPPORT_URL = os.getenv("SUPPORT_URL", "https://t.me/telegram")

# ============================================================
#  🎞️  ANIMATION FRAMES
# ============================================================
LOADING_FRAMES = ["🕐", "🕑", "🕒", "🕓", "🕔", "🕕", "🕖", "🕗", "🕘", "🕙", "🕚", "🕛"]
WELCOME_FRAMES = ["👋", "👋✨", "✨🎉", "🎉🤖", "🤖💫", "💫✅"]
PARTY_FRAMES = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "⚪", "⚫", "🌟", "✨", "💫", "⭐"]

# ============================================================
#  🗄️  DATABASE
# ============================================================
def db_init() -> None:
    con = sqlite3.connect(DB_PATH)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            first_name  TEXT,
            joined_at   TEXT
        )
        """
    )
    con.commit()
    con.close()


def add_user(user) -> bool:
    """Naya user add karta hai. True = naya, False = purana."""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT 1 FROM users WHERE user_id = ?", (user.id,))
    exists = cur.fetchone() is not None
    if not exists:
        cur.execute(
            "INSERT INTO users (user_id, username, first_name, joined_at) VALUES (?,?,?,?)",
            (user.id, user.username or "", user.first_name or "", datetime.now().isoformat()),
        )
        con.commit()
    con.close()
    return not exists


def total_users() -> int:
    con = sqlite3.connect(DB_PATH)
    n = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    con.close()
    return n


def all_users() -> list[int]:
    con = sqlite3.connect(DB_PATH)
    rows = con.execute("SELECT user_id FROM users").fetchall()
    con.close()
    return [r[0] for r in rows]


def today_users() -> int:
    con = sqlite3.connect(DB_PATH)
    today = datetime.now().strftime("%Y-%m-%d")
    n = con.execute(
        "SELECT COUNT(*) FROM users WHERE joined_at LIKE ?", (today + "%",)
    ).fetchone()[0]
    con.close()
    return n


# ============================================================
#  🤖 BOT + DISPATCHER
# ============================================================
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())


# ============================================================
#  ⌨️  KEYBOARDS
# ============================================================
def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Channel", url=CHANNEL_URL),
                InlineKeyboardButton(text="💬 Support", url=SUPPORT_URL),
            ],
            [
                InlineKeyboardButton(text="👤 My Profile", callback_data="profile"),
                InlineKeyboardButton(text="🎬 Animation", callback_data="anim"),
            ],
            [
                InlineKeyboardButton(text="ℹ️ Help", callback_data="help"),
                InlineKeyboardButton(text="📊 Stats", callback_data="stats"),
            ],
        ]
    )


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="back_home")]]
    )


def admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Bot Stats", callback_data="admin_stats")],
            [InlineKeyboardButton(text="📣 Broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton(text="👥 Users List", callback_data="admin_users")],
            [InlineKeyboardButton(text="🔙 Back", callback_data="back_home")],
        ]
    )


# ============================================================
#  ✨ ANIMATION HELPERS
# ============================================================
async def animate_new(message: Message, frames, final_text, keyboard=None, delay=0.35):
    """Naya message bhej kar usko frames se animate karta hai."""
    sent = await message.answer(frames[0])
    for frame in frames[1:]:
        await asyncio.sleep(delay)
        try:
            await sent.edit_text(frame)
        except TelegramBadRequest:
            pass
    await asyncio.sleep(delay)
    try:
        await sent.edit_text(final_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    except TelegramBadRequest:
        await message.answer(final_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    return sent


async def animate_edit(callback: CallbackQuery, frames, final_text, keyboard=None, delay=0.22):
    """Purane message ko frames se animate karke naya text dikhata hai."""
    for frame in frames:
        try:
            await callback.message.edit_text(frame)
        except TelegramBadRequest:
            pass
        await asyncio.sleep(delay)
    try:
        await callback.message.edit_text(
            final_text, reply_markup=keyboard, parse_mode=ParseMode.HTML
        )
    except TelegramBadRequest:
        pass


# ============================================================
#  🧠 FSM STATES
# ============================================================
class BroadcastState(StatesGroup):
    waiting = State()


# ============================================================
#  🚀 COMMAND HANDLERS
# ============================================================
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    is_new = add_user(message.from_user)
    name = html.escape(message.from_user.first_name or "Dost")

    text = (
        f"<b>✨ Namaste {name}! ✨</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 Main ek <b>Animated Telegram Bot</b> hoon.\n"
        f"🎯 Neeche ke buttons se kaam karo.\n\n"
        f"🆔 <b>Tumhari ID:</b> <code>{message.from_user.id}</code>\n"
        f"👑 <b>Role:</b> {'Admin ✅' if message.from_user.id == ADMIN_ID else 'User 👤'}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    if is_new:
        text += "\n\n🎉 <i>Aapka swagat hai! Aap naye member ho.</i>"

    await animate_new(message, WELCOME_FRAMES, text, main_menu_kb())


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "<b>ℹ️ HELP MENU</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "/start — Bot dobara start karo\n"
        "/help — Yeh help menu\n"
        "/profile — Apni profile dekho\n"
        "/admin — Admin panel (sirf admin)\n"
        "/cancel — Koi bhi kaam cancel karo\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💡 Har button click par animation dikhegi!",
        reply_markup=back_kb(),
    )


@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    u = message.from_user
    text = (
        f"👤 <b>YOUR PROFILE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📛 <b>Name:</b> {html.escape(u.full_name)}\n"
        f"🔗 <b>Username:</b> @{u.username if u.username else 'None'}\n"
        f"🆔 <b>ID:</b> <code>{u.id}</code>\n"
        f"🌐 <b>Language:</b> {u.language_code}\n"
        f"👑 <b>Role:</b> {'Admin ✅' if u.id == ADMIN_ID else 'User 👤'}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back", callback_data="back_home")]
        ]
    )
    if u.id == ADMIN_ID:
        kb.inline_keyboard.insert(
            0, [InlineKeyboardButton(text="🛠 Admin Panel", callback_data="admin_panel")]
        )
    await animate_new(message, LOADING_FRAMES[:6], text, kb)


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ <b>Access Denied!</b>\nAap admin nahi ho.")
    await animate_new(
        message,
        ["🔐", "🔓", "🛠️", "✅"],
        "<b>🛠️ ADMIN PANEL</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        "Neeche se option choose karo 👇\n━━━━━━━━━━━━━━━━━━━━",
        admin_kb(),
    )


@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ <b>Cancel ho gaya.</b>", reply_markup=back_kb())


# ============================================================
#  🔘 CALLBACK HANDLERS (Animated Buttons)
# ============================================================
@dp.callback_query(F.data == "back_home")
async def cb_back_home(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("🏠 Home")
    u = callback.from_user
    text = (
        f"<b>✨ Main Menu ✨</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 Kaise madad kar sakta hoon, {html.escape(u.first_name or 'Dost')}?\n"
        f"👇 Neeche se choose karo\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    await animate_edit(callback, LOADING_FRAMES[:5], text, main_menu_kb())


@dp.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery):
    await callback.answer("👤 Loading profile...")
    u = callback.from_user
    text = (
        f"👤 <b>YOUR PROFILE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📛 <b>Name:</b> {html.escape(u.full_name)}\n"
        f"🔗 <b>Username:</b> @{u.username if u.username else 'None'}\n"
        f"🆔 <b>ID:</b> <code>{u.id}</code>\n"
        f"🌐 <b>Language:</b> {u.language_code}\n"
        f"👑 <b>Role:</b> {'Admin ✅' if u.id == ADMIN_ID else 'User 👤'}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    kb = back_kb()
    if u.id == ADMIN_ID:
        kb.inline_keyboard.insert(
            0, [InlineKeyboardButton(text="🛠 Admin Panel", callback_data="admin_panel")]
        )
    await animate_edit(callback, LOADING_FRAMES[:6], text, kb)


@dp.callback_query(F.data == "anim")
async def cb_anim(callback: CallbackQuery):
    await callback.answer("🎬 Animation chal rahi hai...")
    text = (
        "🎬 <b>ANIMATION DEMO</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "✨ Dekha? Buttons par click karte hi\n"
        "🔄 message animate hota hai!\n\n"
        "🎯 Yeh trick Telegram inline buttons\n"
        "    ke saath <b>edit_text</b> se hoti hai.\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await animate_edit(callback, PARTY_FRAMES, text, back_kb(), delay=0.18)


@dp.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery):
    await callback.answer("ℹ️ Help")
    text = (
        "<b>ℹ️ HELP MENU</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "/start — Bot dobara start karo\n"
        "/help — Yeh help menu\n"
        "/profile — Apni profile dekho\n"
        "/admin — Admin panel (sirf admin)\n"
        "/cancel — Kaam cancel karo\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💡 Har button click par animation dikhegi!"
    )
    await animate_edit(callback, LOADING_FRAMES[:5], text, back_kb())


@dp.callback_query(F.data == "stats")
async def cb_stats(callback: CallbackQuery):
    await callback.answer("📊 Stats")
    text = (
        "📊 <b>BOT STATISTICS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 <b>Total Users:</b> {total_users()}\n"
        f"🆕 <b>Aaj ke Users:</b> {today_users()}\n"
        f"⚡ <b>Status:</b> Online ✅\n"
        f"🕒 <b>Time:</b> {datetime.now().strftime('%d-%m-%Y %H:%M')}\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await animate_edit(callback, LOADING_FRAMES[:6], text, back_kb())


# ---------------- ADMIN CALLBACKS ----------------
@dp.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("❌ Aap admin nahi ho!", show_alert=True)
    await callback.answer("🛠️ Admin Panel")
    text = (
        "<b>🛠️ ADMIN PANEL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Neeche se option choose karo 👇\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await animate_edit(callback, ["🔐", "🔓", "🛠️", "✅"], text, admin_kb())


@dp.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("❌ Access Denied!", show_alert=True)
    await callback.answer("📊 Loading...")
    text = (
        "📊 <b>ADMIN STATISTICS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 <b>Total Users:</b> {total_users()}\n"
        f"🆕 <b>Today Joined:</b> {today_users()}\n"
        f"👑 <b>Admin ID:</b> <code>{ADMIN_ID}</code>\n"
        f"🤖 <b>Bot:</b> @{(await bot.get_me()).username}\n"
        f"🕒 <b>Server Time:</b> {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await animate_edit(callback, LOADING_FRAMES[:6], text, admin_kb())


@dp.callback_query(F.data == "admin_users")
async def cb_admin_users(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("❌ Access Denied!", show_alert=True)
    await callback.answer("👥 Loading...")
    users = all_users()
    preview = "\n".join(f"• <code>{u}</code>" for u in users[:30]) or "Koi user nahi."
    text = (
        f"👥 <b>USERS LIST</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Total: <b>{len(users)}</b>\n\n"
        f"{preview}\n"
        f"{'... aur bhi' if len(users) > 30 else ''}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    await animate_edit(callback, LOADING_FRAMES[:5], text, admin_kb())


@dp.callback_query(F.data == "admin_broadcast")
async def cb_broadcast(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("❌ Access Denied!", show_alert=True)
    await state.set_state(BroadcastState.waiting)
    await callback.answer("📣 Broadcast Mode")
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="back_home")]]
    )
    await animate_edit(
        callback,
        ["📣", "📢", "📨"],
        "📣 <b>BROADCAST MODE</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Jo message bhejna hai wo bhejo\n"
        "(text / photo / video — kuch bhi)\n\n"
        "❌ Cancel karne ke liye /cancel\n"
        "━━━━━━━━━━━━━━━━━━━━",
        kb,
    )


@dp.message(BroadcastState.waiting)
async def do_broadcast(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.clear()

    users = all_users()
    total = len(users)
    if total == 0:
        return await message.answer("❌ Koi user nahi hai broadcast ke liye.")

    status = await message.answer(f"📤 <b>Broadcasting...</b>\n\n0 / {total}")
    sent = failed = 0

    for i, uid in enumerate(users, 1):
        try:
            await message.copy_to(uid)
            sent += 1
        except Exception:
            failed += 1

        if i % 25 == 0 or i == total:
            try:
                await status.edit_text(
                    f"📤 <b>Broadcasting...</b>\n\n{i} / {total}\n"
                    f"✅ Sent: {sent}   ❌ Failed: {failed}"
                )
            except TelegramBadRequest:
                pass
        await asyncio.sleep(0.05)  # flood-safe

    await status.edit_text(
        f"✅ <b>BROADCAST COMPLETE!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Total: {total}\n"
        f"✅ Sent: {sent}\n"
        f"❌ Failed: {failed}\n"
        f"━━━━━━━━━━━━━━━━━━━━",
        reply_markup=back_kb(),
    )


# ============================================================
#  🌐 WEB SERVER (Render Web Service ke liye zaroori)
# ============================================================
async def health(request):
    return web.Response(
        text=f"🤖 Bot is running!\nUsers: {total_users()}\nTime: {datetime.now()}",
        content_type="text/plain",
    )


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"🌐 Web server started on port {port}")


# ============================================================
#  ▶️ MAIN
# ============================================================
async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    log = logging.getLogger("BOT")

    db_init()
    log.info("🗄️ Database ready")

    # ---------------------------------------------------------
    # ⭐ SABSE IMPORTANT STEP:
    # Purane host (Render/Heroku/VPS) ka webhook hata deta hai.
    # Isse naya host clean tarike se polling start kar pata hai.
    # ---------------------------------------------------------
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        log.info("🧹 Purane host ka webhook REMOVE ho gaya (drop_pending_updates=True)")
    except Exception as e:
        log.warning(f"Webhook delete me dikkat: {e}")

    # Bot commands set karo (menu button)
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="🚀 Bot Start karo"),
            BotCommand(command="profile", description="👤 Meri Profile"),
            BotCommand(command="help", description="ℹ️ Help Menu"),
            BotCommand(command="admin", description="🛠️ Admin Panel"),
            BotCommand(command="cancel", description="❌ Cancel"),
        ]
    )
    log.info("⌨️ Bot commands set ho gaye")

    # Render Web Service ke liye health server
    await start_web_server()

    me = await bot.get_me()
    log.info(f"✅ Bot started: @{me.username} (ID: {me.id})")
    log.info(f"👑 Admin ID: {ADMIN_ID}")

    # Polling start — yahi se bot chalta hai
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("🛑 Bot band ho gaya")
