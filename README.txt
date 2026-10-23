# TOSHIRO Chinese Translator (Telegram)

Features:
- Type English or Bisaya text; translate to Simplified Chinese
- Show Chinese characters and pinyin
- Send Mandarin pronunciation audio
- Accept Telegram voice messages (English speech recognition is the default)

## Create your Telegram bot
1. Open https://t.me/BotFather
2. Send `/newbot`.
3. Set the display name to `TOSHIRO Chinese Translator`.
4. Choose an available username ending in `bot`, such as `ToshiroChineseTranslatorBot` if available.
5. Copy the token privately. Do NOT send it to anyone or post it in chat.

## Run on a Python host
1. Upload `bot.py` and `requirements.txt`.
2. Install packages: `pip install -r requirements.txt`
3. Install FFmpeg on the server (needed for voice messages).
4. Add an environment variable/secret named `TELEGRAM_BOT_TOKEN` with your BotFather token.
5. Start command: `python bot.py`
6. Open your bot in Telegram and send `/start`.

## Important notes
- Translation uses the unofficial Google Translate interface via `deep-translator`; it can be rate-limited or change.
- gTTS uses Google's text-to-speech service and needs internet access.
- Speech recognition uses Google's web speech recognition and defaults to Philippine English (`en-PH`). It may not understand Bisaya voice reliably; typing Bisaya may work better.
- The hosting provider must allow a persistent Python process and outbound internet. A free host may sleep or stop the bot.
- Never put the bot token directly in public code or share it. If exposed, revoke it through BotFather.
