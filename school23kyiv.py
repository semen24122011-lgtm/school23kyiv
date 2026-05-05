import asyncio
import json
import os

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# =========================
# SETTINGS
# =========================
BOT_TOKEN = "8625861867:AAEVud8NrymeR4yHVNjdNqORl5qKgijANVA"

OWNER_ID = 7381375989
CHANNEL_ID = -1003828225024

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

pending_posts = {}
USERS_FILE = "users.json"


# =========================
# USERS SAVE/UPDATE
# =========================
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}

    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)


def update_user(user):
    users = load_users()

    user_id = str(user.id)
    username = f"@{user.username}" if user.username else "No username"

    users[user_id] = {
        "username": username,
        "name": user.full_name
    }

    save_users(users)


# =========================
# STATES
# =========================
class PostState(StatesGroup):
    waiting_for_content = State()


# =========================
# START
# =========================
@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    update_user(message.from_user)

    if message.from_user.id == OWNER_ID:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🕵️ Анонимно")],
                [KeyboardButton(text="👤 С именем")],
                [KeyboardButton(text="📋 Пользователи")]
            ],
            resize_keyboard=True
        )
    else:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🕵️ Анонимно")],
                [KeyboardButton(text="👤 С именем")]
            ],
            resize_keyboard=True
        )

    await message.answer(
        "Welcome to School 23 Hub Kyiv 🖤\n\n"
        "Send anonymous or public messages, photos or videos.",
        reply_markup=keyboard
    )


# =========================
# USERS LIST (ONLY OWNER)
# =========================
@dp.message(F.text == "📋 Пользователи")
async def users_list(message: Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("У вас нет доступа.")
        return

    users = load_users()

    if not users:
        await message.answer("Пользователей пока нет.")
        return

    text = f"Всего пользователей: {len(users)}\n\n"

    for i, (user_id, data) in enumerate(users.items(), start=1):
        text += (
            f"{i}. {data['username']}\n"
            f"ID: {user_id}\n\n"
        )

    await message.answer(text)


# =========================
# MODE SELECTION
# =========================
@dp.message(F.text == "🕵️ Анонимно")
async def anonymous_mode(message: Message, state: FSMContext):
    update_user(message.from_user)

    await state.update_data(mode="anonymous")
    await state.set_state(PostState.waiting_for_content)

    await message.answer("Отправь текст, фото или видео.")


@dp.message(F.text == "👤 С именем")
async def named_mode(message: Message, state: FSMContext):
    update_user(message.from_user)

    await state.update_data(mode="named")
    await state.set_state(PostState.waiting_for_content)

    await message.answer("Отправь текст, фото или видео.")


# =========================
# RECEIVE CONTENT
# =========================
@dp.message(PostState.waiting_for_content)
async def receive_content(message: Message, state: FSMContext):
    update_user(message.from_user)

    data = await state.get_data()
    mode = data.get("mode")

    user = message.from_user
    username = f"@{user.username}" if user.username else user.full_name

    post_id = message.message_id

    pending_posts[post_id] = {
        "mode": mode,
        "username": username,
        "user_id": user.id,
        "text": message.text or message.caption,
        "photo": message.photo[-1].file_id if message.photo else None,
        "video": message.video.file_id if message.video else None
    }

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Отправить",
                    callback_data=f"approve_{post_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"reject_{post_id}"
                )
            ]
        ]
    )

    mod_text = (
        f"📩 Новая заявка\n\n"
        f"Username: {username}\n"
        f"ID: {user.id}\n"
        f"Режим: {'Анонимно' if mode == 'anonymous' else 'С именем'}\n\n"
        f"Текст: {message.text or message.caption or 'Без текста'}"
    )

    if message.photo:
        await bot.send_photo(
            OWNER_ID,
            photo=message.photo[-1].file_id,
            caption=mod_text,
            reply_markup=keyboard
        )

    elif message.video:
        await bot.send_video(
            OWNER_ID,
            video=message.video.file_id,
            caption=mod_text,
            reply_markup=keyboard
        )

    else:
        await bot.send_message(
            OWNER_ID,
            mod_text,
            reply_markup=keyboard
        )

    await message.answer("✅ Сообщение отправлено на модерацию.")
    await state.clear()


# =========================
# APPROVE POST
# =========================
@dp.callback_query(F.data.startswith("approve_"))
async def approve_post(callback: CallbackQuery):
    post_id = int(callback.data.split("_")[1])

    if post_id not in pending_posts:
        await callback.answer("Сообщение не найдено.")
        return

    post = pending_posts[post_id]

    if post["mode"] == "anonymous":
        caption = f"🕵️ Анонимное сообщение:\n\n{post['text'] or ''}"
    else:
        caption = f"👤 Сообщение от {post['username']}:\n\n{post['text'] or ''}"

    if post["photo"]:
        await bot.send_photo(
            CHANNEL_ID,
            photo=post["photo"],
            caption=caption
        )

    elif post["video"]:
        await bot.send_video(
            CHANNEL_ID,
            video=post["video"],
            caption=caption
        )

    else:
        await bot.send_message(
            CHANNEL_ID,
            caption
        )

    del pending_posts[post_id]

    if callback.message.photo or callback.message.video:
        await callback.message.edit_caption(
            caption="✅ Опубликовано."
        )
    else:
        await callback.message.edit_text(
            "✅ Опубликовано."
        )

    await callback.answer()


# =========================
# REJECT POST
# =========================
@dp.callback_query(F.data.startswith("reject_"))
async def reject_post(callback: CallbackQuery):
    post_id = int(callback.data.split("_")[1])

    if post_id in pending_posts:
        del pending_posts[post_id]

    if callback.message.photo or callback.message.video:
        await callback.message.edit_caption(
            caption="❌ Отклонено."
        )
    else:
        await callback.message.edit_text(
            "❌ Отклонено."
        )

    await callback.answer()


# =========================
# RUN BOT
# =========================
async def main():
    print("Bot started...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())