import asyncio
import json
import logging
import os
import random
import time
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
SLEEP_DURATION_SECONDS = 300  # 5 минут сна

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

# --- НАБОРЫ ДЕЙСТВИЙ, ТРЮКОВ И ПОДАРКОВ ---

GIFTS = [
    "🎁 {pet} принёс для {user} блестящий космический камушек!",
    "🎁 {pet} притащил в зубах свежий кекс с другого конца галактики!",
    "🎁 {pet} подарил {user} маленькую звёздочку в прозрачной баночке!",
    "🎁 {pet} выкатил из-под дивана забавную пищащую игрушку для {user}!",
    "🎁 {pet} протягивает {user} пушистый космический одуванчик 🌸",
    "🎁 {pet} достал из тайника редкий разноцветный кристалльчик для {user}!",
    "🎁 {pet} гордо принёс {user} миниатюрную тарелочку с космическим печеньем!",
    "🎁 {pet} нашел и притащил {user} мягкие домашние тапочки!",
    "🎁 {pet} протягивает {user} волшебную палочку, которая светится в темноте ✨",
    "🎁 {pet} делится с {user} своим любимым виртуальным пледиком!",
    "🎁 {pet} принёс для {user} баночку с мерцающим космическим вареньем 🍓",
    "🎁 {pet} достал откуда-то крошечный бумажный самолётик с предсказанием!"
]

STUDY_PHRASES = [
    "📚 {pet} внимательно учит алфавит и забавно повторяет звуки!",
    "🧮 {pet} решает простые задачки и радостно машет лапками!",
    "🌌 {pet} изучает карту звёздного неба и запоминает названия созвездий!",
    "📖 {pet} прочитал детскую книжку и гордо показывает картинки!"
]

TRICKS = [
    "🎪 {pet} делает тройное сальто в воздухе и грациозно приземляется!",
    "🎪 {pet} балансирует мячиком на носу и подмигивает вам!",
    "🎪 {pet} встаёт на задние лапки и забавно кланяется чату!",
    "🎪 {pet} исчезает на секунду в вспышке искорок и появляется сзади!"
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
            "color": "blue",
            "level": 1,
            "exp": 0,
            "iq": 10,
            "age": 1,
            "sleep_until": 0
        }
        save_all_pets(pets_db)
    else:
        pet = pets_db[str_id]
        pet.setdefault("level", 1)
        pet.setdefault("exp", 0)
        pet.setdefault("iq", 10)
        pet.setdefault("age", 1)
        pet.setdefault("sleep_until", 0)
    return pets_db[str_id]

def is_sleeping(pet_data: dict) -> bool:
    return time.time() < pet_data.get("sleep_until", 0)

def get_remaining_sleep_time(pet_data: dict) -> int:
    remaining = int(pet_data.get("sleep_until", 0) - time.time())
    return max(0, remaining)

def add_exp(pet_data: dict, amount: int) -> str:
    pet_data["exp"] += amount
    needed_exp = pet_data["level"] * 50
    if pet_data["exp"] >= needed_exp:
        pet_data["level"] += 1
        pet_data["exp"] -= needed_exp
        pet_data["age"] += 1
        return f"\n\n🎉 **УРА! {pet_data['name']} подрос и получил {pet_data['level']} уровень!** 🎂 (Возраст: {pet_data['age']} дн.)"
    return ""

def get_status_text(pet_data: dict) -> str:
    def make_bar(value):
        filled = round(value / 20)
        return "🟩" * filled + "⬜" * (5 - filled)

    current_skin = SKINS.get(pet_data["color"], SKINS["blue"])["name"]
    needed_exp = pet_data["level"] * 50

    if is_sleeping(pet_data):
        rem_min = (get_remaining_sleep_time(pet_data) // 60) + 1
        sleep_status = f"😴 **Спит** (проснется через ~{rem_min} мин.)"
    else:
        sleep_status = "⚡ **Бодрствует**"

    return (
        f"🐾 **Питомец:** {pet_data['name']}\n"
        f"Статус: {sleep_status}\n"
        f"🌟 **Уровень:** {pet_data['level']} ({pet_data['exp']}/{needed_exp} EXP)\n"
        f"🎂 **Возраст:** {pet_data['age']} дн. | 🧠 **IQ:** {pet_data['iq']}\n"
        f"🎨 **Шерстка:** {current_skin}\n\n"
        f"🍖 **Сытость:** {make_bar(pet_data['satiety'])} ({pet_data['satiety']}%)\n"
        f"💛 **Счастье:** {make_bar(pet_data['happiness'])} ({pet_data['happiness']}%)\n"
        f"⚡ **Энергия:** {make_bar(pet_data['energy'])} ({pet_data['energy']}%)\n"
    )

def get_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🍎 Покормить", callback_data="feed")
    builder.button(text="⚽ Поиграть", callback_data="play")
    builder.button(text="📚 Учить", callback_data="study")
    builder.button(text="😴 Спать", callback_data="sleep")
    builder.button(text="🎪 Трюк", callback_data="trick")
    builder.button(text="🎨 Сменить цвет", callback_data="open_color_menu")
    builder.adjust(3, 2, 1)
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
        f"• `/study` — позаниматься и прокачать IQ 📚\n"
        f"• `/trick` — попросить показать трюк 🎪\n"
        f"• `/gift` — попросить случайный подарок 🎁\n"
        f"• `/top` — посмотреть топ умных питомцев 🏆\n"
        f"• `/color` — изменить цвет шерстки 🎨\n"
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
    if is_sleeping(pet_data):
        rem_min = (get_remaining_sleep_time(pet_data) // 60) + 1
        await message.answer(f"😴 {pet_data['name']} сейчас сладко спит и проснется через ~{rem_min} мин. Не будите его!")
        return

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
    if is_sleeping(pet_data):
        rem_min = (get_remaining_sleep_time(pet_data) // 60) + 1
        await message.answer(f"😴 {pet_data['name']} спит и не может принести подарок. Проснется через ~{rem_min} мин.!")
        return

    user_name = message.from_user.first_name
    gift_template = random.choice(GIFTS)
    gift_text = gift_template.format(pet=pet_data["name"], user=user_name)
    await message.answer(gift_text)

@dp.message(Command("study"))
async def cmd_study(message: types.Message):
    pet_data = get_pet(message.chat.id)
    if is_sleeping(pet_data):
        rem_min = (get_remaining_sleep_time(pet_data) // 60) + 1
        await message.answer(f"😴 {pet_data['name']} спит! Проснется через ~{rem_min} мин.")
        return

    if pet_data["energy"] < 20:
        await message.answer(f"😴 {pet_data['name']} слишком устал для учёбы! Отправьте его спать.")
        return
    
    pet_data["iq"] += random.randint(2, 5)
    pet_data["energy"] = max(0, pet_data["energy"] - 20)
    pet_data["satiety"] = max(0, pet_data["satiety"] - 10)
    lvl_msg = add_exp(pet_data, 25)
    save_all_pets(pets_db)
    
    phrase = random.choice(STUDY_PHRASES).format(pet=pet_data["name"])
    await message.answer(f"{phrase}\n🧠 **IQ вырастает до {pet_data['iq']}!** (+25 EXP){lvl_msg}")

@dp.message(Command("trick"))
async def cmd_trick(message: types.Message):
    pet_data = get_pet(message.chat.id)
    if is_sleeping(pet_data):
        rem_min = (get_remaining_sleep_time(pet_data) // 60) + 1
        await message.answer(f"😴 {pet_data['name']} спит! Проснется через ~{rem_min} мин.")
        return

    if pet_data["iq"] < 15:
        await message.answer(f"🤔 {pet_data['name']} еще пока не знает трюков! Позанимайтесь с ним через `/study`.")
        return
    
    trick = random.choice(TRICKS).format(pet=pet_data["name"])
    await message.answer(trick)

@dp.message(Command("top"))
async def cmd_top(message: types.Message):
    if not pets_db:
        await message.answer("Пока нет зарегистрированных питомцев!")
        return
    
    sorted_pets = sorted(pets_db.values(), key=lambda p: (p.get("level", 1), p.get("iq", 10)), reverse=True)[:5]
    
    top_text = "🏆 **ТОП-5 САМЫХ УМНЫХ И РАЗВИТЫХ ПИТОМЦЕВ:**\n\n"
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    
    for i, pet in enumerate(sorted_pets):
        top_text += f"{medals[i]} **{pet['name']}** — Уровень {pet.get('level', 1)} | IQ: {pet.get('iq', 10)} | Возраст: {pet.get('age', 1)} дн.\n"
        
    await message.answer(top_text, parse_mode="Markdown")

# --- ОБРАБОТКА КНОПОК ---

@dp.callback_query(F.data == "open_color_menu")
async def process_color_menu(callback: types.CallbackQuery):
    pet_data = get_pet(callback.message.chat.id)
    if is_sleeping(pet_data):
        rem_min = (get_remaining_sleep_time(pet_data) // 60) + 1
        await callback.answer(f"😴 {pet_data['name']} спит! Проснется через ~{rem_min} мин.", show_alert=True)
        return

    text = f"Выберите новый цвет шерстки для {pet_data['name']}: 🎨"
    if callback.message.photo:
        await callback.message.edit_caption(caption=text, reply_markup=get_color_keyboard())
    else:
        await callback.message.edit_text(text=text, reply_markup=get_color_keyboard())
    await callback.answer()

@dp.callback_query(F.data.startswith("set_color_"))
async def process_set_color(callback: types.CallbackQuery):
    pet_data = get_pet(callback.message.chat.id)
    if is_sleeping(pet_data):
        rem_min = (get_remaining_sleep_time(pet_data) // 60) + 1
        await callback.answer(f"😴 {pet_data['name']} спит! Проснется через ~{rem_min} мин.", show_alert=True)
        return

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
    if is_sleeping(pet_data):
        rem_min = (get_remaining_sleep_time(pet_data) // 60) + 1
        await callback.answer(f"😴 {pet_data['name']} сейчас спит! Проснется через ~{rem_min} мин.", show_alert=True)
        return

    if pet_data["satiety"] >= 100:
        await callback.answer("Я уже сыт! 🥐", show_alert=True)
        return
    
    pet_data["satiety"] = min(100, pet_data["satiety"] + 25)
    lvl_msg = add_exp(pet_data, 10)
    save_all_pets(pets_db)
    
    caption_text = f"🍎 Вы покормили {pet_data['name']}! (+10 EXP){lvl_msg}\n\n{get_status_text(pet_data)}"
    
    if callback.message.photo:
        await callback.message.edit_caption(caption=caption_text, parse_mode="Markdown", reply_markup=get_keyboard())
    else:
        await callback.message.edit_text(text=caption_text, parse_mode="Markdown", reply_markup=get_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "play")
async def process_play(callback: types.CallbackQuery):
    pet_data = get_pet(callback.message.chat.id)
    if is_sleeping(pet_data):
        rem_min = (get_remaining_sleep_time(pet_data) // 60) + 1
        await callback.answer(f"😴 {pet_data['name']} сейчас спит! Проснется через ~{rem_min} мин.", show_alert=True)
        return

    if pet_data["energy"] < 15:
        await callback.answer("Я слишком устал для игр! 😴", show_alert=True)
        return
    
    pet_data["happiness"] = min(100, pet_data["happiness"] + 20)
    pet_data["energy"] = max(0, pet_data["energy"] - 15)
    pet_data["satiety"] = max(0, pet_data["satiety"] - 10)
    lvl_msg = add_exp(pet_data, 15)
    save_all_pets(pets_db)
    
    caption_text = f"⚽ Отлично поиграли! (+15 EXP){lvl_msg}\n\n{get_status_text(pet_data)}"
    
    if callback.message.photo:
        await callback.message.edit_caption(caption=caption_text, parse_mode="Markdown", reply_markup=get_keyboard())
    else:
        await callback.message.edit_text(text=caption_text, parse_mode="Markdown", reply_markup=get_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "study")
async def process_study(callback: types.CallbackQuery):
    pet_data = get_pet(callback.message.chat.id)
    if is_sleeping(pet_data):
        rem_min = (get_remaining_sleep_time(pet_data) // 60) + 1
        await callback.answer(f"😴 {pet_data['name']} сейчас спит! Проснется через ~{rem_min} мин.", show_alert=True)
        return

    if pet_data["energy"] < 20:
        await callback.answer("Я слишком устал для учёбы! 😴", show_alert=True)
        return
    
    pet_data["iq"] += random.randint(2, 5)
    pet_data["energy"] = max(0, pet_data["energy"] - 20)
    pet_data["satiety"] = max(0, pet_data["satiety"] - 10)
    lvl_msg = add_exp(pet_data, 25)
    save_all_pets(pets_db)
    
    phrase = random.choice(STUDY_PHRASES).format(pet=pet_data["name"])
    caption_text = f"{phrase}\n🧠 IQ: {pet_data['iq']} (+25 EXP){lvl_msg}\n\n{get_status_text(pet_data)}"
    
    if callback.message.photo:
        await callback.message.edit_caption(caption=caption_text, parse_mode="Markdown", reply_markup=get_keyboard())
    else:
        await callback.message.edit_text(text=caption_text, parse_mode="Markdown", reply_markup=get_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "trick")
async def process_trick(callback: types.CallbackQuery):
    pet_data = get_pet(callback.message.chat.id)
    if is_sleeping(pet_data):
        rem_min = (get_remaining_sleep_time(pet_data) // 60) + 1
        await callback.answer(f"😴 {pet_data['name']} сейчас спит! Проснется через ~{rem_min} мин.", show_alert=True)
        return

    if pet_data["iq"] < 15:
        await callback.answer("Петти еще слишком мал и не знает трюков! Сначала поучите его (кнопка 📚 Учить).", show_alert=True)
        return
    
    trick = random.choice(TRICKS).format(pet=pet_data["name"])
    await callback.answer(trick, show_alert=True)

@dp.callback_query(F.data == "sleep")
async def process_sleep(callback: types.CallbackQuery):
    pet_data = get_pet(callback.message.chat.id)
    if is_sleeping(pet_data):
        rem_min = (get_remaining_sleep_time(pet_data) // 60) + 1
        await callback.answer(f"😴 {pet_data['name']} уже сладко спит! Проснется через ~{rem_min} мин.", show_alert=True)
        return

    pet_data["sleep_until"] = time.time() + SLEEP_DURATION_SECONDS
    save_all_pets(pets_db)
    
    caption_text = f"😴 {pet_data['name']} укутался в пледик и улегся спать на 5 минут!\n\n{get_status_text(pet_data)}"
    
    if callback.message.photo:
        await callback.message.edit_caption(caption=caption_text, parse_mode="Markdown", reply_markup=get_keyboard())
    else:
        await callback.message.edit_text(text=caption_text, parse_mode="Markdown", reply_markup=get_keyboard())
    await callback.answer("Петти отправился спать на 5 минут! 💤")

# --- ФОНОВЫЙ ЦИКЛ (ПРОВЕРКА СНА И АВТОНОМНЫЕ СОБЫТИЯ) ---

async def autonomous_life_loop():
    while True:
        await asyncio.sleep(15)  # Проверка статуса каждые 15 секунд
        current_now = time.time()
        
        for chat_id_str, pet_data in list(pets_db.items()):
            # Проверка пробуждения
            if pet_data.get("sleep_until", 0) > 0 and current_now >= pet_data["sleep_until"]:
                pet_data["sleep_until"] = 0
                pet_data["energy"] = 100
                save_all_pets(pets_db)
                try:
                    await bot.send_message(
                        int(chat_id_str),
                        f"☀️ **{pet_data['name']} проснулся, полнен сил (Энергия 100%) и готов играть дальше!** 🐾"
                    )
                except Exception as e:
                    logging.error(f"Ошибка отправки уведомления о пробуждении: {e}")

        # Каждые 30 минут снижаем показатели и отправляем автономные события
        if int(current_now) % 1800 < 15:
            for chat_id_str, pet_data in pets_db.items():
                if not is_sleeping(pet_data):
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

# --- ЗАГЛУШКА ДЛЯ РЕНДЕРА ---

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
