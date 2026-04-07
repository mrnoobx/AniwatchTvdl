#@cantarellabots
from pyrogram.enums import ParseMode
from pyrogram import Client
#@cantarellabots
from pyrogram.types import InlineKeyboardMarkup, Message
from cantarella.button import Button as InlineKeyboardButton
from cantarella.core.anilist import TextEditor, CAPTION_FORMAT
from cantarella.core.utils import encode_data
from config import MAIN_CHANNEL, BOT_TOKEN
import re

async def post_to_main_channel(client: Client, anime_url: str, uploaded_messages: list, quality_map: dict, batch_ep_range: str = None):
    """
    Creates a post in the MAIN_CHANNEL with AniList metadata and quality buttons.
    uploaded_messages: list of Pyrogram Message objects that were uploaded to TARGET_CHAT_ID.
    quality_map: { '720p': msg_id, '1080p': msg_id, ... }
    batch_ep_range: str, if provided, sets ep_no to this value (e.g., '1-25')
    """
    if not MAIN_CHANNEL:
        return

    # 1. Fetch metadata
    # We need a name to search on AniList. Let's try to extract it from the anime_url or first message title.
    sample_title = "Anime"
    if uploaded_messages:
        # Example title: [S1 - E1] Episode Title [720p] [Dual Audio]
        match = re.search(r'\] (.*?) \[', uploaded_messages[0].caption or "")
        if match:
            sample_title = match.group(1)
        elif uploaded_messages[0].document and uploaded_messages[0].document.file_name:
            match = re.search(r'\] (.*?) \[', uploaded_messages[0].document.file_name)
            if match:
                sample_title = match.group(1)

    te = TextEditor(sample_title)
    await te.load_anilist()
    data = te.adata

    # 2. Format Caption
    # CAPTION_FORMAT: title, anime_season, ep_no, audio, status, t_eps, genres
    # User requested ONLY English name where possible
    title = data.get('title', {}).get('english') or data.get('title', {}).get('romaji') or sample_title
    status = data.get('status', 'Unknown')
    t_eps = data.get('episodes', 'Unknown')
    genres = ", ".join(data.get('genres', [])) or "Unknown"

    # Try to get season and ep_no from the first message
    anime_season = "1"
    ep_no = batch_ep_range if batch_ep_range else "1"

    audio = "Dual Audio"
    if uploaded_messages:
        m = re.search(r'\[S(\d+) - E(\d+)\]', uploaded_messages[0].caption or "")
        if m:
            anime_season = m.group(1)
            if not batch_ep_range:
                ep_no = m.group(2)
        if "JP" in (uploaded_messages[0].caption or ""):
            audio = "Japanese"
        elif "EN" in (uploaded_messages[0].caption or ""):
            audio = "English"

    caption = CAPTION_FORMAT.format(
        title=title,
        anime_season=anime_season,
        ep_no=ep_no,
        audio=audio,
        status=status,
        t_eps=t_eps,
        genres=genres
    )

    # 3. Create Quality Buttons
    # Each button will be a deep link: t.me/bot?start=base64(msgid_chatid)
    bot_username = (await client.get_me()).username
    buttons = []

    row = []
    for q_label, msg_id in quality_map.items():
        # Encode msg_id and chat_id (TARGET_CHAT_ID)
        chat_id = uploaded_messages[0].chat.id
        payload = encode_data(f"{msg_id}_{chat_id}")
        url = f"https://t.me/{bot_username}?start={payload}"
        row.append(InlineKeyboardButton(q_label, url=url))

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    # 4. Send to Main Channel
    poster = await te.get_poster()
    try:
        await client.send_photo(
            chat_id=int(MAIN_CHANNEL),
            photo=poster,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        print(f"Error posting to main channel: {e}")
