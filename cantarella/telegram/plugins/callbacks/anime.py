#@cantarellabots
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup
from cantarella.button import Button as InlineKeyboardButton

from cantarella.core.state import user_episodes, user_search_results
from config import *
from .helpers import check_fsub, send_fsub_prompt

# ─────────────────────────────────────────────
#  Anime select & episode pagination
# ─────────────────────────────────────────────

@Client.on_callback_query(filters.regex("^anime_"))
async def on_anime_select(client: Client, callback_query):
    if not await check_fsub(client, callback_query.from_user.id):
        await callback_query.answer("🔒 ᴘʟᴇᴀꜱᴇ ᴊᴏɪɴ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ ꜰɪʀꜱᴛ!", show_alert=True)
        return await send_fsub_prompt(client, callback_query.message)

    anime_id = callback_query.data.split("_")[1]
    url = f"https://aniwatchtv.to/watch/{anime_id}"
    from cantarella.scraper.cantarellatv import cantarellatvDownloader
    downloader = cantarellatvDownloader()
    entries = await client.loop.run_in_executor(None, downloader.list_episodes, url)

    if not entries:
        await callback_query.answer("❌ ɴᴏ ᴇᴘɪꜱᴏᴅᴇꜱ ꜰᴏᴜɴᴅ.")
        return

    user_episodes[callback_query.from_user.id] = {
        'title':    entries[0].get('title', 'ᴜɴᴋɴᴏᴡɴ'),
        'episodes': entries,
        'url':      url,
        'page':     0
    }
    await show_episodes_page(client, callback_query, 0)


async def show_episodes_page(client, callback_query, page):
    user_id = callback_query.from_user.id
    data    = user_episodes.get(user_id)
    if not data:
        return

    entries         = data['episodes']
    start           = page * 20
    end             = start + 20
    current_entries = entries[start:end]

    buttons = []
    for i, entry in enumerate(current_entries):
        ep_idx = start + i
        buttons.append([InlineKeyboardButton(f"ᴇᴘɪꜱᴏᴅᴇ {ep_idx+1}", callback_data=f"ep_{ep_idx}")])

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ ᴘʀᴇᴠ", callback_data=f"eps_page_{page-1}"))
    if end < len(entries):
        nav_row.append(InlineKeyboardButton("ɴᴇxᴛ ➡️", callback_data=f"eps_page_{page+1}"))

    jump_row = []
    if page >= 5:
        jump_row.append(InlineKeyboardButton("⏪ -100 ᴇᴘꜱ", callback_data=f"eps_page_{page-5}"))
    if (page + 5) * 20 < len(entries):
        jump_row.append(InlineKeyboardButton("+100 ᴇᴘꜱ ⏩", callback_data=f"eps_page_{page+5}"))

    if nav_row:
        buttons.append(nav_row)
    if jump_row:
        buttons.append(jump_row)

    buttons.append([
        InlineKeyboardButton("🔙 ʙᴀᴄᴋ",         callback_data="back_to_search"),
        InlineKeyboardButton("📥 ᴅᴏᴡɴʟᴏᴀᴅ ᴀʟʟ", callback_data="download_all_opts"),
        InlineKeyboardButton("❌ ᴄʟᴏꜱᴇ",         callback_data="cancel")
    ])

    try:
        await callback_query.edit_message_caption(
            caption=f"<blockquote>📺 <b>ᴇᴘɪꜱᴏᴅᴇꜱ (ᴘᴀɢᴇ {page+1}):</b>\nꜱᴇʟᴇᴄᴛ ᴀɴ ᴇᴘɪꜱᴏᴅᴇ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ:</blockquote>",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.HTML
        )
    except:
        await callback_query.edit_message_text(
            f"<blockquote>📺 <b>ᴇᴘɪꜱᴏᴅᴇꜱ (ᴘᴀɢᴇ {page+1}):</b>\nꜱᴇʟᴇᴄᴛ ᴀɴ ᴇᴘɪꜱᴏᴅᴇ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ:</blockquote>",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.HTML
        )


@Client.on_callback_query(filters.regex("^eps_page_"))
async def on_eps_page(client: Client, callback_query):
    page = int(callback_query.data.split("_")[2])
    await show_episodes_page(client, callback_query, page)


@Client.on_callback_query(filters.regex("^back_to_search$"))
async def on_back_to_search(client: Client, callback_query):
    user_id = callback_query.from_user.id
    results = user_search_results.get(user_id)
    if not results:
        await callback_query.answer("❌ ꜱᴇᴀʀᴄʜ ʀᴇꜱᴜʟᴛꜱ ᴇxᴘɪʀᴇᴅ.", show_alert=True)
        return

    buttons = []
    for res in results:
        cb_data = f"anime_{res['id']}"
        if len(cb_data) > 64:
            cb_data = cb_data[:64]
        buttons.append([InlineKeyboardButton(f"{res['title']} ({res['type']})", callback_data=cb_data)])

    buttons.append([InlineKeyboardButton("❌ ᴄʟᴏꜱᴇ", callback_data="cancel")])

    keyboard = InlineKeyboardMarkup(buttons)
    try:
        await callback_query.edit_message_caption(
            caption="<blockquote>📺 <b>ꜱᴇᴀʀᴄʜ ʀᴇꜱᴜʟᴛꜱ:</b>\nꜱᴇʟᴇᴄᴛ ᴀɴ ᴀɴɪᴍᴇ:</blockquote>",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    except:
        await callback_query.edit_message_text(
            "<blockquote>📺 <b>ꜱᴇᴀʀᴄʜ ʀᴇꜱᴜʟᴛꜱ:</b>\nꜱᴇʟᴇᴄᴛ ᴀɴ ᴀɴɪᴍᴇ:</blockquote>",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )


@Client.on_callback_query(filters.regex("^ep_"))
async def on_episode_select(client: Client, callback_query):
    if not await check_fsub(client, callback_query.from_user.id):
        await callback_query.answer("🔒 ᴘʟᴇᴀꜱᴇ ᴊᴏɪɴ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ ꜰɪʀꜱᴛ!", show_alert=True)
        return await send_fsub_prompt(client, callback_query.message)

    ep_idx  = int(callback_query.data.split("_")[1])
    user_id = callback_query.from_user.id
    if user_id not in user_episodes:
        await callback_query.answer("❌ ꜱᴇꜱꜱɪᴏɴ ᴇxᴘɪʀᴇᴅ.")
        return

    page = ep_idx // 20
    buttons = [
        [
            InlineKeyboardButton("360ᴘ",  callback_data=f"dl_360_{ep_idx}"),
            InlineKeyboardButton("720ᴘ",  callback_data=f"dl_720_{ep_idx}"),
            InlineKeyboardButton("1080ᴘ", callback_data=f"dl_1080_{ep_idx}")
        ],
        [InlineKeyboardButton("ᴀᴜᴛᴏ (ʙᴇꜱᴛ)",    callback_data=f"dl_auto_{ep_idx}")],
        [InlineKeyboardButton("ᴀʟʟ ǫᴜᴀʟɪᴛɪᴇꜱ", callback_data=f"dl_all_{ep_idx}")],
        [
            InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data=f"eps_page_{page}"),
            InlineKeyboardButton("❌ ᴄʟᴏꜱᴇ", callback_data="cancel")
        ]
    ]
    try:
        await callback_query.edit_message_caption(
            caption=f"<blockquote>📥 <b>ᴅᴏᴡɴʟᴏᴀᴅ ᴇᴘɪꜱᴏᴅᴇ {ep_idx+1}</b>\nꜱᴇʟᴇᴄᴛ ǫᴜᴀʟɪᴛʏ:</blockquote>",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.HTML
        )
    except:
        await callback_query.edit_message_text(
            f"<blockquote>📥 <b>ᴅᴏᴡɴʟᴏᴀᴅ ᴇᴘɪꜱᴏᴅᴇ {ep_idx+1}</b>\nꜱᴇʟᴇᴄᴛ ǫᴜᴀʟɪᴛʏ:</blockquote>",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.HTML
        )
