import asyncio
import json
import logging
import os
import random
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("Ошибка: Переменная окружения BOT_TOKEN не задана!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

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

# --- НАБОРЫ ДЕЙСТВИЙ И ПОДАРКОВ ---

GIFTS = [
    "🎁 {pet} принёс для {user} блестящий космический камушек!",
    "🎁 {pet} притащил в зубах свежий кекс с другого конца галактики!",
    "🎁 {pet} подарил {user} маленькую звёздочку в прозрачной баночке!",
    "🎁 {pet} выкатил из под дивана забавную пищащую игрушку для {user}!",
    "🎁 {pet} протягивает {user} пушистый космический одуванчик 🌸",
    "🎁 {pet} достал из тайника редкий разноцветный кристалльчик для {user}!",
    "🎁 {pet} гордо принёс {user} миниатюрную тарелочку с космическим печеньем!",
    "🎁 {pet} нашел и притащил {user} мягкие домашние тапочки!",
    "🎁 {pet} протягивает {user} волшебную палочку, которая светится в темноте ✨",
    "🎁 {pet} делится с {user} своим любимым виртуальным пледиком!",
    "🎁 {pet} принёс для {user} баночку с мерцающим космическим вареньем 🍓",
    "🎁 {pet} достал откуда-то крошечный бумажный самолётик с предсказанием!"
]

AUTONOMOUS_EVENTS_HAPPY = [
    "🐾 {pet} весело катается по ковру и пытается поймать свой хвост!",
    "🧶 {pet} гоняет по всему чату виртуальный клубочек шерсти.",
    "📦 {pet} с разбега запрыгнул в картонную коробку и гордо сидит там.",
    "✨ {pet} забавно чихнул и случайно выпустил пучок искорок!",
    "🎶 {pet} мурчит и напевает про себя какую-то инопланетную песенку.",
    "🛸 {pet} подпрыгнул на месте и на секунду завис в воздухе от радости!",
    "🐾 {pet} развалился на солнышке и сладко потягивает лапки.",
    "🔮 {pet} внимательно разглядывает пылинку, думая, что это новая планета."
]

AUTONOMOUS_EVENTS_HUNGRY = [
    "🥐 {pet} сидит возле своей миски и намекающе вздыхает...",
    "🐾 {pet} тихо шуршит пакетиком на кухне в поисках вкусняшек.",
    "👀 {pet} жалобно смотрит на всех в чате, намекая, что пора бы покушать!",
    "🍽️ {pet} аккуратно двигает лапкой пустую миску ближе к вам."
]

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
    
    gift_template = random.choice(GIFTS)
    gift_text = gift_template.format(pet=pet_data["name"], user=user_name)
    await message.answer(gift_text)

# --- ОБРАБОТКА КНОПОК ---

@dp.callback_query(F.data == "open_color_menu")
async def process_color_menu(callback: types.CallbackQuery):
    pet_data = get_pet(callback.message.chat.id)
    text = f"Выберите новый цвет шерстки для {pet_data['name']}: 🎨"
    
    if callback.message.photo:
        await callback.message.edit_caption(caption=text, reply_markup=get_color_keyboard())
    else:
        await callback.message.edit_text(text=text, reply_markup=get_color_keyboard())
    await callback.answer()

@dp.callback_query(F.data.startswith("set_color_"))
async def process_set_color(callback: types.CallbackQuery):
    pet_data = get_pet(callback.message.chat.id)
    new_color = callback.data.replace("set_color_", "")
    
    if new_color in SKINS:
        pet_data["color"] = new_color
        save_all_pets(pets_db)
        
        skin = SKINS[new_color]
        await callback.answer(f"Цвет изменён на {skin['name']}! ✨")
        
        if callback.message.photo:
            try:
                media = types.InputMediaPhoto(
                    media=skin['url'],
                    caption=f"🎨 {pet_data['name']} сменил цвет шерстки!\n\n{get_status_text(pet_data)}",
                    parse_mode="Markdown"
                )
                await callback.message.edit_media(media=media, reply_markup=get_keyboard())
            except Exception:
                await callback.message.edit_caption(
                    caption=f"🎨 {pet_data['name']} сменил цвет шерстки!\n\n{get_status_text(pet_data)}",
                    parse_mode="Markdown",
                    reply_markup=get_keyboard()
                )
        else:
            await callback.message.edit_text(
                text=f"🎨 {pet_data['name']} сменил цвет шерстки!\n\n{get_status_text(pet_data)}",
                parse_mode="Markdown",
                reply_markup=get_keyboard()
            )

@dp.callback_query(F.data == "back_to_status")
async def process_back_to_status(callback: types.CallbackQuery):
    pet_data = get_pet(callback.message.chat.id)
    if callback.message.photo:
        await callback.message.edit_caption(
            caption=get_status_text(pet_data),
            parse_mode="Markdown",
            reply_markup=get_keyboard()
        )
    else:
        await callback.message.edit_text(
            text=get_status_text(pet_data),
            parse_mode="Markdown",
            reply_markup=get_keyboard()
        )
    await callback.answer()

@dp.callback_query(F.data == "feed")
async def process_feed(callback: types.CallbackQuery):
    pet_data = get_pet(callback.message.chat.id)
    if pet_data["satiety"] >= 100:
        await callback.answer("Я уже сыт! 🥐", show_alert=True)
        return
    
    pet_data["satiety"] = min(100, pet_data["satiety"] + 25)
    save_all_pets(pets_db)
    
    caption_text = f"🍎 Вы покормили {pet_data['name']}!\n\n{get_status_text(pet_data)}"
    
    if callback.message.photo:
        await callback.message.edit_caption(caption=caption_text, parse_mode="Markdown", reply_markup=get_keyboard())
    else:
        await callback.message.edit_text(text=caption_text, parse_mode="Markdown", reply_markup=get_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "play")
async def process_play(callback: types.CallbackQuery):
    pet_data = get_pet(callback.message.chat.id)
    if pet_data["energy"] < 15:
        await callback.answer("Я слишком устал для игр! 😴", show_alert=True)
        return
    
    pet_data["happiness"] = min(100, pet_data["happiness"] + 20)
    pet_data["energy"] = max(0, pet_data["energy"] - 15)
    pet_data["satiety"] = max(0, pet_data["satiety"] - 10)
    save_all_pets(pets_db)
    
    caption_text = f"⚽ Отлично поиграли!\n\n{get_status_text(pet_data)}"
    
    if callback.message.photo:
        await callback.message.edit_caption(caption=caption_text, parse_mode="Markdown", reply_markup=get_keyboard())
    else:
        await callback.message.edit_text(text=caption_text, parse_mode="Markdown", reply_markup=get_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "sleep")
async def process_sleep(callback: types.CallbackQuery):
    pet_data = get_pet(callback.message.chat.id)
    pet_data["energy"] = min(100, pet_data["energy"] + 40)
    save_all_pets(pets_db)
    
    caption_text = f"😴 {pet_data['name']} вздремнул и восстановил силы!\n\n{get_status_text(pet_data)}"
    
    if callback.message.photo:
        await callback.message.edit_caption(caption=caption_text, parse_mode="Markdown", reply_markup=get_keyboard())
    else:
        await callback.message.edit_text(text=caption_text, parse_mode="Markdown", reply_markup=get_keyboard())
    await callback.answer()

# --- ФОНОВЫЙ ЦИКЛ ---

async def autonomous_life_loop():
    while True:
        await asyncio.sleep(1800)
        
        for chat_id_str, pet_data in pets_db.items():
            pet_data["satiety"] = max(0, pet_data["satiety"] - 5)
            pet_data["happiness"] = max(0, pet_data["happiness"] - 3)
            pet_data["energy"] = max(0, pet_data["energy"] - 2)

            if random.random() < 0.4:
                if pet_data["satiety"] < 40:
                    event_msg = random.choice(AUTONOMOUS_EVENTS_HUNGRY).format(pet=pet_data["name"])
                else:
                    event_msg = random.choice(AUTONOMOUS_EVENTS_HAPPY).format(pet=pet_data["name"])
                
                try:
                    await bot.send_message(int(chat_id_str), event_msg)
                except Exception as e:
                    logging.error(f"Не удалось отправить сообщение: {e}")
        
        save_all_pets(pets_db)

# --- ЗАГЛУШКА ДЛЯ РЕНДЕРА (ФЕЙКОВЫЙ ВЕБ-СЕРВЕР) ---

async def handle_ping(request):
    return web.Response(text="Pettie is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    app.router.add_get('/health', handle_ping)
    
    port = int(os.getenv("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    await start_web_server()
    asyncio.create_task(autonomous_life_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
