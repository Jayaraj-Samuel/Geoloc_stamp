import os
import logging
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Logging
logging.basicConfig(format="%(asctime)s — %(levelname)s — %(message)s", level=logging.INFO)

# Constants
FONT_PATH = "fonts/DejaVuSans.ttf"
OVERLAY_PATH = "overlay.png"

# Text handler
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["gps_text"] = update.message.text.strip()
    await update.message.reply_text("✅ Location text received. Now send a photo.")

# Photo handler
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gps_text = context.user_data.get("gps_text")
    if not gps_text:
        await update.message.reply_text("❗ First, send the GPS location text.")
        return

    photo = update.message.photo[-1]
    photo_file = await photo.get_file()
    photo_bytes = BytesIO()
    await photo_file.download(out=photo_bytes)
    photo_bytes.seek(0)

    # Load and convert base image
    base = Image.open(photo_bytes).convert("RGBA")

    # Load and apply overlay with 89% transparency
    overlay = Image.open(OVERLAY_PATH).convert("RGBA")
    overlay.putalpha(int(255 * 0.89))
    combined = Image.alpha_composite(base, overlay)

    # Prepare to draw text
    draw = ImageDraw.Draw(combined)
    try:
        font_big = ImageFont.truetype(FONT_PATH, 54)
        font_small = ImageFont.truetype(FONT_PATH, 42)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Font error: {e}")
        return

    # Split text into lines
    lines = [line.strip() for line in gps_text.split("\n") if line.strip()]
    if not lines:
        await update.message.reply_text("⚠️ No valid GPS text found.")
        return

    # Measure text block height
    line_heights = [font_big.getbbox("A")[3]] + [font_small.getbbox("A")[3]] * (len(lines) - 1)
    total_height = sum(line_heights) + (len(lines) - 1) * 10
    img_w, img_h = combined.size
    start_y = img_h - total_height - 100  # move block slightly up

    # Draw text lines, center-aligned with letter spacing
    for i, line in enumerate(lines):
        font = font_big if i == 0 else font_small
        spaced_line = " ".join(char for char in line)
        text_width = font.getlength(spaced_line)
        x = (img_w - text_width) // 2 - 15  # centered and nudged left
        draw.text((x, start_y), spaced_line, font=font, fill="white")
        start_y += line_heights[i] + 10

    # Save to buffer and send
    result = BytesIO()
    combined.convert("RGB").save(result, format="JPEG", quality=95)
    result.seek(0)

    await update.message.reply_photo(photo=InputFile(result), caption="✅ GPS-stamped!")

# Main bot runner
def main():
    logging.info("🚀 Starting bot...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()

if __name__ == "__main__":
    main()
