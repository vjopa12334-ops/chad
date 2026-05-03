import anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import base64
import httpx

TELEGRAM_TOKEN = "8774144586:AAG_h4h3uW8QnR-YtODLorKwgT7d7PiCBmc"
ANTHROPIC_KEY = "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"

SYSTEM_PROMPT = """Ты эксперт по оценке внешности. 
Оцени лицо на фото по шкале:
- Sub 5 — ниже среднего
- LTN (Lower Than Normal) — чуть ниже среднего  
- MTN (Mid Tier Normal) — средний уровень
- HTN (High Tier Normal) — выше среднего
- Chad — топ уровень

Дай оценку и коротко объясни почему (черты лица, симметрия, jawline и т.д.).
Отвечай честно и по делу."""

async def analyze_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]  # берём фото лучшего качества
    file = await context.bot.get_file(photo.file_id)
    
    # Скачиваем фото
    image_bytes = await file.download_as_bytearray()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    
    await update.message.reply_text("Анализирую фото... 🔍")
    
    # Отправляем в Claude
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Оцени это лицо по шкале."
                    }
                ],
            }
        ],
    )
    
    result = response.content[0].text
    await update.message.reply_text(result)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Скинь фото лица — дам оценку по шкале:\n"
        "Sub 5 → LTN → MTN → HTN → Chad 💪"
    )

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, analyze_photo))
    from telegram.ext import CommandHandler
    app.add_handler(CommandHandler("start", start))
    print("Бот запущен...")
    app.run_polling()
