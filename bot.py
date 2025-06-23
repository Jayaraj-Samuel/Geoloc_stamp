import logging, textwrap
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ── CONFIG ───────────────────────────────────────────────
BOT_TOKEN      = "7988898183:AAEo7bG7ScFw0HdZRPCE1yzwYippHVv69Cg"
OVERLAY_PATH   = "overlay.png"
FONT_PATH      = "fonts/DejaVuSans.ttf"
TEXT_COLOR     = "white"
BOTTOM_Y_PCT   = 0.88           # text block baseline (88 % down)
MAX_WIDTH_PCT  = 0.90           # wrap lines to 90 % of image width
OFFSET_X       = -30            # nudge whole block left (–)
OFFSET_Y       = -40            # nudge whole block up   (–)
FIRST_LINE_BOOST = 6            # +px for line 1
CHAR_SPACING   = 0.8            # extra pixels between characters
CACHE          = {}
# ─────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(levelname)s — %(message)s")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Send a photo.\n📝 Then send the GPS text.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.photo[-1].get_file()
    CACHE[update.effective_chat.id] = await file.download_as_bytearray()
    await update.message.reply_text("📝 Got the photo. Now send the GPS text.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    if cid not in CACHE:
        await update.message.reply_text("⚠️ Please send a photo first.")
        return

    gps_text = update.message.text.strip()
    buf = BytesIO(CACHE.pop(cid))

    try:
        # ----- base photo -----
        buf.seek(0)
        with Image.open(buf) as im:
            base = im.convert("RGBA").copy()

        # ----- overlay -----
        ov = Image.open(OVERLAY_PATH).convert("RGBA").resize(base.size)
        ov_alpha = ov.getchannel("A").point(lambda a: int(a * 0.89))  # 89 % opacity
        ov.putalpha(ov_alpha)
        combined = Image.alpha_composite(base, ov)

        W, H = combined.size
        base_font_size = max(int(H * 0.018) - 2, 10)

        try:
            font_base = ImageFont.truetype(FONT_PATH, base_font_size)
        except Exception as e:
            logging.warning("Font load failed: %s. Using default.", e)
            font_base = ImageFont.load_default()

        draw = ImageDraw.Draw(combined)

        # ----- wrap lines -----
        max_px = int(W * MAX_WIDTH_PCT)
        wrapped = []
        for raw in gps_text.splitlines():
            if not raw.strip():
                wrapped.append("")
                continue
            for part in textwrap.wrap(raw, width=60):
                while draw.textlength(part, font=font_base) > max_px and len(part) > 1:
                    part = part[:-1]
                wrapped.append(part)

        # ----- positioning -----
        line_h = font_base.getbbox("Ag")[3] + 8
        widest = max(draw.textlength(line, font=font_base) for line in wrapped)
        start_x = (W - widest) // 2 + OFFSET_X
        start_y = int(H * BOTTOM_Y_PCT) + OFFSET_Y

        # ----- draw lines with letter-spacing -----
        for idx, line in enumerate(wrapped):
            this_size  = base_font_size + FIRST_LINE_BOOST if idx == 0 else base_font_size
            this_font  = ImageFont.truetype(FONT_PATH, this_size) if FONT_PATH else font_base

            x_cursor = start_x
            y_cursor = start_y + idx * line_h

            for ch in line:
                draw.text((x_cursor, y_cursor), ch, font=this_font, fill=TEXT_COLOR)
                x_cursor += draw.textlength(ch, font=this_font) + CHAR_SPACING

        # ----- output -----
        out = BytesIO(); out.name = "gps_stamped.jpg"
        combined.convert("RGB").save(out, "JPEG", quality=95)
        out.seek(0)
        await update.message.reply_photo(InputFile(out), caption="✅ GPS-stamped!")

    except Exception as err:
        logging.error("❌ %s", err)
        await update.message.reply_text(f"❌ Error: {err}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logging.info("🤖 Bot running — Ctrl-C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
