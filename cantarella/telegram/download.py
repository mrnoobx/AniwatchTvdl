#@cantarellabots
from pyrogram.enums import ParseMode
from pyrogram import Client
from queue import Queue, Empty
from threading import Thread
import asyncio
import os
import time
from cantarella.scraper.cantarellatv import cantarellatvDownloader
from cantarella.core.utils import is_video_file
from cantarella.core.images import get_random_image
from cantarella.core.database import db
from config import LOG_CHANNEL


async def schedule_deletion(client: Client, chat_id: int, message_id: int, delay: int, notify_msg_id: int = None):
    """Wait for 'delay' seconds, then delete the specified message(s)."""
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id, message_id)
        if notify_msg_id:
            await client.delete_messages(chat_id, notify_msg_id)
    except Exception:
        pass


# Global semaphores to limit concurrent tasks and prevent resource conflicts
download_semaphore = asyncio.Semaphore(1)
upload_semaphore = asyncio.Semaphore(1)


def _make_progress_bar(percent: float, length: int = 10) -> str:
    """Generate a visual progress bar string."""
    filled = int(length * percent / 100)
    empty = length - filled
    bar = "●" * filled + "○" * empty
    return f"[{bar}] {percent:.1f}%"


async def _handle_download(client: Client, message, url, status_msg, is_playlist=False, quality="auto", chat_id=None, name_override=None, season_override=None, ep_num_override=None):
    if chat_id is None:
        chat_id = message.chat.id if message else status_msg.chat.id

    # The user's original chat for user-side progress
    user_chat_id = message.chat.id if message else None

    # Progress is always reported in LOG_CHANNEL if set, otherwise original chat_id
    progress_chat_id = int(LOG_CHANNEL) if LOG_CHANNEL else chat_id

    # If the request didn't come from LOG_CHANNEL, create a new status message there

    if status_msg.chat.id != progress_chat_id:
        status_msg = await client.send_message(progress_chat_id, f"<blockquote>🔄 ꜱᴛᴀʀᴛɪɴɢ ᴘʀᴏᴄᴇꜱꜱ ғᴏʀ: {url}</blockquote>", parse_mode=ParseMode.HTML)

    # ── Create a user-side progress message ──
    user_progress_msg = None
    if user_chat_id:
        try:
            user_progress_msg = await client.send_message(
                user_chat_id,
                text=f"<blockquote>⏳ <b><i>ʏᴏᴜʀ ᴅᴏᴡɴʟᴏᴀᴅ ɪꜱ ǫᴜᴇᴜᴇᴅ...</i></b>\n\n<b>{name_override or 'Anime Episode'}</b>\nǫᴜᴀʟɪᴛʏ: {quality}</blockquote>",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass


    # Inform the user if the task is waiting in the queue
    if download_semaphore.locked():
        try:
            await client.edit_message_text(progress_chat_id, status_msg.id, f"<blockquote>⏳ **ᴡᴀɪᴛɪɴɢ ɪɴ ǫᴜᴇᴜᴇ...**\nᴀɴɪᴍᴇ: {name_override or url}\nǫᴜᴀʟɪᴛʏ: {quality}</blockquote>", parse_mode=ParseMode.HTML)
        except Exception:
            pass
        if user_progress_msg:
            try:
                await client.edit_message_text(
                    user_chat_id, user_progress_msg.id,
                    f"<blockquote>⏳ <b><i>ᴡᴀɪᴛɪɴɢ ɪɴ ǫᴜᴇᴜᴇ...</i></b>\n\n{_make_progress_bar(0)}\n\n<b>{name_override or 'Anime Episode'}</b>\nǫᴜᴀʟɪᴛʏ: {quality}</blockquote>",
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass

    async with download_semaphore:
        try:
            await client.edit_message_text(progress_chat_id, status_msg.id, f"<blockquote>🔄 **ᴘʀᴏᴄᴇꜱꜱɪɴɢ ꜱᴛᴀʀᴛᴇᴅ...**\nᴀɴɪᴍᴇ: {name_override or url}</blockquote>", parse_mode=ParseMode.HTML)
        except Exception:
            pass
        return await __handle_download_internal(client, message, url, status_msg, is_playlist, quality, chat_id, progress_chat_id, name_override, season_override, ep_num_override, user_chat_id, user_progress_msg)


async def __handle_download_internal(client: Client, message, url, status_msg, is_playlist, quality, chat_id, progress_chat_id, name_override, season_override, ep_num_override, user_chat_id, user_progress_msg):
    progress_q = Queue()
    upload_q = Queue()
    downloader = cantarellatvDownloader(progress_queue=progress_q)

    def download_target():
        if is_playlist and quality != "all":
            downloader.download_all_episodes(url, quality=quality)
        else:
            downloader.download_episode(url, quality=quality, name_override=name_override, season_override=season_override, ep_num_override=ep_num_override)

    thread = Thread(target=download_target)
    thread.start()

    uploaded_messages = []
    active_uploads = [0]
    error = [None]

    async def do_upload(filename, title):
        last_up_time = [time.time()]
        last_up_size = [0]

        def up_cb(current, total):
            now = time.time()
            diff_time = now - last_up_time[0]
            if diff_time >= 2:
                diff_size = current - last_up_size[0]
                speed_mb = (diff_size / diff_time / 1024 / 1024)
                percent = (current / total) * 100

                def format_size(b):
                    for unit in ['B', 'KB', 'MB', 'GB']:
                        if b < 1024: return f"{b:.1f} {unit}"
                        b /= 1024
                    return f"{b:.1f} TB"

                upload_q.put({
                    'uploading': {
                        'percent': round(percent, 1),
                        'speed': f"{speed_mb:.1f} MB/s",
                        'title': title,
                        'current': format_size(current),
                        'total': format_size(total)
                    }
                })
                last_up_time[0] = now
                last_up_size[0] = current

        try:
            async with upload_semaphore:
                # Add explicit file_name so Telegram does not infer weird numeric names
                ext = os.path.splitext(filename)[1] or ".mkv"
                actual_file_name = f"{title}{ext}"

                # Try to use CAPTION config format if possible
                file_caption = ""
                try:
                    from config import CAPTION
                    file_caption = CAPTION.replace("{FORMAT}", title)
                except Exception:
                    file_caption = title

                thumb_path = "thumb.jpg" if os.path.exists("thumb.jpg") else None

                up_msg = await client.send_document(
                    chat_id,
                    document=filename,
                    file_name=actual_file_name,
                    thumb=thumb_path,
                    caption=file_caption,
                    progress=up_cb
                )
                uploaded_messages.append(up_msg)
                upload_q.put({'uploaded': True})

                # --- Auto-Delete Logic for User PM ---
                # Check if this is a private chat (user PM)
                try:
                    chat = await client.get_chat(chat_id)
                    if chat.type == "private":
                        autodel_time = await db.get_user_setting(chat_id, "autodel_time", 0)
                        if autodel_time > 0:

                            mins = autodel_time // 60
                            notify_msg = await client.send_message(
                                chat_id,
                                f"<blockquote>🗑️ <b>ᴛʜɪꜱ ғɪʟᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ᴀғᴛᴇʀ {mins} ᴍɪɴ ({autodel_time}ꜱ).</b>\n"
                                "<i>ᴍᴀᴋᴇ ꜱᴜʀᴇ ᴛᴏ ꜱᴀᴠᴇ ɪᴛ ɪɴ ʏᴏᴜʀ 'ꜱᴀᴠᴇᴅ ᴍᴇꜱꜱᴀɢᴇꜱ' ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴋᴇᴇᴘ ɪᴛ!</i></blockquote>",
                                reply_to_message_id=up_msg.id,
                                parse_mode=ParseMode.HTML
                            )
                            asyncio.create_task(schedule_deletion(client, chat_id, up_msg.id, autodel_time, notify_msg.id))
                except Exception:
                    pass

        except Exception as e:

            upload_q.put({'upload_error': str(e)})
            try:
                await client.send_message(progress_chat_id, f"<blockquote>❌ ᴜᴘʟᴏᴀᴅ ғᴀɪʟᴇᴅ ғᴏʀ {title}: {str(e)}</blockquote>", parse_mode=ParseMode.HTML)
            except Exception:
                pass
        finally:
            active_uploads[0] -= 1
            try:
                os.unlink(filename)
            except:
                pass

    async def monitor():
        current_episode_title = "Unknown"
        last_text = ""
        last_edit_time = 0
        last_user_edit_time = 0
        last_user_text = ""
        dl_status = {'sub': None, 'dub': None}

        while thread.is_alive() or not progress_q.empty() or not upload_q.empty() or active_uploads[0] > 0:
            text = None
            user_text = None

            while not progress_q.empty():
                try:
                    info = progress_q.get_nowait()
                    if 'error' in info:
                        error[0] = info['error']
                        if active_uploads[0] > 0:
                            text = f"<blockquote>⚠️ **ᴅᴏᴡɴʟᴏᴀᴅ ᴇʀʀᴏʀ:** {info['error']}\n📤 ᴡᴀɪᴛɪɴɢ ғᴏʀ {active_uploads[0]} ᴜᴘʟᴏᴀᴅ(ꜱ) ᴛᴏ ғɪɴɪꜱʜ...</blockquote>"
                            user_text = f"<blockquote>⚠️ <b><i>ᴅᴏᴡɴʟᴏᴀᴅ ᴇʀʀᴏʀ</i></b>\n📤 ᴡᴀɪᴛɪɴɢ ғᴏʀ ᴜᴘʟᴏᴀᴅꜱ ᴛᴏ ғɪɴɪꜱʜ...</blockquote>"
                        continue
                    if 'status' in info:
                        text = info['status']
                    elif 'finished' in info:
                        dl_status = {'sub': None, 'dub': None}
                        filename = info['filename']
                        title = info['title']
                        current_episode_title = title
                        if is_video_file(filename):
                            active_uploads[0] += 1
                            text = f"<blockquote>📤 **ᴅᴏᴡɴʟᴏᴀᴅ ᴄᴏᴍᴘʟᴇᴛᴇ!**\nꜱᴛᴀʀᴛɪɴɢ ᴜᴘʟᴏᴀᴅ: {title}...</blockquote>"
                            user_text = (
                                f"<blockquote>📤 <b><i>ᴅᴏᴡɴʟᴏᴀᴅ ᴄᴏᴍᴘʟᴇᴛᴇ!</i></b>\n\n"
                                f"{_make_progress_bar(100)}\n\n"
                                f"📁 <b>{title}</b>\n⬆️ ꜱᴛᴀʀᴛɪɴɢ ᴜᴘʟᴏᴀᴅ...</blockquote>"
                            )
                            task = asyncio.create_task(do_upload(filename, title))
                            task.set_name(f"upload_{title}")
                    elif 'percent' in info:
                        dl_type = info.get('type', 'sub')
                        dl_status[dl_type] = info
                        current_episode_title = info.get('title', current_episode_title)

                        primary = dl_status['sub'] or dl_status['dub']
                        if primary:
                            try:
                                pct = float(str(primary['percent']).replace('%', ''))
                            except:
                                pct = 0

                            from config import PROGRESS_BAR
                            bar_str = PROGRESS_BAR.format(
                                bar=_make_progress_bar(pct),
                                title=current_episode_title,
                                speed=primary['speed'],
                                current=primary['downloaded'],
                                total=primary['total']
                            )

                            user_text = (
                                f"<blockquote>📥 <b><i>ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ...</i></b>\n"
                                f"{bar_str}</blockquote>"
                            )
                            # Update LOG_CHANNEL to use exactly the same visual progress
                            text = (
                                f"<blockquote>📥 <b><i>ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ...</i></b>\n"
                                f"{bar_str}</blockquote>"
                            )
                except Empty:
                    break

            # Only break on error if there are NO active uploads left
            if error[0] and active_uploads[0] <= 0 and progress_q.empty():
                break

            while not upload_q.empty():
                try:
                    info = upload_q.get_nowait()
                    if 'uploaded' in info:
                        text = f"<blockquote>📤 **ᴜᴘʟᴏᴀᴅᴇᴅ {len(uploaded_messages)} ᴇᴘɪꜱᴏᴅᴇ(ꜱ)**\nᴡᴀɪᴛɪɴɢ ғᴏʀ ɴᴇxᴛ...</blockquote>"
                        user_text = (
                            f"<blockquote>✅ <b><i>ᴜᴘʟᴏᴀᴅᴇᴅ {len(uploaded_messages)} ғɪʟᴇ(ꜱ)!</i></b>\n"
                            f"{_make_progress_bar(100)}\n\n"
                            f"⏳ ᴡᴀɪᴛɪɴɢ ғᴏʀ ɴᴇxᴛ ᴛᴀꜱᴋ...</blockquote>"
                        )
                    elif 'uploading' in info:
                        up = info['uploading']
                        from config import PROGRESS_BAR
                        bar_str = PROGRESS_BAR.format(
                            bar=_make_progress_bar(up['percent']),
                            title=up['title'],
                            speed=up['speed'],
                            current=up.get('current', '?'),
                            total=up.get('total', '?')
                        )

                        user_text = (
                            f"<blockquote>📤 <b><i>ᴜᴘʟᴏᴀᴅɪɴɢ...</i></b>\n"
                            f"{bar_str}</blockquote>"
                        )
                        text = (
                            f"<blockquote>📤 <b><i>ᴜᴘʟᴏᴀᴅɪɴɢ...</i></b>\n"
                            f"{bar_str}</blockquote>"
                        )
                    elif 'upload_error' in info:
                        text = f"<blockquote>⚠️ ᴜᴘʟᴏᴀᴅ ᴇʀʀᴏʀ: {info['upload_error']}</blockquote>"
                        user_text = f"<blockquote>⚠️ <b><i>ᴜᴘʟᴏᴀᴅ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ</i></b></blockquote>"
                except Empty:
                    break

            now = time.time()

            # Update LOG_CHANNEL

            if text and text != last_text and (now - last_edit_time) > 2.5:
                try:
                    await client.edit_message_text(progress_chat_id, status_msg.id, text, parse_mode=ParseMode.HTML)
                    last_text = text
                    last_edit_time = now
                except Exception:
                    pass

            # Update user-side progress text
            if user_progress_msg and user_text and user_text != last_user_text and (now - last_user_edit_time) > 3:
                try:
                    await client.edit_message_text(
                        user_chat_id, user_progress_msg.id,
                        user_text,
                        parse_mode=ParseMode.HTML
                    )
                    last_user_text = user_text
                    last_user_edit_time = now
                except Exception:
                    pass

            await asyncio.sleep(0.5)
        thread.join()

    await monitor()

    # ── Final status updates ──

    if uploaded_messages:
        unit = 'episode(s)' if is_playlist else 'file(s)'
        unit_sc = unit
        suffix = ""
        if error[0]:
            suffix = f"\n⚠️ ɴᴏᴛᴇ: ᴅᴏᴡɴʟᴏᴀᴅ ʜᴀᴅ ᴇʀʀᴏʀꜱ ʙᴜᴛ {len(uploaded_messages)} {unit_sc} ᴡᴇʀᴇ ꜱᴀᴠᴇᴅ."
        try:
            await client.edit_message_text(
                progress_chat_id, status_msg.id,
                f"<blockquote>✅ **ᴅᴏᴡɴʟᴏᴀᴅ & ᴜᴘʟᴏᴀᴅ ᴄᴏᴍᴘʟᴇᴛᴇ!**\nᴜᴘʟᴏᴀᴅᴇᴅ {len(uploaded_messages)} {unit_sc} ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ.{suffix}</blockquote>",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass
        # User-side final
        if user_progress_msg:
            try:
                await client.edit_message_text(
                    user_chat_id, user_progress_msg.id,
                    f"<blockquote>✅ <b><i>ᴀʟʟ ᴅᴏɴᴇ!</i></b>\n\n"
                    f"{_make_progress_bar(100)}\n\n"
                    f"📦 ᴜᴘʟᴏᴀᴅᴇᴅ <b>{len(uploaded_messages)} {unit_sc}</b> ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ!{suffix}</blockquote>",
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass
    elif error[0]:
        try:
            await client.edit_message_text(progress_chat_id, status_msg.id, f"<blockquote>❌ ᴅᴏᴡɴʟᴏᴀᴅ ᴇʀʀᴏʀ: {error[0]}</blockquote>", parse_mode=ParseMode.HTML)
        except Exception:
            pass
        if user_progress_msg:
            try:
                await client.edit_message_text(
                    user_chat_id, user_progress_msg.id,
                    f"<blockquote>❌ <b><i>ᴅᴏᴡɴʟᴏᴀᴅ ғᴀɪʟᴇᴅ</i></b>\n\n{error[0]}</blockquote>",
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass
    else:
        try:
            await client.edit_message_text(progress_chat_id, status_msg.id, "<blockquote>❌ ɴᴏ ғɪʟᴇꜱ ᴡᴇʀᴇ ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ ᴜᴘʟᴏᴀᴅᴇᴅ.</blockquote>", parse_mode=ParseMode.HTML)
        except Exception:
            pass
        if user_progress_msg:
            try:
                await client.edit_message_text(
                    user_chat_id, user_progress_msg.id,
                    "<blockquote>❌ <b><i>ɴᴏ ғɪʟᴇꜱ ᴡᴇʀᴇ ᴜᴘʟᴏᴀᴅᴇᴅ.</i></b></blockquote>",
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass

    return uploaded_messages
