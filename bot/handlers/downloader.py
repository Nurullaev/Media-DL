import asyncio
import re
import time

import yt_dlp
from aiogram import types


def format_time(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def format_bytes(size):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


class Downloader:
    def __init__(self, url: str, message: types.Message, download_dir: str = "."):
        self.message = message
        self.url = url
        self.download_dir = download_dir

        self.last_update_time = time.time()
        self.d = None
        self.loop = asyncio.get_running_loop()

    async def run(self) -> str:
        return await asyncio.to_thread(self.download_video, self.url)

    def progress_hook(self, d):
        if d["status"] == "downloading" and time.time() - self.last_update_time >= 3:
            self.last_update_time = time.time()
            self.loop.call_soon_threadsafe(asyncio.create_task, self.update_message(d))

    async def update_message(self, d):
        try:
            percent_str = d.get("_percent_str") or d.get("percent") or "0.0%"
            clean_percent_str = re.sub(r"\x1b\[[0-9;]*m", "", percent_str)
            percent = float(clean_percent_str.strip("%"))

            downloaded = d.get("downloaded_bytes", 0)
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            eta = d.get("eta", 0)

            bar_length = 20
            filled_blocks = int(round(bar_length * percent / 100))
            bar = f"[{'█' * filled_blocks}{'░' * (bar_length - filled_blocks)}]"

            text = f"<code>{self.url}</code>\n\n" f"{bar} {percent:.1f}%\n" f"💾 {format_bytes(downloaded)} / {format_bytes(total)}\n" f"⏳ Remaining: {format_time(eta)}"

            await self.message.edit_text(text=text)
        except Exception:
            pass  # transient: "message is not modified", message deleted, flood-wait — safe to ignore

    def download_video(self, url: str) -> str:
        opts = {
            # Prefer H.264/AAC (plays inline in Telegram; VP9/AV1 in mp4 shows as image+sound).
            # No height cap: it would wrongly throttle vertical Shorts (their height is ~1920).
            "format": "bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo+bestaudio/best",
            "format_sort": ["vcodec:h264", "res:1080", "acodec:m4a"],
            "merge_output_format": "mp4",
            "remote_components": ["ejs:github"],
            "paths": {"home": self.download_dir},
            "quiet": True,
            "progress_hooks": [self.progress_hook],
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # After merge/postprocessing the real path lives here; fall back to prepare_filename.
            try:
                filename = info["requested_downloads"][0]["filepath"]
            except (KeyError, IndexError, TypeError):
                filename = ydl.prepare_filename(info)
            return filename, (info.get("width"), info.get("height"))
