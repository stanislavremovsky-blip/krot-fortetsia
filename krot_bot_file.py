import os
import logging
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from google import genai
from google.genai.errors import APIError

# Ініціалізація логування
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Отримання змінних середовища
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
# Використовуємо 10000, як рекомендовано для Web Service на Render, якщо змінна PORT встановлена
PORT = int(os.environ.get('PORT', 8080))
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', None)

# Ініціалізація Gemini API
client = None
model = None
try:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY не знайдено.")
    
    # Ініціалізація клієнта
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Створення системної інструкції
    system_instruction = (
        "Твоє головне завдання — бути Кротом у Фортеці. "
        "Спілкуйся українською мовою. "
        "Використовуй **жирний** текст для виділення важливих думок. "
        "Твоя мета — бути мудрим, обережним та лаконічним. "
        "Завжди відповідай у цьому стилі."
    )
    
    # Вибір моделі та конфігурація
    # Оскільки виникала помилка "TypeError: Models.get() takes 1 positional argument but 2 were given", 
    # використовуємо client.get_model() або безпосередньо client.models.generate_content
    # Для стабільності краще використовувати models.get() без параметрів.
    model = 'gemini-2.5-flash' # Тепер просто рядок, а не об'єкт
    
except ValueError as e:
    logger.error(f"Помилка ініціалізації API: {e}")
except APIError as e:
    logger.error(f"Помилка підключення до Gemini API: {e}")

# Обробник команди /start
async def start(update: Update, context):
    """Надсилає вітальне повідомлення при команді /start."""
    welcome_message = (
        "Вітаю, друже! Я **Кріт у Фортеці**. "
        "Питання? Поради? Тільки проси, і я відповім."
    )
    await update.message.reply_text(welcome_message)

# Обробник текстових повідомлень
async def echo(update: Update, context):
    """Обробляє вхідні повідомлення та відповідає за допомогою Gemini."""
    if not client or not model:
        await update.message.reply_text(
            "На жаль, наразі я не можу відповісти. **API ключ відсутній** або недійсний."
        )
        return

    user_text = update.message.text
    
    # Надсилання повідомлення до Gemini з системною інструкцією
    try:
        response = client.models.generate_content(
            model=model,
            contents=[user_text],
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )
        
        # Надсилання відповіді
        await update.message.reply_text(response.text)

    except Exception as e:
        logger.error(f"Помилка Gemini: {e}")
        await update.message.reply_text(
            "Вибач, друже. **Сталася помилка** під час обробки твого запиту."
        )

# Головна функція
def main():
    """Запускає бота у режимі Webhooks або Polling."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не знайдено. Запуск неможливий.")
        # Виходимо, якщо токена немає
        sys.exit(1)

    # Ініціалізація програми Telegram
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Реєстрація обробників
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # КРИТИЧНО: Налаштування Webhook
    if WEBHOOK_URL:
        logger.info(f"Starting Webhook mode on port {PORT}")
        
        # Виправлена логіка Webhook для PTB
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            # url_path: Секретна кінцева точка, зазвичай токен.
            url_path=TELEGRAM_BOT_TOKEN, 
            # webhook_url: Базова адреса Render, до якої PTB додасть url_path.
            webhook_url=WEBHOOK_URL
        )

    else:
        # Режим Polling (якщо змінна WEBHOOK_URL не встановлена)
        logger.warning("WEBHOOK_URL не встановлено. Запуск у режимі Polling...")
        application.run_polling(poll_interval=5)

if __name__ == "__main__":
    main()
