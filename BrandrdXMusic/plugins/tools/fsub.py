from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pymongo import MongoClient
from BrandrdXMusic import app
import asyncio
from BrandrdXMusic.misc import SUDOERS
from config import MONGO_DB_URI
from pyrogram.enums import ChatMembersFilter
from pyrogram.errors import (
    ChatAdminRequired,
    UserNotParticipant,
    UsernameNotOccupied,
    PeerIdInvalid,
)

fsubdb = MongoClient(MONGO_DB_URI)
forcesub_collection = fsubdb.status_db.status


# ------------------ SET FORCE SUB ------------------
@app.on_message(filters.command(["fsub", "forcesub"]) & filters.group)
async def set_forcesub(client: Client, message: Message):
    chat_id = message.chat.id

    if not message.from_user:
        return

    user_id = message.from_user.id
    member = await client.get_chat_member(chat_id, user_id)

    if not (member.status == "creator" or user_id in SUDOERS):
        return await message.reply_text("**Only group owners or sudo users can use this command.**")

    if len(message.command) == 2 and message.command[1].lower() in ["off", "disable"]:
        forcesub_collection.delete_one({"chat_id": chat_id})
        return await message.reply_text("**Force subscription has been disabled for this group.**")

    if len(message.command) != 2:
        return await message.reply_text("**Usage:** `/fsub <channel username or ID>` or `/fsub off`")

    channel_input = message.command[1]

    # ✅ ensure username format
    if channel_input.startswith("https://t.me/"):
        channel_input = channel_input.replace("https://t.me/", "").replace("@", "")

    try:
        channel_info = await client.get_chat(channel_input)
        channel_id = channel_info.id
        channel_title = channel_info.title

        try:
            channel_link = await app.export_chat_invite_link(channel_id)
        except ChatAdminRequired:
            channel_link = f"https://t.me/{channel_info.username}" if channel_info.username else None

        channel_username = f"{channel_info.username}" if channel_info.username else channel_link

        # ✅ get member count properly
        try:
            channel_members_count = await app.get_chat_members_count(channel_id)
        except Exception:
            channel_members_count = "Unknown"

        # ✅ check bot is admin in channel
        bot_id = (await client.get_me()).id
        bot_is_admin = False

        async for admin in app.get_chat_members(channel_id, filter=ChatMembersFilter.ADMINISTRATORS):
            if admin.user.id == bot_id:
                bot_is_admin = True
                break

        if not bot_is_admin:
            return await message.reply_photo(
                photo="https://envs.sh/TnZ.jpg",
                caption=("🚫 **I'm not an admin in this channel.**\n\n"
                         "➲ Please make me an admin with:\n"
                         "➥ Invite new members\n\n"
                         "Then use `/fsub <channel_username>` again."),
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("➕ Add Me in Channel",
                                           url=f"https://t.me/{app.username}?startchannel=s&admin=invite_users+manage_video_chats")]]
                )
            )

        # ✅ save to DB
        forcesub_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"channel_id": channel_id, "channel_username": channel_username}},
            upsert=True
        )

        set_by_user = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name

        await message.reply_photo(
            photo="https://envs.sh/Tn_.jpg",
            caption=(
                f"🎉 **Force subscription set to** [{channel_title}]({channel_username})\n\n"
                f"🆔 **Channel ID:** `{channel_id}`\n"
                f"📎 **Channel Link:** {channel_link or 'N/A'}\n"
                f"👥 **Members:** {channel_members_count}\n"
                f"👤 **Set by:** {set_by_user}"
            ),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("✖ Close", callback_data="close_force_sub")]]
            )
        )

    except (UsernameNotOccupied, PeerIdInvalid):
        await message.reply_text("🚫 **Invalid username or channel ID.** Please check and try again.")
    except Exception as e:
        await message.reply_text(f"⚠️ Unexpected error: `{e}`")


# ------------------ CLOSE BUTTON ------------------
@app.on_callback_query(filters.regex("close_force_sub"))
async def close_force_sub(client: Client, callback_query: CallbackQuery):
    await callback_query.answer("Closed!")
    await callback_query.message.delete()
