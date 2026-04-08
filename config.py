#@cantarellabots
import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.environ.get("API_ID", 22419004))
API_HASH = os.environ.get("API_HASH", "34982b52c4a83c2af3ce8f4fe12fe4e1")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8732170391:AAHIm0_xvUCjePzRegZaK6crL_Pxdpaa9no")

SET_INTERVAL = int(os.environ.get("SET_INTERVAL", 60))  # in seconds, default 1 hour
TARGET_CHAT_ID = os.environ.get("TARGET_CHAT_ID", "-1003741006721")
MAIN_CHANNEL = os.environ.get("MAIN_CHANNEL", "-1003741006721") # Change as needed
LOG_CHANNEL = os.environ.get("LOG_CHANNEL", "-1003703944362")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb+srv://mrnoobx:DAZCdTczVWyECi04@cluster0.sedgwxy.mongodb.net/?retryWrites=true&w=majority")
MONGO_NAME = os.environ.get("MONGO_NAME", "cantarellabots")
OWNER_ID = int(os.environ.get("OWNER_ID", "8565045255"))
ADMIN_URL = os.environ.get("ADMIN_URL", "@cdn_obita")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "@noob_animeworld_bot")
FSUB_PIC = os.environ.get("FSUB_PIC", "https://files.catbox.moe/3fyfxh.jpg")
FSUB_LINK_EXPIRY = int(os.environ.get("FSUB_LINK_EXPIRY", 600))
START_PIC =os.environ.get("START_PIC", "https://files.catbox.moe/4b8jvw.jpg")

# ─── Filename & Caption Formats ───
FORMAT = os.environ.get("FORMAT", "[S{season}-E{episode}] {title} [{quality}] [{audio}]")
CAPTION = os.environ.get("CAPTION", "[ @cdn_obita {FORMAT}]")

# ─── Progress Bar Settings ───
PROGRESS_BAR = os.environ.get("PROGRESS_BAR", """
<blockquote> {bar} </blockquote>
<blockquote>📁 <b>{title}</b>
⚡ Speed: {speed}
📦 {current} / {total}</blockquote>
""")

# ─── Response Images ───
# Rotating anime images sent with every bot reply. Add as many as you like.
RESPONSE_IMAGES = [
    "https://files.catbox.moe/3fyfxh.jpg",
    "https://files.catbox.moe/9ufgme.jpg",
    "https://files.catbox.moe/4b8jvw.jpg",
    "https://files.catbox.moe/bli70r.jpg",
    "https://files.catbox.moe/uce0lw.jpg",
    "https://files.catbox.moe/is7q4q.jpg"
]
