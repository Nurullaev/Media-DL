# Media DL

Telegram bot for downloading videos & shorts from YouTube (+ Shorts), TikTok,
Instagram Reels, X (Twitter), VK, OK.ru, Rutube, Dzen, Reddit, Pinterest,
Vimeo, Dailymotion, Twitch clips, Likee, Coub and more.

## Requirements
- Python 3.8+
- ffmpeg
- deno — for reliable YouTube HD (nsig solving)

## Installation
```bash
git clone https://github.com/Nurullaev/Media-DL.git
cd Media-DL/bot

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration
```bash
cp .env.example .env
```
Edit `.env` and set `TOKEN` (get it from [@BotFather](https://t.me/BotFather)).

`DL_*` variables are optional — they enable serving files larger than
Telegram's 50 MB limit via an external host (file self-deletes after the
first download). Leave them empty to disable.

## Run
```bash
python main.py
```
