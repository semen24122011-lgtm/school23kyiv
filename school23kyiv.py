import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
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

# хранение заявок
pending_posts = {}


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
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🕵️ Анонимно")],
            [KeyboardButton(text="👤 С именем")]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "Welcome to School 23 Hub Kyiv\n\n"
        "Send anonymous or public messages, photos or videos.",
        reply_markup=keyboard
    )


# =========================
# CHOOSE MODE
# =========================
@dp.message(F.text == "🕵️ Анонимно")
async def anonymous_mode(message: Message, state: FSMContext):
    await state.update_data(mode="anonymous")
    await state.set_state(PostState.waiting_for_content)
    await message.answer("Отправь текст, фото или видео.")


@dp.message(F.text == "👤 С именем")
async def named_mode(message: Message, state: FSMContext):
    await state.update_data(mode="named")
    await state.set_state(PostState.waiting_for_content)
    await message.answer("Отправь текст, фото или видео.")


# =========================
# RECEIVE CONTENT
# =========================
@dp.message(PostState.waiting_for_content)
async def receive_content(message: Message, state: FSMContext):
    data = await state.get_data()
    mode = data.get("mode")

    user = message.from_user
    username = f"@{user.username}" if user.username else user.full_name

    post_id = message.message_id

    pending_posts[post_id] = {
        "mode": mode,
        "user_id": user.id,
        "username": username,
        "text": message.text or message.caption,
        "photo": message.photo[-1].file_id if message.photo else None,
        "video": message.video.file_id if message.video else None
    }

    moderation_buttons = InlineKeyboardMarkup(
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
        f"User ID: {user.id}\n"
        f"Режим: {'Анонимно' if mode == 'anonymous' else 'С именем'}\n\n"
        f"Текст: {message.text or message.caption or 'Без текста'}"
    )

    if message.photo:
        await bot.send_photo(
            OWNER_ID,
            photo=message.photo[-1].file_id,
            caption=mod_text,
            reply_markup=moderation_buttons
        )

    elif message.video:
        await bot.send_video(
            OWNER_ID,
            video=message.video.file_id,
            caption=mod_text,
            reply_markup=moderation_buttons
        )

    else:
        await bot.send_message(
            OWNER_ID,
            mod_text,
            reply_markup=moderation_buttons
        )

    await message.answer("✅ Твоё сообщение отправлено на модерацию.")
    await state.clear()


# =========================
# APPROVE
# =========================
@dp.callback_query(F.data.startswith("approve_"))
async def approve_post(callback: CallbackQuery):
    post_id = int(callback.data.split("_")[1])

    if post_id not in pending_posts:
        await callback.answer("Сообщение не найдено.")
        return

    post = pending_posts[post_id]

    if post["mode"] == "anonymous":
        caption_text = f"🕵️ Анонимное сообщение:\n\n{post['text'] or ''}"
    else:
        caption_text = f"👤 Сообщение от {post['username']}:\n\n{post['text'] or ''}"

    if post["photo"]:
        await bot.send_photo(
            CHANNEL_ID,
            photo=post["photo"],
            caption=caption_text
        )

    elif post["video"]:
        await bot.send_video(
            CHANNEL_ID,
            video=post["video"],
            caption=caption_text
        )

    else:
        await bot.send_message(
            CHANNEL_ID,
            caption_text
        )

    del pending_posts[post_id]

    await callback.message.edit_caption(
        caption="✅ Опубликовано в канал."
    ) if callback.message.photo or callback.message.video else await callback.message.edit_text(
        "✅ Опубликовано в канал."
    )

    await callback.answer()


# =========================
# REJECT
# =========================
@dp.callback_query(F.data.startswith("reject_"))
async def reject_post(callback: CallbackQuery):
    post_id = int(callback.data.split("_")[1])

    if post_id in pending_posts:
        del pending_posts[post_id]

    if callback.message.photo or callback.message.video:
        await callback.message.edit_caption(
            caption="❌ Сообщение отклонено."
        )
    else:
        await callback.message.edit_text(
            "❌ Сообщение отклонено."
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