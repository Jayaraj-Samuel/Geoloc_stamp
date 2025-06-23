import os
import logging
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# === CONFIG ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "your-token-here")
OVERLAY_PATH = "overlay.png"
FONT_PATH = "fonts/DejaVuSans.ttf"
IMAGE_SIZE = (2449, 3265)
FONT_SIZE_LARGE = 46
FONT_SIZE_SMALL = 40
TEXT_COLOR = (255, 255, 255)
TEXT_POSITION = (60, 3180)  # left, from bottom
LINE_SPACING = 48
TRANSPARENCY = 227  # 0-255 → 227 ≈ 89%

# === LOGGING ===
logging.basicConfig(
    format="%(asctime)s — %(levelname)s — %(message)s", level=logging.INFO
)

# === START COMMAND ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Send a photo.\n📝 Then send the GPS text to add.")

# === PHOTO HANDLER ===
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    photo_file = await photo.get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    context.user_data["photo"] = photo_bytes
    await update.message.reply_text("✅ Photo received. Now send the GPS text.")

# === TEXT HANDLER ===
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "photo" not in context.user_data:
        await update.message.reply_text("⚠️ Please send a photo first.")
        return

    text = update.message.text
    base_img = Image.open(BytesIO(context.user_data["photo"])).convert("RGBA")

    # Overlay
    overlay = Image.open(OVERLAY_PATH).convert("RGBA")
    overlay.putalpha(TRANSPARENCY)
    base_img.alpha_composite(overlay)

    # Draw text
    draw = ImageDraw.Draw(base_img)
    try:
        font_large = ImageFont.truetype(FONT_PATH, FONT_SIZE_LARGE)
        font_small = ImageFont.truetype(FONT_PATH, FONT_SIZE_SMALL)
    except Exception as e:
        logging.warning("❗ Font load failed: %s", e)
        font_large = font_small = ImageFont.load_default()

    # Draw lines with slight left offset and spacing
    lines = text.splitlines()
    x, y = TEXT_POSITION
    for i, line in enumerate(lines):
        font = font_large if i == 0 else font_small
        draw.text((x, y + i * LINE_SPACING), line, font=font, fill=TEXT_COLOR, spacing=5)

    # Send result
    buf = BytesIO()
    base_img.convert("RGB").save(buf, format="JPEG")
    buf.seek(0)

    await update.message.reply_photo(photo=InputFile(buf), caption="✅ GPS-stamped!")
    del context.user_data["photo"]

# === MAIN FUNCTION ===
def main():
    print("🚀 Starting bot...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("✅ Bot is live and polling!")
    app.run_polling()

if __name__ == "__main__":
    main()
