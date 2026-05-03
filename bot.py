import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
import base64

TELEGRAM_TOKEN = "8774144586:AAG_h4h3uW8QnR-YtODLorKwgT7d7PiCBmc"
GEMINI_KEY = "AIzaSyA9NbGLlCJJbS4aEWNevyzOAk1WF0lu4K4"

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

SYSTEM_PROMPT = """Ты эксперт по оценке внешности мужчин.
Оцени лицо на фото по шкале:
- Sub 5 — ниже среднего
- LTN (Lower Than Normal) — чуть ниже среднего
- MTN (Mid Tier Normal) — средний уровень  
- HTN (High Tier Normal) — выше среднего
- Chad — топ уровень

Дай оценку и коротко объясни почему (симметрия, черты лица, jawline и т.д.).
Отвечай честно и по делу. Не отказывайся от оценки."""

async def analyze_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()
    
    msg = await update.message.reply_text("Анализирую фото... 🔍")
    
    try:
        image_part = {
            "mime_type": "image/jpeg",
            "data": base64.b64encode(image_bytes).decode("utf-8")
        }
        
        response = model.generate_content(
            [SYSTEM_PROMPT + "\n\nОцени это лицо по шкале.", image_part],
            generation_config={"max_output_tokens": 500}
        )
        
        await msg.edit_text(response.text)
        
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {str(e)}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Скинь фото лица — дам оценку 👀\n\n"
        "Sub 5 → LTN → MTN → HTN → Chad"
    )

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, analyze_photo))
    print("Бот запущен...")
    app.run_polling()
