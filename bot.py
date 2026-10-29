import asyncio
import logging
import os
import random
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Включаем логирование, чтобы в Render было видно, если что-то пойдёт не так
logging.basicConfig(level=logging.INFO)

# Получаем токен из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("Ошибка: Переменная окружения BOT_TOKEN не задана!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Параметры нашего питомца
pet = {
    "name": "Тамагочи",
    "satiety": 70,   # Сытость (0-100)
    "happiness": 70, # Счастье (0-100)
    "energy": 70,    # Энергия (0-100)
}

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
    await message.answer(get_status_text(), parse_mode="Markdown", reply_markup=get_keyboard())

@dp.callback_query(F.data == "feed")
async def process_feed(callback: types.CallbackQuery):
    if pet["satiety"] >= 100:
        await callback.answer("Питомец уже полностью сыт! 🥐", show_alert=True)
        return
    
    pet["satiety"] = min(100, pet["satiety"] + 25)
    await callback.message.edit_text(
        f"🍎 Вы покормили питомца!\n\n{get_status_text()}",
        parse_mode="Markdown",
        reply_markup=get_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "play")
async def process_play(callback: types.CallbackQuery):
    if pet["energy"] < 15:
        await callback.answer("Питомец слишком устал для игр! 😴", show_alert=True)
        return
    
    pet["happiness"] = min(100, pet["happiness"] + 20)
    pet["energy"] = max(0, pet["energy"] - 15)
    pet["satiety"] = max(0, pet["satiety"] - 10)
    
    await callback.message.edit_text(
        f"⚽ Вы отлично поиграли!\n\n{get_status_text()}",
        parse_mode="Markdown",
        reply_markup=get_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "sleep")
async def process_sleep(callback: types.CallbackQuery):
    pet["energy"] = min(100, pet["energy"] + 40)
    await callback.message.edit_text(
        f"😴 Питомец вздремнул и восстановил силы!\n\n{get_status_text()}",
        parse_mode="Markdown",
        reply_markup=get_keyboard()
    )
    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())