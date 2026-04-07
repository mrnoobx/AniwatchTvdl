#@cantarellabots
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
import time
import sys
import os

from cantarella.core.database import db
from config import OWNER_ID

@Client.on_message(filters.private & filters.command("add_admin"))
async def handle_add_admin(client: Client, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply("<blockquote>❌ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪꜱ ᴏɴʟʏ ғᴏʀ ᴛʜᴇ ʙᴏᴛ ᴏᴡɴᴇʀ.</blockquote>", parse_mode=ParseMode.HTML)

    user_id = None
    user_name = "Admin"

    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        user_name = message.reply_to_message.from_user.first_name
    elif len(message.command) > 1:
        try:
            user_id = int(message.command[1])
        except ValueError:
            return await message.reply("<blockquote>❌ ɪɴᴠᴀʟɪᴅ ᴜꜱᴇʀ ɪᴅ.</blockquote>", parse_mode=ParseMode.HTML)

    if not user_id:
        return await message.reply("<blockquote>❌ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜꜱᴇʀ'ꜱ ᴍᴇꜱꜱᴀɢᴇ ᴏʀ ᴘʀᴏᴠɪᴅᴇ ᴛʜᴇɪʀ ᴜꜱᴇʀ ɪᴅ.</blockquote>", parse_mode=ParseMode.HTML)

    await db.add_admin(user_id, user_name)
    await message.reply(f"<blockquote>✅ <b>ᴀᴅᴍɪɴ ᴀᴅᴅᴇᴅ:</b> {user_name} (<code>{user_id}</code>)</blockquote>", parse_mode=ParseMode.HTML)

@Client.on_message(filters.private & filters.command("rm_admin"))
async def handle_rm_admin(client: Client, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply("<blockquote>❌ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪꜱ ᴏɴʟʏ ғᴏʀ ᴛʜᴇ ʙᴏᴛ ᴏᴡɴᴇʀ.</blockquote>", parse_mode=ParseMode.HTML)

    user_id = None
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        try:
            user_id = int(message.command[1])
        except ValueError:
            return await message.reply("<blockquote>❌ ɪɴᴠᴀʟɪᴅ ᴜꜱᴇʀ ɪᴅ.</blockquote>", parse_mode=ParseMode.HTML)

    if not user_id:
        return await message.reply("<blockquote>❌ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜꜱᴇʀ'ꜱ ᴍᴇꜱꜱᴀɢᴇ ᴏʀ ᴘʀᴏᴠɪᴅᴇ ᴛʜᴇɪʀ ᴜꜱᴇʀ ɪᴅ.</blockquote>", parse_mode=ParseMode.HTML)

    await db.remove_admin(user_id)
    await message.reply(f"<blockquote>✅ <b>ᴀᴅᴍɪɴ ʀᴇᴍᴏᴠᴇᴅ:</b> <code>{user_id}</code></blockquote>", parse_mode=ParseMode.HTML)

@Client.on_message(filters.private & filters.command("admins"))
async def handle_admins_list(client: Client, message):
    is_admin = await db.is_admin(message.from_user.id)
    if message.from_user.id != OWNER_ID and not is_admin:
        return await message.reply("<blockquote>❌ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪꜱ ғᴏʀ ᴀᴅᴍɪɴɪꜱᴛʀᴀᴛᴏʀꜱ ᴏɴʟʏ.</blockquote>", parse_mode=ParseMode.HTML)

    admins = await db.get_all_admins()
    if not admins:
        return await message.reply("<blockquote>📋 <b>ɴᴏ ᴀᴅᴍɪɴꜱ ᴀᴅᴅᴇᴅ ʏᴇᴛ.</b></blockquote>", parse_mode=ParseMode.HTML)

    text = "<blockquote>📋 <b>ʙᴏᴛ ᴀᴅᴍɪɴɪꜱᴛʀᴀᴛᴏʀꜱ:</b>\n\n"
    text += f"👑 <b>ᴏᴡɴᴇʀ:</b> <code>{OWNER_ID}</code>\n"
    for admin in admins:
        admin_name = admin.get('name', 'Admin')
        text += f"• {admin_name}: <code>{admin['_id']}</code>\n"
    text += "</blockquote>"

    await message.reply(text, parse_mode=ParseMode.HTML)

@Client.on_message(filters.private & filters.command("users"))
async def handle_users_count(client: Client, message):
    is_admin = await db.is_admin(message.from_user.id)
    if message.from_user.id != OWNER_ID and not is_admin:
        return await message.reply("<blockquote>❌ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪꜱ ғᴏʀ ᴀᴅᴍɪɴɪꜱᴛʀᴀᴛᴏʀꜱ ᴏɴʟʏ.</blockquote>", parse_mode=ParseMode.HTML)

    count = await db.get_user_count()
    await message.reply(f"<blockquote>📊 <b>ᴛᴏᴛᴀʟ ᴜꜱᴇʀꜱ:</b> <code>{count}</code></blockquote>", parse_mode=ParseMode.HTML)

@Client.on_message(filters.private & filters.command("ping"))
async def handle_ping(client: Client, message):
    start_t = time.time()
    msg = await message.reply("<b>ᴘᴏɴɢ...</b>", parse_mode=ParseMode.HTML)
    end_t = time.time()

    ping = (end_t - start_t) * 1000
    await msg.edit_text(f"<b>ᴘᴏɴɢ!</b> <code>{ping:.3f} ᴍꜱ</code>", parse_mode=ParseMode.HTML)


@Client.on_message(filters.private & filters.command("restart"))
async def handle_restart(client: Client, message):
    is_admin = await db.is_admin(message.from_user.id)
    if message.from_user.id != OWNER_ID and not is_admin:
        return await message.reply("<blockquote>❌ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪꜱ ᴏɴʟʏ ꜰᴏʀ ᴀᴅᴍɪɴꜱ ᴏʀ ᴛʜᴇ ʙᴏᴛ ᴏᴡɴᴇʀ.</blockquote>", parse_mode=ParseMode.HTML)

    msg = await message.reply("<b>🔄 ʀᴇꜱᴛᴀʀᴛɪɴɢ ʙᴏᴛ...</b>", parse_mode=ParseMode.HTML)

    # Save the restart message info to DB so it can be updated after restart
    await db.set_user_setting(OWNER_ID, "restart_msg_id", msg.id)
    await db.set_user_setting(OWNER_ID, "restart_chat_id", msg.chat.id)

    # Restart the current process
    os.execl(sys.executable, sys.executable, "-m", "cantarella")
