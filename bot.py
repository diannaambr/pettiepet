import asyncio
import logging
import os
import random
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from google import genai

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

if not TOKEN:
    raise ValueError("Ошибка: Переменная окружения BOT_TOKEN не задана!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Инициализация клиента Gemini (если ключ задан)
ai_client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# Состояние питомца и ID чата для авто-сообщений
pet = {
    "name": "Рудик",
    "satiety": 70,
    "happiness": 70,
    "energy": 70,
    "chat_id": None  # Запоминается автоматически при вызове /pet в группе
}

def generate_ai_event(mood_context: str) -> str:
    """Генерация уникальной выходки питомца через Gemini"""
    if not ai_client:
        # Резервные фразы, если ключ GEMINI_API_KEY не установлен
        fallback_events = [
            f"🐾 {pet['name']} тихо шуршит пакетом в углу...",
            f"📦 {pet['name']} пытался залезть в коробку, но промазал.",
            f"🧶 {pet['name']} катает по комнате виртуальный клубок."
        ]
        return random.choice(fallback_events)

    prompt = (
        f"Ты — виртуальный домашний питомец по имени {pet['name']}. "
        f"Твоё состояние сейчас: {mood_context}. "
        f"Придумай одну очень короткую, смешную и забавную выходку или фразу (1-2 предложения), "
        f"которую ты прямо сейчас делаешь в групповом чате. Добавь подходящие эмодзи."
    )

    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        logging.error(f"Ошибка Gemini: {e}")
        return f"🐾 {pet['name']} задумчиво смотрит в окно..."

def get_status_text():
    def make_bar(value):
        filled = round(value / 20)
        return "🟩" * filled + "⬜" * (5 - filled)

    return (
        f"🐾 **Питомец:** {pet['name']}\n\n"
        f"🍖 **Сытость:** {make_bar(pet['satiety'])} ({pet['satiety']}%)\n"
        f"💛 **Счастье:** {make_bar(pet['happiness'])} ({pet['happiness']}%)\n"
        f"⚡ **Энергия:** {make_bar(pet['energy'])} ({pet['energy']}%)\n"
    )

def get_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🍎 Покормить", callback_data="feed")
    builder.button(text="⚽ Поиграть", callback_data="play")
    builder.button(text="😴 Спать", callback_data="sleep")
    builder.adjust(3)
    return builder.as_markup()

@dp.message(Command("start", "pet"))
async def cmd_pet(message: types.Message):
    # Запоминаем ID чата, чтобы бот мог сам писать сюда автономные сообщения
    pet["chat_id"] = message.chat.id
    await message.answer(get_status_text(), parse_mode="Markdown", reply_markup=get_keyboard())

@dp.message(Command("rename"))
async def cmd_rename(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        pet["name"] = args[1].strip()
        await message.answer(f"✨ Питомца теперь зовут **{pet['name']}**!")
    else:
        await message.answer("Укажите новое имя, например: `/rename Барсик`", parse_mode="Markdown")

@dp.message(Command("gift"))
async def cmd_gift(message: types.Message):
    user_name = message.from_user.first_name
    if ai_client:
        prompt = (
            f"Придумай забавный, абсурдный или милый виртуальный подарок, который "
            f"питомец {pet['name']} принёс в зубах/лапах для пользователя {user_name}. "
            f"Одно короткое предложение с эмодзи."
        )
        try:
            res = ai_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            gift_text = res.text.strip()
        except Exception:
            gift_text = f"🎁 {pet['name']} принёс для {user_name} блестящий камушек!"
    else:
        gift_text = f"🎁 {pet['name']} принёс для {user_name} красивую сосновую шишку!"

    await message.answer(gift_text)

@dp.callback_query(F.data == "feed")
async def process_feed(callback: types.CallbackQuery):
    if pet["satiety"] >= 100:
        await callback.answer("Я уже сыт! 🥐", show_alert=True)
        return
    
    pet["satiety"] = min(100, pet["satiety"] + 25)
    await callback.message.edit_text(
        f"🍎 Вы покормили {pet['name']}!\n\n{get_status_text()}",
        parse_mode="Markdown",
        reply_markup=get_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "play")
async def process_play(callback: types.CallbackQuery):
    if pet["energy"] < 15:
        await callback.answer("Я слишком устал для игр! 😴", show_alert=True)
        return
    
    pet["happiness"] = min(100, pet["happiness"] + 20)
    pet["energy"] = max(0, pet["energy"] - 15)
    pet["satiety"] = max(0, pet["satiety"] - 10)
    
    await callback.message.edit_text(
        f"⚽ Отлично поиграли!\n\n{get_status_text()}",
        parse_mode="Markdown",
        reply_markup=get_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "sleep")
async def process_sleep(callback: types.CallbackQuery):
    pet["energy"] = min(100, pet["energy"] + 40)
    await callback.message.edit_text(
        f"😴 {pet['name']} вздремнул и восстановил силы!\n\n{get_status_text()}",
        parse_mode="Markdown",
        reply_markup=get_keyboard()
    )
    await callback.answer()

# Фоновый цикл: естественные потребности и генерация автономных выходок
async def autonomous_life_loop():
    while True:
        # Каждые 30 минут потребности постепенно снижаются
        await asyncio.sleep(1800)
        
        pet["satiety"] = max(0, pet["satiety"] - 5)
        pet["happiness"] = max(0, pet["happiness"] - 3)
        pet["energy"] = max(0, pet["energy"] - 2)

        # Если бот знает чат, с вероятностью 40% он совершает автономную выходку
        if pet["chat_id"] and random.random() < 0.4:
            mood = "голодный" if pet["satiety"] < 40 else "весёлый и игривый"
            event_msg = generate_ai_event(mood)
            try:
                await bot.send_message(pet["chat_id"], event_msg)
            except Exception as e:
                logging.error(f"Не удалось отправить авто-сообщение: {e}")

async def main():
    asyncio.create_task(autonomous_life_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
