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

# ====== LOG ======
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ====== TOKEN ======
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ Chưa set BOT_TOKEN trong Railway")

# ====== DATA ======
user_state = {}
history = {}

MENU = ReplyKeyboardMarkup(
    [
        ["🚽 Đi vệ sinh", "Đi vệ sinh 15p"],
        ["🍚 Đi ăn", "🔙 Quay lại"],
        ["/report"],
    ],
    resize_keyboard=True,
)

TIME_LIMITS = {
    "🚽 Đi vệ sinh": 10 * 60,
    "Đi vệ sinh 15p": 15 * 60,
    "🍚 Đi ăn": 30 * 60,
}

# ====== FUNCTIONS ======
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

# ====== COMMANDS ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👉 Chọn chức năng:",
        reply_markup=MENU
    )

# ====== HANDLE ======
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        user_name = update.message.from_user.full_name
        text = update.message.text

        # Đang chạy mà bấm cái khác
        if user_id in user_state and text != "🔙 Quay lại":
            await update.message.reply_text(
                "⚠️ Bạn đang thực hiện chức năng.\n👉 Bấm 'Quay lại' trước."
            )
            return

        # ===== BẮT ĐẦU =====
        if text in TIME_LIMITS:
            user_state[user_id] = {
                "action": text,
                "start": time.time()
            }
            await update.message.reply_text(f"⏱️ Bắt đầu: {text}")

        # ===== KẾT THÚC =====
        elif text == "🔙 Quay lại":
            if user_id not in user_state:
                await update.message.reply_text("❌ Chưa có chức năng nào.")
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
                overtime = (elapsed - limit) // 60

                await update.message.reply_text(
                    f"❌ {data['action']}\n⏱️ {minutes}p {seconds}s\n🚫 Quá giờ"
                )

                if 1 <= overtime < 10:
                    await update.message.reply_text("💸 Mất 100k")
                elif overtime >= 10:
                    await update.message.reply_text("💸 Mất 500k")

            else:
                await update.message.reply_text(
                    f"✅ {data['action']} xong\n⏱️ {minutes}p {seconds}s"
                )

            del user_state[user_id]

        else:
            await update.message.reply_text("❓ Không hợp lệ")

    except Exception as e:
        logging.error(f"Lỗi handle: {e}")
        await update.message.reply_text("❌ Có lỗi xảy ra")

# ====== REPORT ======
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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

        # QUAN TRỌNG: mở file đúng cách
        with open(file_name, "rb") as f:
            await update.message.reply_document(f)

    except Exception as e:
        logging.error(f"Lỗi report: {e}")
        await update.message.reply_text("❌ Lỗi xuất file")

# ====== MAIN ======
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("✅ Bot đang chạy...")
    app.run_polling()

if __name__ == "__main__":
    main()
