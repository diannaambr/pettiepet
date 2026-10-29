import asyncio
import logging
import os
import random
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.utils.keyboard import InlineKeyboardBuilder
from google import genai

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

if not TOKEN:
    raise ValueError("Ошибка: Переменная окружения BOT_TOKEN не задана!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Инициализация ИИ-клиента Gemini (если задан ключ)
ai_client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# Состояние питомца
pet = {
    "name": "Рудик",
    "satiety": 70,   # Сытость (0-100)
    "happiness": 70, # Счастье (0-100)
    "energy": 70,    # Энергия (0-100)
    "chat_id": None  # ID чата запоминается при /start, /pet или входе в группу
}

def generate_ai_event(mood_context: str) -> str:
    """Генерация автономной выходки питомца через Gemini"""
    if not ai_client:
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

def get_status_text() -> str:
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

# --- АВТОМАТИЧЕСКОЕ ПРИВЕТСТВИЕ ПРИ ДОБАВЛЕНИИ В ЧАТ ---

@dp.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def bot_added_to_chat(event: types.ChatMemberUpdated):
    pet["chat_id"] = event.chat.id
    
    welcome_text = (
        f"Всем привет! 🐾 Я ваш новый инопланетный питомец **{pet['name']}**!\n\n"
        f"Теперь я буду жить в этом чате, играть с вами и иногда устраивать маленькие внезапные выходки 📦\n\n"
        f"Вот что со мной можно делать:\n"
        f"• `/pet` — проверить моё состояние и поухаживать за мной\n"
        f"• `/gift` — попросить меня принести вам случайный подарок 🎁\n"
        f"• `/rename [имя]` — дать мне новое имя ✨\n\n"
        f"Не забывайте меня кормить и укладывать спать! Начнём?\n\n"
    ) + get_status_text()

    await bot.send_message(
        chat_id=event.chat.id,
        text=welcome_text,
        parse_mode="Markdown",
        reply_markup=get_keyboard()
    )

# --- КОМANDЫ БОТА ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    pet["chat_id"] = message.chat.id
    
    welcome_text = (
        f"Привет всем! 🐾 Я ваш новый инопланетный питомец **{pet['name']}**!\n\n"
        f"Я буду жить в этом чате, играть с вами и иногда устраивать маленькие внезапные выходки 📦\n\n"
        f"Вот что со мной можно делать:\n"
        f"• `/pet` — проверить моё состояние и поухаживать за мной\n"
        f"• `/gift` — попросить меня принести вам случайный подарок 🎁\n"
        f"• `/rename [имя]` — дать мне новое имя ✨\n\n"
        f"Не забывайте меня кормить и укладывать спать! Начнём?\n\n"
    ) + get_status_text()

    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_keyboard())

@dp.message(Command("pet"))
async def cmd_pet(message: types.Message):
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

# --- ОБРАБОТКА КНОПОК ---

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

# --- ФОНОВЫЙ ЦИКЛ (АВТОНОМНАЯ ЖИЗНЬ) ---

async def autonomous_life_loop():
    while True:
        await asyncio.sleep(1800)
        
        pet["satiety"] = max(0, pet["satiety"] - 5)
        pet["happiness"] = max(0, pet["happiness"] - 3)
        pet["energy"] = max(0, pet["energy"] - 2)

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
