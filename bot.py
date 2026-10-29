import asyncio
import json
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

# Настройка клиента Gemini через официальную библиотеку
ai_client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

DATA_FILE = "pets_data.json"

# Галерея скинов Петти
SKINS = {
    "blue": {
        "name": "🩵 Космический синий",
        "url": "https://i.postimg.cc/pLN5yRyY/Gemini-Generated-Image-vn3lbvvn3lbvvn3l.jpg"
    },
    "pink": {
        "name": "🌸 Неоново-розовый",
        "url": "https://i.postimg.cc/J049WGfJ/Gemini-Generated-Image-any1ifany1ifany1.jpg"
    },
    "purple": {
        "name": "💜 Галактический фиолетовый",
        "url": "https://i.postimg.cc/mgNJh3T9/Gemini-Generated-Image-ho8yrqho8yrqho8y.jpg"
    },
    "gold": {
        "name": "🟡 Золотой звёздный",
        "url": "https://i.postimg.cc/Xqb9Z5VT/Gemini-Generated-Image-uka2owuka2owuka2.jpg"
    },
    "black": {
        "name": "🖤 Пепельно-чёрный",
        "url": "https://i.postimg.cc/Yq2mJMj3/Gemini-Generated-Image-v8t2esv8t2esv8t2.jpg"
    },
    "red_gold": {
        "name": "❤️ Красно-золотой",
        "url": "https://i.postimg.cc/X7XYfJr6/Gemini-Generated-Image-abd5yoabd5yoabd5.jpg"
    }
}

# --- АВТОСОХРАНЕНИЕ ---

def load_all_pets():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Ошибка чтения файла: {e}")
    return {}

def save_all_pets(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка сохранения файла: {e}")

pets_db = load_all_pets()

def get_pet(chat_id: int):
    str_id = str(chat_id)
    if str_id not in pets_db:
        pets_db[str_id] = {
            "name": "Петти",
            "satiety": 70,
            "happiness": 70,
            "energy": 70,
            "color": "blue"
        }
        save_all_pets(pets_db)
    return pets_db[str_id]

# --- ИИ ГЕНЕРАЦИЯ ---

def generate_ai_event(pet_data: dict, mood_context: str) -> str:
    fallback_events = [
        f"🐾 {pet_data['name']} тихо шуршит пакетом в углу...",
        f"📦 {pet_data['name']} пытался залезть в коробку, но промазал.",
        f"🧶 {pet_data['name']} катает по комнате виртуальный клубок."
    ]
    if not ai_client:
        return random.choice(fallback_events)

    color_info = SKINS.get(pet_data["color"], SKINS["blue"])["name"]
    prompt = (
        f"Ты — виртуальный домашний инопланетный питомец по имени {pet_data['name']}. "
        f"Твой цвет шерстки: {color_info}. Состояние: {mood_context}. "
        f"Придумай одну очень короткую, смешную и забавную выходку или фразу (1-2 предложения) "
        f"для чата с друзьями. Добавь эмодзи."
    )

    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        logging.error(f"Ошибка Gemini Event: {e}")
        return random.choice(fallback_events)

def get_status_text(pet_data: dict) -> str:
    def make_bar(value):
        filled = round(value / 20)
        return "🟩" * filled + "⬜" * (5 - filled)

    current_skin = SKINS.get(pet_data["color"], SKINS["blue"])["name"]

    return (
        f"🐾 **Питомец:** {pet_data['name']}\n"
        f"🎨 **Шерстка:** {current_skin}\n\n"
        f"🍖 **Сытость:** {make_bar(pet_data['satiety'])} ({pet_data['satiety']}%)\n"
        f"💛 **Счастье:** {make_bar(pet_data['happiness'])} ({pet_data['happiness']}%)\n"
        f"⚡ **Энергия:** {make_bar(pet_data['energy'])} ({pet_data['energy']}%)\n"
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
    builder.button(text="🖤 Чёрный", callback_data="set_color_black")
    builder.button(text="❤️ Красно-золотой", callback_data="set_color_red_gold")
    builder.button(text="⬅️ Назад", callback_data="back_to_status")
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()

# --- АВТО-ПРИВЕТСТВИЕ ---

@dp.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def bot_added_to_chat(event: types.ChatMemberUpdated):
    pet_data = get_pet(event.chat.id)
    skin_url = SKINS.get(pet_data["color"], SKINS["blue"])["url"]
    
    welcome_text = (
        f"Всем привет! 🐾 Я ваш новый инопланетный питомец **{pet_data['name']}**!\n\n"
        f"Вот что со мной можно делать:\n"
        f"• `/pet` — посмотреть моё состояние 📸\n"
        f"• `/color` — изменить цвет моей шерстки 🎨\n"
        f"• `/gift` — попросить у меня случайный подарок 🎁\n"
        f"• `/rename [имя]` — дать мне новое имя ✨\n\n"
    ) + get_status_text(pet_data)

    try:
        await bot.send_photo(
            chat_id=event.chat.id,
            photo=skin_url,
            caption=welcome_text,
            parse_mode="Markdown",
            reply_markup=get_keyboard()
        )
    except Exception:
        await bot.send_message(
            chat_id=event.chat.id,
            text=welcome_text,
            parse_mode="Markdown",
            reply_markup=get_keyboard()
        )

# --- КОМАНДЫ ---

@dp.message(Command("start", "pet"))
async def cmd_pet(message: types.Message):
    pet_data = get_pet(message.chat.id)
    skin_url = SKINS.get(pet_data["color"], SKINS["blue"])["url"]
    
    try:
        await message.answer_photo(
            photo=skin_url,
            caption=get_status_text(pet_data),
            parse_mode="Markdown",
            reply_markup=get_keyboard()
        )
    except Exception:
        await message.answer(
            text=get_status_text(pet_data),
            parse_mode="Markdown",
            reply_markup=get_keyboard()
        )

@dp.message(Command("color"))
async def cmd_color(message: types.Message):
    pet_data = get_pet(message.chat.id)
    await message.answer(
        f"Выберите новый цвет шерстки для {pet_data['name']}: 🎨",
        reply_markup=get_color_keyboard()
    )

@dp.message(Command("rename"))
async def cmd_rename(message: types.Message):
    pet_data = get_pet(message.chat.id)
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        pet_data["name"] = args[1].strip()
        save_all_pets(pets_db)
        await message.answer(f"✨ Питомца теперь зовут **{pet_data['name']}**!")
    else:
        await message.answer("Укажите новое имя, например: `/rename Петти`", parse_mode="Markdown")

@dp.message(Command("gift"))
async def cmd_gift(message: types.Message):
    pet_data = get_pet(message.chat.id)
    user_name = message.from_user.first_name
    
    fallback_gifts = [
        f"🎁 {pet_data['name']} принёс для {user_name} блестящий космический камушек!",
        f"🎁 {pet_data['name']} притащил в зубах свежий кекс с другого конца галактики!",
        f"🎁 {pet_data['name']} подарил {user_name} маленькую звёздочку в баночке!"
    ]

    if ai_client:
