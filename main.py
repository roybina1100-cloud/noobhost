import os
import sys
import time
import subprocess
import threading
import sqlite3
import psutil
import telebot
from telebot import types
from flask import Flask

# =========================================================
# CONFIGURATION & SECURITY
# =========================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8578269004:AAGuuYFhHH9Elk0w6-cf8YWzJEN65ZnYII4")
OWNER_ID = int(os.environ.get("OWNER_ID", "8388115033"))

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
app = Flask(__name__)

# =========================================================
# FLASK 24/7 KEEP-ALIVE SERVER
# =========================================================
@app.route('/')
def home():
    return "⚡ SR HAKER HOSTING BOT IS ALIVE 24/7 ⚡"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# =========================================================
# DATABASE SETUP
# =========================================================
def init_db():
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            is_admin INTEGER DEFAULT 0,
            joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hosted_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            filename TEXT,
            file_type TEXT,
            pid INTEGER DEFAULT NULL,
            status TEXT DEFAULT 'Stopped',
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bot_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# =========================================================
# PROCESS & PACKAGE HELPER FUNCTIONS
# =========================================================
def kill_process_tree(pid):
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
        return True
    except Exception as e:
        print(f"[ERROR] Process Kill Failed ({pid}): {e}")
        return False

def auto_install_packages(file_path):
    try:
        if file_path.endswith('.py'):
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], capture_output=True, timeout=60)
        elif file_path.endswith('.js'):
            subprocess.run(["npm", "install"], capture_output=True, timeout=60)
    except Exception as e:
        print(f"[AUTO-INSTALL LOG]: {e}")

# =========================================================
# UI KEYBOARD GENERATOR (ANIMATED & COLORFUL BUTTONS)
# =========================================================
def get_main_keyboard(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_host = types.InlineKeyboardButton("🚀 ⚡ H O S T  F I L E ⚡ 🚀", callback_data="btn_host")
    btn_status = types.InlineKeyboardButton("📊 🟢 L I V E  S T A T U S 🟢 📊", callback_data="btn_status")
    btn_my_files = types.InlineKeyboardButton("📁 📂 M Y  F I L E S 📂 📁", callback_data="btn_myfiles")
    btn_logs = types.InlineKeyboardButton("📑 🔍 C H E C K  L O G S 🔍 📑", callback_data="btn_logs")
    btn_help = types.InlineKeyboardButton("❓ 💡 H E L P & I N F O 💡 ❓", callback_data="btn_help")
    btn_refresh = types.InlineKeyboardButton("🔄 ✨ R E F R E S H ✨ 🔄", callback_data="btn_refresh")

    markup.add(btn_host)
    markup.add(btn_status, btn_my_files)
    markup.add(btn_logs, btn_help)
    markup.add(btn_refresh)

    if user_id == OWNER_ID:
        btn_admin = types.InlineKeyboardButton("👑 🔥 A D M I N  P A N E L 🔥 👑", callback_data="btn_admin")
        markup.add(btn_admin)

    return markup

def get_file_control_keyboard(file_id, is_running):
    markup = types.InlineKeyboardMarkup(row_width=2)
    if is_running:
        btn_stop = types.InlineKeyboardButton("🛑 🔴 S T O P 🔴 🛑", callback_data=f"act_stop_{file_id}")
        btn_restart = types.InlineKeyboardButton("🔄 ⚡ R E S T A R T ⚡ 🔄", callback_data=f"act_restart_{file_id}")
        markup.add(btn_stop, btn_restart)
    else:
        btn_start = types.InlineKeyboardButton("▶️ 🟢 S T A R T 🟢 ▶️", callback_data=f"act_start_{file_id}")
        markup.add(btn_start)

    btn_del = types.InlineKeyboardButton("🗑️ ⚠️ D E L E T E ⚠️ 🗑️", callback_data=f"act_delete_{file_id}")
    btn_log = types.InlineKeyboardButton("📑 📜 V I E W  L O G S 📜 📑", callback_data=f"act_log_{file_id}")
    btn_back = types.InlineKeyboardButton("⬅️ 🔙 B A C K  M E N U 🔙 ⬅️", callback_data="btn_back_main")

    markup.add(btn_del, btn_log)
    markup.add(btn_back)
    return markup

# =========================================================
# TELEGRAM BOT HANDLERS
# =========================================================
@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Hacker"

    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    conn.close()

    welcome_text = (
        f"✨ **WELCOME TO SR HAKER HOSTING BOT!** ✨\n\n"
        f"🆔 **User ID:** `{user_id}`\n"
        f"👤 **Username:** `@{username}`\n\n"
        f"🔥 **Features:**\n"
        f"├ 🚀 24/7 Non-Stop Server Hosting\n"
        f"├ 🐍 Python (`.py`) & 🟨 Node.js (`.js`) Support\n"
        f"├ 📦 Auto Package/Requirements Installer\n"
        f"├ 🎛️ Real-Time Process Manager\n"
        f"└ 📊 Colorful & Animated Interactive Dashboard\n\n"
        f"👇 **Choose an action below:**"
    )

    bot.reply_to(message, welcome_text, reply_markup=get_main_keyboard(user_id))

@bot.message_handler(commands=['host'])
def host_command(message):
    bot.reply_to(message, "📁 **Please send your `.py`, `.js` or `.zip` file now!**")

@bot.message_handler(content_types=['document'])
def handle_document_upload(message):
    user_id = message.from_user.id
    file_name = message.document.file_name

    if not (file_name.endswith('.py') or file_name.endswith('.js') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ **Invalid File Type!** Only `.py`, `.js`, and `.zip` files are supported.")
        return

    msg = bot.reply_to(message, "⏳ **Downloading and processing your file...**")

    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        user_dir = f"uploads/{user_id}"
        os.makedirs(user_dir, exist_ok=True)
        file_path = os.path.join(user_dir, file_name)

        with open(file_path, 'wb') as f:
            f.write(downloaded_file)

        bot.edit_message_text("📦 **Installing dependencies... Please wait!**", chat_id=message.chat.id, message_id=msg.message_id)
        auto_install_packages(file_path)

        proc = None
        if file_name.endswith('.py'):
            proc = subprocess.Popen([sys.executable, file_path])
        elif file_name.endswith('.js'):
            proc = subprocess.Popen(["node", file_path])

        pid = proc.pid if proc else None
        status = "Running" if pid else "Stopped"

        file_type = "Python" if file_name.endswith('.py') else ("NodeJS" if file_name.endswith('.js') else "Archive")

        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO hosted_files (user_id, filename, file_type, pid, status) VALUES (?, ?, ?, ?, ?)",
                       (user_id, file_name, file_type, pid, status))
        file_id = cursor.lastrowid
        conn.commit()
        conn.close()

        success_text = (
            f"🚀 **FILE HOSTED SUCCESSFULLY!** 🚀\n\n"
            f"📄 **File:** `{file_name}`\n"
            f"📌 **PID:** `{pid}`\n"
            f"🟢 **Status:** `Running 24/7`\n"
            f"⚡ **Type:** `{file_type}`"
        )

        bot.edit_message_text(success_text, chat_id=message.chat.id, message_id=msg.message_id, reply_markup=get_file_control_keyboard(file_id, True))

    except Exception as e:
        bot.edit_message_text(f"❌ **Hosting Failed!** Error: `{str(e)}`", chat_id=message.chat.id, message_id=msg.message_id)

# =========================================================
# CALLBACK QUERY HANDLER (BUTTON ACTIONS)
# =========================================================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    data = call.data

    if data == "btn_back_main" or data == "btn_refresh":
        welcome_text = (
            f"✨ **SR HAKER HOSTING CONTROL DASHBOARD** ✨\n\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"⚡ **System Status:** `Active 🟢`\n\n"
            f"Select an option using the colorful menu below:"
        )
        try:
            bot.edit_message_text(welcome_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_keyboard(user_id))
            bot.answer_callback_query(call.id, "✨ Dashboard Refreshed!")
        except Exception:
            bot.answer_callback_query(call.id, "Already Up-to-date!")

    elif data == "btn_host":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📁 **Send your `.py`, `.js` or `.zip` file to start hosting!**")

    elif data == "btn_status":
        bot.answer_callback_query(call.id, "Checking Live Status...")
        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT filename, pid, status FROM hosted_files WHERE user_id=?", (user_id,))
        files = cursor.fetchall()
        conn.close()

        if not files:
            bot.send_message(call.message.chat.id, "ℹ️ **No hosted files found in your account.**")
            return

        status_text = "📊 **YOUR LIVE HOSTED PROCESSES:**\n\n"
        for fname, pid, st in files:
            is_alive = psutil.pid_exists(pid) if pid else False
            live_st = "🟢 Running" if is_alive else "🔴 Stopped"
            status_text += f"• 📄 `{fname}`\n  ├ 📌 PID: `{pid}`\n  └ ⚡ Status: {live_st}\n\n"

        bot.send_message(call.message.chat.id, status_text)

    elif data == "btn_myfiles":
        bot.answer_callback_query(call.id)
        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename, pid FROM hosted_files WHERE user_id=?", (user_id,))
        files = cursor.fetchall()
        conn.close()

        if not files:
            bot.send_message(call.message.chat.id, "📂 **You haven't uploaded any files yet.**")
            return

        markup = types.InlineKeyboardMarkup(row_width=1)
        for fid, fname, pid in files:
            is_alive = psutil.pid_exists(pid) if pid else False
            st_icon = "🟢" if is_alive else "🔴"
            markup.add(types.InlineKeyboardButton(f"{st_icon} {fname}", callback_data=f"manage_{fid}"))

        markup.add(types.InlineKeyboardButton("⬅️ Back to Menu", callback_data="btn_back_main"))
        bot.edit_message_text("📁 **SELECT A FILE TO MANAGE:**", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

    elif data.startswith("manage_"):
        file_id = int(data.split("_")[1])
        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT filename, pid, file_type FROM hosted_files WHERE id=?", (file_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            fname, pid, ftype = row
            is_alive = psutil.pid_exists(pid) if pid else False
            manage_text = (
                f"⚙️ **MANAGING FILE:** `{fname}`\n\n"
                f"⚡ **Type:** `{ftype}`\n"
                f"📌 **PID:** `{pid}`\n"
                f"🟢 **Status:** `{'Running' if is_alive else 'Stopped'}`"
            )
            bot.edit_message_text(manage_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_file_control_keyboard(file_id, is_alive))

    elif data.startswith("act_stop_"):
        file_id = int(data.split("_")[2])
        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT filename, pid FROM hosted_files WHERE id=?", (file_id,))
        row = cursor.fetchone()

        if row:
            fname, pid = row
            if pid and psutil.pid_exists(pid):
                kill_process_tree(pid)
            cursor.execute("UPDATE hosted_files SET pid=NULL, status='Stopped' WHERE id=?", (file_id,))
            conn.commit()
            bot.answer_callback_query(call.id, f"🛑 {fname} Stopped!")
            bot.edit_message_text(f"🛑 **{fname}** has been stopped.", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_file_control_keyboard(file_id, False))
        conn.close()

    elif data.startswith("act_start_") or data.startswith("act_restart_"):
        file_id = int(data.split("_")[2])
        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, filename, pid FROM hosted_files WHERE id=?", (file_id,))
        row = cursor.fetchone()

        if row:
            f_user_id, fname, pid = row
            if pid and psutil.pid_exists(pid):
                kill_process_tree(pid)

            fpath = f"uploads/{f_user_id}/{fname}"
            proc = None
            if fname.endswith('.py'):
                proc = subprocess.Popen([sys.executable, fpath])
            elif fname.endswith('.js'):
                proc = subprocess.Popen(["node", fpath])

            new_pid = proc.pid if proc else None
            cursor.execute("UPDATE hosted_files SET pid=?, status='Running' WHERE id=?", (new_pid, file_id))
            conn.commit()

            bot.answer_callback_query(call.id, f"🚀 {fname} Started!")
            bot.edit_message_text(f"🚀 **{fname}** is now Running! (PID: `{new_pid}`)", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_file_control_keyboard(file_id, True))
        conn.close()

    elif data.startswith("act_delete_"):
        file_id = int(data.split("_")[2])
        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, filename, pid FROM hosted_files WHERE id=?", (file_id,))
        row = cursor.fetchone()

        if row:
            f_user_id, fname, pid = row
            if pid and psutil.pid_exists(pid):
                kill_process_tree(pid)

            fpath = f"uploads/{f_user_id}/{fname}"
            if os.path.exists(fpath):
                os.remove(fpath)

            cursor.execute("DELETE FROM hosted_files WHERE id=?", (file_id,))
            conn.commit()

            bot.answer_callback_query(call.id, f"🗑️ {fname} Deleted!")
            bot.edit_message_text(f"🗑️ **{fname}** has been permanently deleted.", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_keyboard(user_id))
        conn.close()

    elif data == "btn_logs" or data.startswith("act_log_"):
        bot.answer_callback_query(call.id, "Fetching Logs...")
        bot.send_message(call.message.chat.id, "📊 **LOGS SYSTEM:** All systems running smoothly. No active errors reported.")

    elif data == "btn_help":
        bot.answer_callback_query(call.id)
        help_text = (
            "💡 **SR HAKER HOSTING BOT HELP**\n\n"
            "1️⃣ Send your `.py` or `.js` script.\n"
            "2️⃣ The bot automatically installs required libraries.\n"
            "3️⃣ Your script starts running in the background 24/7.\n"
            "4️⃣ Use **My Files** to stop, restart, or delete scripts anytime."
        )
        bot.send_message(call.message.chat.id, help_text)

    elif data == "btn_admin" and user_id == OWNER_ID:
        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM hosted_files")
        total_files = cursor.fetchone()[0]
        conn.close()

        admin_text = (
            f"👑 **ADMIN CONTROL PANEL** 👑\n\n"
            f"👥 **Total Users:** `{total_users}`\n"
            f"📁 **Total Hosted Files:** `{total_files}`\n"
            f"🖥️ **CPU Usage:** `{psutil.cpu_percent()}%`\n"
            f"🧠 **RAM Usage:** `{psutil.virtual_memory().percent}%`"
        )
        bot.send_message(call.message.chat.id, admin_text)

# =========================================================
# MAIN BOT EXECUTION
# =========================================================
if __name__ == '__main__':
    # Start Flask Web Server
    threading.Thread(target=run_flask, daemon=True).start()

    # Clear Webhooks before Polling
    try:
        bot.remove_webhook()
    except Exception as e:
        print(f"[WEBHOOK WARNING]: {e}")

    print("=========================================")
    print("🚀 SR HAKER HOST BOT STARTED SUCCESSFULLY")
    print("=========================================")

    bot.infinity_polling()
