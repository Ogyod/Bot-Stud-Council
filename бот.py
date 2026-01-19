import logging
import asyncio
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ContextTypes,
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен и ID администратора (оператора)
TOKEN = "8363009372:AAGYcNJEMPdztTC8U3IXNe32h5XcUxe8VF4"
ADMIN_CHAT_ID = -5010761449

# Состояния
(
    START,
    WAITING_QUESTION,
    WAITING_COMPLAINT,
    WAITING_SUGGESTION,
    WAITING_CLARIFICATION,
    RATING
) = range(6)


# Тексты сообщений (вынесем для удобства редактирования)
START_MESSAGE = "<b>Привет, студент первого аэрокосмического 🚀</b>"
CHOOSE_ACTION_MESSAGE = "Здесь ты можешь задать вопрос, направить жалобу или предложение. Твое обращение будет передано членам Студенческой комиссии по качеству образования, которая действует в рамках Студенческого совета, для дальнейшей работы с ним.\n\n<b>Выбери тип своего обращения ⤵️</b>"
QUESTION_TEXT = "Тщательно продумай свой вопрос, должна быть ясна его суть. <b>Твой вопрос не должен касаться аспектов личной жизни и деятельности 🎓</b> \nПродолжая пользоваться ботом и его функциями и сообщая личную информацию, вы <b><u>даёте согласие на обработку персональных данных</u></b>."
COMPLAINT_TEXT = "<b>Для отправки жалобы четко ее сформулируй.</b> \n\nУчти, что жалоба должна быть аргументирована и не должна содержать ненормативной лексики, оскорблений и любой другой информации, нарушающей законодательство Российской Федерации 🚨\nПродолжая пользоваться ботом и его функциями, вы <b><u>даёте согласие на обработку персональных данных</u></b>."
SUGGESTION_TEXT = "<b>Для отправки предложения четко сформулируй свои мысли.</b> \n\nВ твоем обращении должны быть ясны суть и значение реализации предложенных действий как для тебя, так и для других студентов 👥\nПродолжая пользоваться ботом и его функциями, вы <b><u>даёте согласие на обработку персональных данных</u></b>."
ACCEPTED_MESSAGE = "<b>Твое обращение принято в работу.</b> В ближайшее время тебе будет направлено сообщение с ответом ⚙️"
RATE_QUESTION_MESSAGE = "Ответили ли мы на твой вопрос?"
CLARIFY_MESSAGE = "Качество ответа напрямую зависит от понимания сути обращения. <b>Если</b> для этого <b>требуется дополнительная информация, то поделись ей</b> с нами и мы сделаем все возможное, чтобы ответ полностью соответствовал обращению 📲"
THANK_YOU_MESSAGE = "<b>Благодарим за обращение!</b> Мы сделаем все возможное, чтобы оказать наиболее качественную поддержку ❤️"
RATE_SERVICE_MESSAGE = "Оцени работу бота по пятибальной шкале:"


# Состояния пользователей (словарь)
user_states = {}
pending_messages = {}  # Для хранения вопросов, жалоб, предложений

# --- Функции обработчики ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    user_id = update.effective_user.id
    user_states[user_id] = START  # Устанавливаем начальное состояние
    await update.message.reply_text(START_MESSAGE, parse_mode=telegram.constants.ParseMode.HTML)
    keyboard = [
        [InlineKeyboardButton("Вопрос", callback_data="question")],
        [InlineKeyboardButton("Жалоба", callback_data="complaint")],
        [InlineKeyboardButton("Предложение", callback_data="suggestion")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(CHOOSE_ACTION_MESSAGE, reply_markup=reply_markup, parse_mode=telegram.constants.ParseMode.HTML)


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == "question":
        await context.bot.send_message(chat_id=query.message.chat_id, text=QUESTION_TEXT, parse_mode=telegram.constants.ParseMode.HTML) # Отправляем новое сообщение
        user_states[user_id] = WAITING_QUESTION
    elif query.data == "complaint":
        await context.bot.send_message(chat_id=query.message.chat_id, text=COMPLAINT_TEXT, parse_mode=telegram.constants.ParseMode.HTML)
        user_states[user_id] = WAITING_COMPLAINT
    elif query.data == "suggestion":
        await context.bot.send_message(chat_id=query.message.chat_id, text=SUGGESTION_TEXT, parse_mode=telegram.constants.ParseMode.HTML)
        user_states[user_id] = WAITING_SUGGESTION
    elif query.data == "yes":
        await ask_for_rating(update, context)
    elif query.data == "no":
        await context.bot.send_message(chat_id=query.message.chat_id, text=CLARIFY_MESSAGE, parse_mode=telegram.constants.ParseMode.HTML)
        user_states[user_id] = WAITING_CLARIFICATION
    elif query.data.startswith("rating_"):
        rating = int(query.data[7:])  # Извлекаем оценку
        await process_rating(update, context, rating)
    else:
        await context.bot.send_message(chat_id=query.message.chat_id, text="Неизвестная команда.")


async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений от пользователя."""
    user_id = update.effective_user.id
    text = update.message.text
    state = user_states.get(user_id)

    if state == WAITING_QUESTION:
        await forward_to_admin(update, context, text, "Вопрос")
        user_states[user_id] = None  # Сбрасываем состояние
        pending_messages[user_id] = text
        await update.message.reply_text(ACCEPTED_MESSAGE, parse_mode=telegram.constants.ParseMode.HTML)
      #  await ask_if_answered(update, context)
    elif state == WAITING_COMPLAINT:
        await forward_to_admin(update, context, text, "Жалоба")
        user_states[user_id] = None
        pending_messages[user_id] = text
        await update.message.reply_text(ACCEPTED_MESSAGE, parse_mode=telegram.constants.ParseMode.HTML)
      #  await ask_if_answered(update, context)
    elif state == WAITING_SUGGESTION:
        await forward_to_admin(update, context, text, "Предложение")
        user_states[user_id] = None
        pending_messages[user_id] = text
        await update.message.reply_text(ACCEPTED_MESSAGE, parse_mode=telegram.constants.ParseMode.HTML)
     #   await ask_if_answered(update, context)
    elif state == WAITING_CLARIFICATION:
        await forward_to_admin(update, context, text, "Уточнение")
        pending_messages[user_id] = text
        user_states[user_id] = None
        await update.message.reply_text(ACCEPTED_MESSAGE, parse_mode=telegram.constants.ParseMode.HTML)
     #   await ask_if_answered(update, context) # снова спрашиваем ответили ли
    else:
        await update.message.reply_text("Пожалуйста, начните с команды /start.")


async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, message_type: str):
    """Отправляет сообщение администратору."""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"[{message_type}]\nОт пользователя:\n"
                 f"Имя: {user_name}\n"
                 f"ID: {user_id}\n"
                 f"Сообщение: {text}\n\n"
                 f"Ответьте командой: /reply {user_id} <ваш ответ>"
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке {message_type} администратору: {e}")
        await update.message.reply_text(f"Произошла ошибка при отправке {message_type}.")


async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /reply (только для администратора)."""
    # Проверка прав администратора
    if update.message.chat.id != ADMIN_CHAT_ID:
        await update.message.reply_text("У вас нет прав на выполнение этой команды.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Используйте: /reply <user_id> <ответ>")
        return

    try:
        user_id = int(args[0])
        answer = " ".join(args[1:])
        await context.bot.send_message(
            chat_id=user_id,
            text=f"Ответ от членов Студенческой комиссии:\n{answer}"
        )
        await update.message.reply_text(f"Ответ отправлен пользователю {user_id}")

        # Убираем сообщение из очереди, если оно там есть
        if user_id in pending_messages:
            del pending_messages[user_id]

        # Предлагаем оценить, если еще не предлагали
        if user_states.get(user_id) != RATING:
            await ask_if_answered(update, context)

    except ValueError:
        await update.message.reply_text("Некорректный ID пользователя (должно быть числом).")
    except Exception as e:
        logger.error(f"Ошибка отправки ответа пользователю: {e}")
        await update.message.reply_text(f"Ошибка при отправке ответа: {e}")

async def ask_if_answered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Спрашивает пользователя, ответили ли на его вопрос."""
    user_id = update.effective_user.id

    keyboard = [
        [InlineKeyboardButton("Да", callback_data="yes")],
        [InlineKeyboardButton("Нет", callback_data="no")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=user_id,
        text=RATE_QUESTION_MESSAGE,
        reply_markup=reply_markup, parse_mode=telegram.constants.ParseMode.HTML
    )

def build_rating_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("1️⃣", callback_data="rating_1"),
            InlineKeyboardButton("2️⃣", callback_data="rating_2"),
            InlineKeyboardButton("3️⃣", callback_data="rating_3"),
            InlineKeyboardButton("4️⃣", callback_data="rating_4"),
            InlineKeyboardButton("5️⃣", callback_data="rating_5"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def ask_for_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Предлагает пользователю оценить обслуживание."""
    user_id = update.effective_user.id
    user_states[user_id] = RATING #Устанавливаем состояние RATING

    reply_markup = build_rating_keyboard()

    await context.bot.send_message(
        chat_id=user_id,
        text=RATE_SERVICE_MESSAGE,
        reply_markup=reply_markup, parse_mode=telegram.constants.ParseMode.HTML
    )


async def process_rating(update: Update, context: ContextTypes.DEFAULT_TYPE, rating: int):
    """Обрабатывает оценку, отправляет ее администратору и благодарит пользователя."""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"Пользователь {user_name} (ID: {user_id}) оценил бота на {rating}."
        )
    except Exception as e:
            logger.error(f"Ошибка при отправке оценки оператору: {e}")

    await update.callback_query.edit_message_text(THANK_YOU_MESSAGE, parse_mode=telegram.constants.ParseMode.HTML) # Благодарим пользователя
    user_states[user_id] = START  # Сбрасываем состояние
    await start(update, context) #Возвращаемся в начало

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок."""
    logger.error(f"Update {update} вызвал ошибку {context.error}")

async def main():
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()

    # Обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))
    application.add_handler(CommandHandler("reply", reply))

    # Обработчик ошибок
    application.add_error_handler(error_handler)

    # Запуск
    print("🤖 Бот запускается...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    print("✅ Бот успешно запущен!")

    # Бесконечное ожидание
    import asyncio
    await asyncio.Event().wait()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
