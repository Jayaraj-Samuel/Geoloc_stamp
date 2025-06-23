import os
import logging
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Logging
logging.basicConfig(
    format="%(asctime)s — %(levelname)s — %(message)s", level=logging.INFO
)

# Constants
FONT_PATH = "fonts/DejaVuSans.ttf"
OVERLAY_PATH = "overlay.png"

# Handle text message
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    user_data["gps_text"] = update.message.text
    await update.message.reply_text("✅ Location text received. Now send a photo.")

# Handle photo message
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

    base = Image.open(photo_bytes).convert("RGBA")
    overlay = Image.open(OVERLAY_PATH).convert("RGBA")

    # Set overlay transparency to 89%
    overlay.putalpha(int(255 * 0.89))

    # Merge overlay on top of base
    combined = Image.alpha_composite(base, overlay)

    # Prepare to draw text
    draw = ImageDraw.Draw(combined)
    try:
        font_big = ImageFont.truetype(FONT_PATH, 54)
        font_small = ImageFont.truetype(FONT_PATH, 42)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Font error: {e}")
        return

    lines = gps_text.strip().split("\n")
    lines = [line.strip() for line in lines if line.strip()]

    # Calculate starting Y
    line_heights = [font_big.getbbox("A")[3]] + [font_small.getbbox("A")[3]] * (len(lines) - 1)
    total_height = sum(line_heights) + (len(lines) - 1) * 10
    img_width, img_height = combined.size
    start_y = img_height - total_height - 80

    # Draw each line, center-aligned, spaced and left-adjusted slightly
    for i, line in enumerate(lines):
        font = font_big if i == 0 else font_small
        spacing = 2  # Adjust for letter spacing
        spaced_line = " ".join(char for char in line)  # Adds spacing manually
        line_width = font.getlength(spaced_line)
        x = (img_width - line_width) // 2 - 10  # Centered, nudged left
        draw.text((x, start_y), spaced_line, font=font, fill="white")
        start_y += line_heights[i] + 10

    # Save result to buffer
    result = BytesIO()
    combined.convert("RGB").save(result, format="JPEG", quality=95)
    result.seek(0)

    await update.message.reply_photo(photo=InputFile(result), caption="✅ GPS-stamped!")

# Main entry
def main():
    logging.info("🚀 Starting bot...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()

if __name__ == "__main__":
    main()
