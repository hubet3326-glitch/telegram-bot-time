import os
import time
import logging
from datetime import datetime
from openpyxl import Workbook

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ====== CONFIG ======
TOKEN = os.getenv("BOT_TOKEN")

# 👉 THAY ID CỦA BẠN VÀO ĐÂY
ADMIN_ID = 8335844317

# ====== LOG ======
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

if not TOKEN:
    raise ValueError("❌ Chưa set BOT_TOKEN")

# ====== DATA ======
user_state = {}
history = {}

MENU = ReplyKeyboardMarkup(
    [
        ["🚽 Đi vệ sinh", "Đi vệ sinh 15p"],
        ["🍚 Đi ăn", "🔙 Quay lại"],
    ],
    resize_keyboard=True,
)

TIME_LIMITS = {
    "🚽 Đi vệ sinh": 10 * 60,
    "Đi vệ sinh 15p": 15 * 60,
    "🍚 Đi ăn": 30 * 60,
}

# ====== SAVE ======
def save_history(user_name, action, duration, number):
    today = datetime.now().strftime("%Y-%m-%d")

    if today not in history:
        history[today] = {}

    if user_name not in history[today]:
        history[today][user_name] = []

    history[today][user_name].append({
        "action": action,
        "duration": duration,
        "number": number
    })

# ====== START ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👉 Chọn chức năng:", reply_markup=MENU)

# ====== HANDLE ======
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_name = update.message.from_user.full_name
    text = update.message.text

    # 🚫 đang chạy
    if user_id in user_state and text != "🔙 Quay lại":
        await update.message.reply_text("⚠️ Bấm 'Quay lại' trước.")
        return

    # ===== BẮT ĐẦU =====
    if text in TIME_LIMITS:

        # 🔥 Giới hạn 2 người đi ăn
        if text == "🍚 Đi ăn":
            count = sum(1 for u in user_state.values() if u["action"] == "🍚 Đi ăn")
            if count >= 2:
                await update.message.reply_text("🚫 Đã đủ 2 người đi ăn rồi!")
                return

        user_state[user_id] = {
            "action": text,
            "start": time.time()
        }

        await update.message.reply_text(f"⏱️ Bắt đầu: {text}")

    # ===== KẾT THÚC =====
    elif text == "🔙 Quay lại":
        if user_id not in user_state:
            await update.message.reply_text("❌ Chưa có chức năng.")
            return

        data = user_state[user_id]
        elapsed = int(time.time() - data["start"])

        minutes = elapsed // 60
        seconds = elapsed % 60

        limit = TIME_LIMITS[data["action"]]

        today = datetime.now().strftime("%Y-%m-%d")
        count = 1
        if today in history and user_name in history[today]:
            count = len(history[today][user_name]) + 1

        save_history(user_name, data["action"], elapsed, count)

        # ===== CHECK GIỜ =====
        if elapsed > limit:
            await update.message.reply_text(
                f"❌ {data['action']}\n⏱️ {minutes}p {seconds}s\n🚫 Quá thời gian quy định"
            )
            await update.message.reply_text("⚠️ Bạn đã đi quá thời gian quy định")
        else:
            await update.message.reply_text(
                f"✅ {data['action']} xong\n⏱️ {minutes}p {seconds}s"
            )

        del user_state[user_id]

    else:
        await update.message.reply_text("❓ Không hợp lệ")

# ====== REPORT (ADMIN ONLY) ======
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 Bạn không có quyền dùng lệnh này")
        return

    today = datetime.now().strftime("%Y-%m-%d")

    if today not in history:
        await update.message.reply_text("📭 Chưa có dữ liệu")
        return

    wb = Workbook()
    ws = wb.active

    ws.append(["Tên", "Hành động", "Phút", "Lần", "Trạng thái"])

    for user_name, actions in history[today].items():
        for item in actions:
            duration = round(item["duration"] / 60, 2)
            limit = TIME_LIMITS[item["action"]]

            status = "Đúng giờ"
            if item["duration"] > limit:
                status = "Quá giờ"

            ws.append([
                user_name,
                item["action"],
                duration,
                item["number"],
                status
            ])

    file_name = f"report_{today}.xlsx"
    wb.save(file_name)

    with open(file_name, "rb") as f:
        await update.message.reply_document(f)

# ====== RESET ======
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 Bạn không có quyền")
        return

    global history, user_state
    history = {}
    user_state = {}

    await update.message.reply_text("🔄 Đã reset toàn bộ dữ liệu")

# ====== MAIN ======
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("✅ Bot đang chạy...")
    app.run_polling()

if __name__ == "__main__":
    main()
