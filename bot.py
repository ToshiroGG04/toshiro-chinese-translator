import os
import logging
import tempfile
import subprocess
import time
from pathlib import Path
from functools import lru_cache

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from deep_translator import GoogleTranslator
from pypinyin import pinyin, Style
from gtts import gTTS
import speech_recognition as sr


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


def make_pinyin(chinese_text: str) -> str:
    words = pinyin(
        chinese_text,
        style=Style.TONE,
        errors=lambda chars: list(chars),
    )
    return " ".join(item[0] for item in words)


@lru_cache(maxsize=500)
def _translate_cached(text: str) -> str:
    return GoogleTranslator(
        source="auto",
        target="zh-CN",
    ).translate(text)


def translate_to_chinese(text: str) -> str:
    text = text.strip()

    for attempt in range(3):
        try:
            result = _translate_cached(text)

            if not result:
                raise ValueError("Walay translation result")

            return result

        except Exception as exc:
            error_name = type(exc).__name__.lower()
            error_text = str(exc).lower()

            limited = (
                "toomanyrequests" in error_name
                or "429" in error_text
                or "too many requests" in error_text
            )

            if not limited or attempt == 2:
                raise

            # Retry after a short delay if the service is rate-limited.
            time.sleep(2 ** (attempt + 1))

    raise RuntimeError("Napakyas ang translation.")


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = (
        "👋 Welcome sa TOSHIRO Chinese Translator! 🇨🇳\n\n"
        "I-type ang English o Bisaya sentence aron i-translate "
        ngadto sa Chinese.\n"
        "Pwede usab magpadala og English voice message.\n\n"
        "Example: Hi, how are you?\n\n"
        "Commands:\n"
        "/start - Sugod\n"
        "/help - Tabang"
    )
    await update.message.reply_text(message)


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "📝 I-type ang sentence nga gusto nimo i-translate.\n"
        "🇨🇳 Makadawat ka og Chinese characters ug pinyin.\n"
        "🔊 Magpadala usab ang bot og Chinese pronunciation audio.\n"
        "🎙️ Pwede magpadala og English voice message.\n\n"
        "Pahinumdom: Ang Bisaya voice recognition mahimong dili sakto."
    )


async def send_translation(update: Update, text: str):
    if not text or not text.strip():
        await update.message.reply_text(
            "Palihog pag-type o pagsulti og sentence."
        )
        return

    try:
        chinese = translate_to_chinese(text.strip())
        py = make_pinyin(chinese)

        response = (
            f"🇨🇳 Chinese (简体中文):\n{chinese}\n\n"
            f"🔤 Pinyin:\n{py}\n\n"
            f"🗣️ Original:\n{text.strip()}"
        )

        await update.message.reply_text(response)

        audio_path = None

        try:
            with tempfile.NamedTemporaryFile(
                suffix=".mp3",
                delete=False,
            ) as audio:
                audio_path = audio.name

            gTTS(text=chinese, lang="zh-CN").save(audio_path)

            with open(audio_path, "rb") as audio_file:
                await update.message.reply_audio(
                    audio=audio_file,
                    title="TOSHIRO Chinese Pronunciation",
                    caption="🔊 Chinese pronunciation (普通话)",
                )

        finally:
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)

    except Exception as exc:
        log.exception("Translation failed")
        await update.message.reply_text(
            "Pasayloa, napakyas ang translation karon.\n"
            "Sulayi pag-usab unya.\n"
            f"Error: {type(exc).__name__}"
        )


async def text_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if update.message and update.message.text:
        await send_translation(update, update.message.text)


async def voice_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    status = await update.message.reply_text(
        "🎙️ Gipaminaw nako imong voice message..."
    )

    ogg_path = None
    wav_path = None

    try:
        voice = update.message.voice
        telegram_file = await context.bot.get_file(voice.file_id)

        with tempfile.NamedTemporaryFile(
            suffix=".ogg",
            delete=False,
        ) as audio_file:
            ogg_path = audio_file.name

        await telegram_file.download_to_drive(ogg_path)

        wav_path = str(Path(ogg_path).with_suffix(".wav"))

        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                ogg_path,
                "-ar",
                "16000",
                "-ac",
                "1",
                wav_path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=45,
        )

        if result.returncode != 0:
            raise RuntimeError("FFmpeg conversion failed")

        recognizer = sr.Recognizer()

        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)

        spoken_text = recognizer.recognize_google(
            audio_data,
            language="en-PH",
        )

        await status.edit_text(
            f"🗣️ Nadungog nako: {spoken_text}"
        )

        await send_translation(update, spoken_text)

    except sr.UnknownValueError:
        await status.edit_text(
            "Wala nako masabti ang imong tingog.\n"
            "Sulayi og klaro nga English voice message "
            "o i-type lang ang sentence."
        )

    except sr.RequestError:
        await status.edit_text(
            "Dili ma-access ang speech recognition karon. "
            "Sulayi pag-usab."
        )

    except FileNotFoundError:
        await status.edit_text(
            "Wala ang FFmpeg sa server. Kinahanglan kini "
            "aron maproseso ang voice messages."
        )

    except Exception as exc:
        log.exception("Voice processing failed")
        await status.edit_text(
            f"Naay problema sa voice processing: {type(exc).__name__}"
        )

    finally:
        for path in (ogg_path, wav_path):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass


def main():
    if not TOKEN:
        raise RuntimeError(
            "Wala makita ang TELEGRAM_BOT_TOKEN. "
            "Ibutang ang bot token sa hosting Environment Variables."
        )

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.VOICE, voice_message))
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_message,
        )
    )

    log.info("TOSHIRO Chinese Translator is starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
