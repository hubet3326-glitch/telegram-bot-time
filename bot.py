from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import time
from datetime import datetime
from openpyxl import Workbook
import os

# ====== LẤY TOKEN TỪ RAILWAY ======
import os

TOKEN = os.getenv("BOT_TOKEN")

print("DEBUG TOKEN:", TOKEN)

if not TOKEN:
    print("❌ Không đọc được BOT_TOKEN")

# ====== DATA ======
user_state = {}
history = {}

MENU = ReplyKeyboardMarkup(
    [["🚽 Đi vệ sinh", "Đi vệ sinh 15p"],
     ["🍚 Đi ăn", "🔙 Quay lại"],
     ["/report"]],
    resize_keyboard=True
)

TIME_LIMITS = {
    "🚽 Đi vệ sinh": 10 * 60,
    "Đi vệ sinh 15p": 15 * 60,
    "🍚 Đi ăn": 30 * 60
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

    # Đang làm mà bấm linh tinh
    if user_id in user_state and text != "🔙 Quay lại":
        await update.message.reply_text(
            "⚠️ Bạn đang thực hiện chức năng.\n👉 Bấm 'Quay lại' để kết thúc."
        )
        return

    # Bắt đầu
    if text in TIME_LIMITS:
        user_state[user_id] = {
            "action": text,
            "start": time.time()
        }
        await update.message.reply_text(f"⏱️ Bắt đầu: {text}")

    # Kết thúc
    elif text == "🔙 Quay lại":
        if user_id not in user_state:
            await update.message.reply_text("❌ Bạn chưa bắt đầu.")
            return

        data = user_state[user_id]
        elapsed = int(time.time() - data["start"])

        minutes = elapsed // 60
        seconds = elapsed % 60
        limit = TIME_LIMITS[data["action"]]

        # Tính lần
        today = datetime.now().strftime("%Y-%m-%d")
        count = 1
        if today in history and user_name in history[today]:
            count = len(history[today][user_name]) + 1

        save_history(user_name, data["action"], elapsed, count)

        # Quá giờ
        if elapsed > limit:
            overtime_min = (elapsed - limit) // 60

            await update.message.reply_text(
                f"❌ {data['action']}\n⏱️ {minutes}p {seconds}s\n🚫 Quá thời gian!"
            )

            # Gửi riêng
            try:
                if 1 <= overtime_min < 10:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="💸 Chúc mừng bạn đã tốn 100k"
                    )
                elif overtime_min > 10:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="💸 Chúc mừng bạn đã tốn 500k"
                    )
            except:
                pass

        else:
            await update.message.reply_text(
                f"✅ {data['action']} xong\n⏱️ {minutes}p {seconds}s"
            )

        del user_state[user_id]

    else:
        await update.message.reply_text("❓ Lệnh không hợp lệ")

# ====== REPORT ======
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now().strftime("%Y-%m-%d")

    if today not in history:
        await update.message.reply_text("📭 Chưa có dữ liệu.")
        return

    wb = Workbook()
    ws = wb.active
    ws.title = "Báo cáo"

    ws.append(["Tên", "Hành động", "Phút", "Lần", "Trạng thái", "Vượt (phút)"])

    for user_name, actions in history[today].items():
        for item in actions:
            action = item["action"]
            duration = item["duration"]
            duration_min = round(duration / 60, 2)

            limit = TIME_LIMITS[action]

            if duration > limit:
                overtime = round((duration - limit) / 60, 2)
                status = "Quá ❌"
            else:
                overtime = 0
                status = "Đúng ✅"

            ws.append([
                user_name,
                action,
                duration_min,
                item["number"],
                status,
                overtime
            ])

    file_name = f"baocao_{today}.xlsx"
    wb.save(file_name)

    await update.message.reply_document(open(file_name, "rb"))

# ====== MAIN ======
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("🚀 Bot đang chạy...")
    app.run_polling()
