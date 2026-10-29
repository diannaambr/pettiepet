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

ai_client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# Галерея скинов (картинки разных окрасов Рудика)
SKINS = {
    "blue": {
        "name": "🩵 Космический синий",
        "url": "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?w=800&auto=format&fit=crop"
    },
    "pink": {
        "name": "🌸 Неоново-розовый",
        "url": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=800&auto=format&fit=crop"
    },
    "purple": {
        "name": "💜 Галактический фиолетовый",
        "url": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800&auto=format&fit=crop"
    },
    "gold": {
        "name": "🟡 Золотой звёздный",
        "url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&auto=format&fit=crop"
    }
}

# Состояние питомца
pet = {
    "name": "Рудик",
    "satiety": 70,
    "happiness": 70,
    "energy": 70,
    "color": "blue",  # Базовый цвет
    "chat_id": None
}

def generate_ai_event(mood_context: str) -> str:
    if not ai_client:
        fallback_events = [
            f"🐾 {pet['name']} тихо шуршит пакетом в углу...",
            f"📦 {pet['name']} пытался залезть в коробку, но промазал.",
            f"🧶 {pet['name']} катает по комнате виртуальный клубок."
        ]
        return random.choice(fallback_events)

    prompt = (
        f"Ты — виртуальный домашний питомец по имени {pet['name']}. "
        f"Твой текущий цвет шерстки: {SKINS[pet['color']]['name']}. "
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

    current_skin = SKINS[pet['color']]['name']

    return (
        f"🐾 **Питомец:** {pet['name']}\n"
        f"🎨 **Шерстка:** {current_skin}\n\n"
        f"🍖 **Сытость:** {make_bar(pet['satiety'])} ({pet['satiety']}%)\n"
        f"💛 **Счастье:** {make_bar(pet['happiness'])} ({pet['happiness']}%)\n"
        f"⚡ **Энергия:** {make_bar(pet['energy'])} ({pet['energy']}%)\n"
    )

def get_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🍎 Покормить", callback_data="feed")
    builder.button(text="⚽ Поиграть", callback_data="play")
    builder.button(text="😴 Спать", callback_data="sleep")
    builder.button(text="🎨 Сменить цвет", callback_data="open_color_menu")
    builder.adjust(3, 1)
    return builder.as_markup()

def get_color_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🩵 Синий", callback_data="set_color_blue")
    builder.button(text="🌸 Розовый", callback_data="set_color_pink")
    builder.button(text="💜 Фиолетовый", callback_data="set_color_purple")
    builder.button(text="🟡 Золотой", callback_data="set_color_gold")
    builder.button(text="⬅️ Назад", callback_data="back_to_status")
    builder.adjust(2, 2, 1)
    return builder.as_markup()

# --- АВТО-ПРИВЕТСТВИЕ ---

@dp.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def bot_added_to_chat(event: types.ChatMemberUpdated):
    pet["chat_id"] = event.chat.id
    
    welcome_text = (
        f"Всем привет! 🐾 Я ваш новый инопланетный питомец **{pet['name']}**!\n\n"
        f"Вот что со мной можно делать:\n"
        f"• `/pet` — посмотреть моё состояние и фото 📸\n"
        f"• `/color` — изменить цвет моей шерстки 🎨\n"
        f"• `/gift` — попросить у меня случайный подарок 🎁\n"
        f"• `/rename [имя]` — дать мне новое имя ✨\n\n"
    ) + get_status_text()

    await bot.send_photo(
        chat_id=event.chat.id,
        photo=SKINS[pet['color']]['url'],
        caption=welcome_text,
        parse_mode="Markdown",
        reply_markup=get_keyboard()
    )

# --- КОМАНДЫ ---

@dp.message(Command("start", "pet"))
async def cmd_pet(message: types.Message):
    pet["chat_id"] = message.chat.id
    await message.answer_photo(
        photo=SKINS[pet['color']]['url'],
        caption=get_status_text(),
        parse_mode="Markdown",
        reply_markup=get_keyboard()
    )

@dp.message(Command("color"))
async def cmd_color(message: types.Message):
    await message.answer("Выберите новый цвет шерстки для Рудика: 🎨", reply_markup=get_color_keyboard())

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
            f"Придумай забавный виртуальный подарок, который "
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

# --- ОБРАБОТКА КНОПОК МЕНЮ ---

@dp.callback_query(F.data == "open_color_menu")
async def process_color_menu(callback: types.CallbackQuery):
    await callback.message.edit_caption(
        caption="Выберите новый цвет шерстки для Рудика: 🎨",
        reply_markup=get_color_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("set_color_"))
async def process_set_color(callback: types.CallbackQuery):
    new_color = callback.data.replace("set_color_", "")
    if new_color in SKINS:
        pet["color"] = new_color
        await callback.answer(f"Цвет изменён на {SKINS[new_color]['name']}! ✨")
        
        # Обновляем сообщение и меняем фото
        media = types.InputMediaPhoto(
            media=SKINS[pet['color']]['url'],
            caption=f"🎨 Рудик сменил цвет шерстки!\n\n{get_status_text()}",
            parse_mode="Markdown"
        )
        await callback.message.edit_media(media=media, reply_markup=get_keyboard())

@dp.callback_query(F.data == "back_to_status")
async def process_back_to_status(callback: types.CallbackQuery):
    media = types.InputMediaPhoto(
        media=SKINS[pet['color']]['url'],
        caption=get_status_text(),
        parse_mode="Markdown"
    )
    await callback.message.edit_media(media=media, reply_markup=get_keyboard())

@dp.callback_query(F.data == "feed")
async def process_feed(callback: types.CallbackQuery):
    if pet["satiety"] >= 100:
        await callback.answer("Я уже сыт! 🥐", show_alert=True)
        return
    
    pet["satiety"] = min(100, pet["satiety"] + 25)
    await callback.message.edit_caption(
        caption=f"🍎 Вы покормили {pet['name']}!\n\n{get_status_text()}",
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
    
    await callback.message.edit_caption(
        caption=f"⚽ Отлично поиграли!\n\n{get_status_text()}",
        parse_mode="Markdown",
        reply_markup=get_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "sleep")
async def process_sleep(callback: types.CallbackQuery):
    pet["energy"] = min(100, pet["energy"] + 40)
    await callback.message.edit_caption(
        caption=f"😴 {pet['name']} вздремнул и восстановил силы!\n\n{get_status_text()}",
        parse_mode="Markdown",
        reply_markup=get_keyboard()
    )
    await callback.answer()

# --- ФОНОВЫЙ ЦИКЛ ---

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
