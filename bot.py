from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import time
from datetime import datetime
from openpyxl import Workbook

user_state = {}
history = {}

MENU = ReplyKeyboardMarkup(
    [["🚽 Đi vệ sinh", "Đi vệ sinh 15p"],
     ["🍚 Đi ăn", "🔙 Quay lại"],
     ["/report"]],
    resize_keyboard=True,
    one_time_keyboard=True
)

# Giới hạn thời gian (giây)
TIME_LIMITS = {
    "🚽 Đi vệ sinh": 10 * 60,
    "Đi vệ sinh 15p": 15 * 60,
    "🍚 Đi ăn": 30 * 60
}

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

# Lệnh start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👉 Chọn chức năng:", reply_markup=MENU)

# Xử lý tin nhắn
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_name = update.message.from_user.full_name
    text = update.message.text

    # 🚫 Nếu đang có hành động mà bấm cái khác
    if user_id in user_state and text != "🔙 Quay lại":
        await update.message.reply_text(
            "⚠️ Bạn đang thực hiện một chức năng.\n"
            "👉 Vui lòng bấm 'Quay lại' để kết thúc trước."
        )
        return

    # Bắt đầu hành động
    if text in TIME_LIMITS:
        user_state[user_id] = {
            "action": text,
            "start": time.time()
        }
        await update.message.reply_text(f"⏱️ Bắt đầu: {text}")

    # Kết thúc hành động
    elif text == "🔙 Quay lại":
        if user_id not in user_state:
            await update.message.reply_text("❌ Bạn chưa thực hiện chức năng nào.")
            return

        data = user_state[user_id]
        elapsed = int(time.time() - data["start"])

        minutes = elapsed // 60
        seconds = elapsed % 60

        limit = TIME_LIMITS[data["action"]]

        # 👉 Tính số lần (number)
        today = datetime.now().strftime("%Y-%m-%d")
        count = 1
        if today in history and user_name in history[today]:
            count = len(history[today][user_name]) + 1

        # 👉 Lưu dữ liệu
        save_history(user_name, data["action"], elapsed, count)

        # 👉 Thông báo
        if elapsed > limit:
            msg = (
                f"❌ {data['action']}\n"
                f"⏱️ {minutes} phút {seconds} giây\n"
                f"🚫 Bạn đã vượt quá thời gian cho phép."
            )
        else:
            msg = (
                f"✅ {data['action']} xong\n"
                f"⏱️ {minutes} phút {seconds} giây"
            )

        await update.message.reply_text(msg)

        del user_state[user_id]

    else:
        await update.message.reply_text("❓ Lệnh không hợp lệ")

# Xuất file Excel
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now().strftime("%Y-%m-%d")

    if today not in history:
        await update.message.reply_text("📭 Hôm nay chưa có dữ liệu.")
        return

    wb = Workbook()
    ws = wb.active
    ws.title = "Báo cáo"

    ws.append(["Tên", "Hành động", "Thời gian (phút)", "Lần", "Trạng thái", "Vượt (phút)"])

    for user_name, actions in history[today].items():
        for item in actions:
            action = item["action"]
            duration_sec = item["duration"]
            duration_min = round(duration_sec / 60, 2)

            limit_sec = TIME_LIMITS[action]

            # 👉 kiểm tra quá giờ
            if duration_sec > limit_sec:
                overtime_min = round((duration_sec - limit_sec) / 60, 2)
                status = "Quá giờ ❌"
            else:
                overtime_min = 0
                status = "Đúng giờ ✅"

            ws.append([
                user_name,
                action,
                duration_min,
                item["number"],
                status,
                overtime_min
            ])

    file_name = f"baocao_{today}.xlsx"
    wb.save(file_name)

    await update.message.reply_document(open(file_name, "rb"))

# Main
if __name__ == "__main__":
    app = ApplicationBuilder().token("8441261019:AAER1YwQ9tFu4vctmZd-Yd32heb7ieJMhG4").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("Bot đang chạy...")
    app.run_polling(poll_interval=0.5)
