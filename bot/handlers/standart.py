import asyncio
import os
import random
import uuid

import shutil
import subprocess
import tempfile
from aiogram import F, Router, types
from aiogram.filters import Command
from dotenv import load_dotenv

from enums import Links
from handlers.downloader import Downloader

router = Router()

load_dotenv()
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))


def publish(user_id: int, filename: str) -> str:
    """Upload a too-large video to the dl host via scp and return its public URL.
    The file self-deletes on the host after the first full download."""
    base_url = os.getenv("DL_BASE_URL", "").rstrip("/")
    host = os.getenv("DL_SSH_HOST", "")
    user = os.getenv("DL_SSH_USER", "")
    remote_dir = os.getenv("DL_REMOTE_DIR", "")
    key = os.getenv("DL_SSH_KEY", "")

    ext = os.path.splitext(filename)[1] or ".mp4"
    remote_name = f"{uuid.uuid4().hex}{ext}"
    remote_path = f"{remote_dir}/{remote_name}"
    ssh_opts = ["-i", key, "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=20"]

    subprocess.run(["scp", "-q", *ssh_opts, filename, f"{user}@{host}:{remote_path}"], check=True, timeout=1800)
    subprocess.run(["ssh", *ssh_opts, f"{user}@{host}", f"chmod 644 {remote_path}"], check=True, timeout=60)
    return f"{base_url}/{remote_name}"


@router.message(F.text.startswith(tuple(Links.STANDART.value)))
async def handle_download(message: types.Message):
    # prepare
    await message.react([types.reaction_type_emoji.ReactionTypeEmoji(emoji="👀")])
    caption = f"<b><i><a href='https://t.me/NurVPN'>Nur VPN</a></i></b>"
    msg = await message.answer(f"<code>{message.text}</code>\n\nYour download will start soon.")

    tmpdir = tempfile.mkdtemp(prefix="ytdl_")
    downloader = Downloader(message.text, msg, tmpdir)
    success = False
    try:
        # download
        try:
            video_path, (width, height) = await downloader.run()
        except Exception as e:
            await message.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"❗ <code>{message.text}</code>\n\n{e}")
            await msg.edit_text(f"<code>{message.text}</code>\n\n⚠️ An error occurred during download. This usually happens because the video is age-restricted (18+) or unavailable in the hosting country.")
            return

        # send
        try:
            await message.answer_video(types.FSInputFile(video_path), caption=caption, width=width, height=height)
        except Exception as e:
            await msg.edit_text(f"<code>{message.text}</code>\n\n⏳ The video is too large for Telegram. Uploading to file host...")
            try:
                filebin_url = await asyncio.to_thread(publish, message.from_user.id, video_path)
                await msg.edit_text(f"{filebin_url}\n\n⚠️ The link works for a single download.\n\n{caption}")
                await message.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"<code>{filebin_url}</code>")
            except Exception as e:
                await msg.edit_text("😔 Upload failed. Please try again a bit later.")

        # log
        await message.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"✅ <code>{message.text}</code>")
        await message.delete()
        await msg.delete()
        success = True
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    # Promote my telegram channel (only after a successful run)
    if success and random.randint(1, 5) == 1:
        promo_msg = await message.answer("Hi! I'm <b>@NurVPN</b> — completely free, no ads, no mandatory subscriptions. If you like my work, check out my <b><a href='https://t.me/NurVPN'>Telegram news channel</a></b> — it’s a big support! 😊\n\n<b>This message will self-delete in 15 seconds</b>")
        await asyncio.sleep(15)
        await promo_msg.delete()
