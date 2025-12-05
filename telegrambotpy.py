import logging
import re
import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Bot tokenini o'rnating
BOT_TOKEN = "8341758119:AAEi9sEFUUMWWe4OxuGoHekPb_91iy5XYXI"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "Mirzohid (@mirzohid_iiv) tomonidan yaratilgan botga xush kelibsiz!\n\n"
        "Instagram linkini yuboring, men video yuklab beraman."
    )
    await update.message.reply_text(welcome_text)

async def handle_instagram_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text
    
    instagram_pattern = r'https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/([a-zA-Z0-9_-]+)/?'
    match = re.search(instagram_pattern, message_text)
    
    if not match:
        await update.message.reply_text("Iltimos, to'g'ri Instagram linkini yuboring!")
        return
    
    try:
        processing_msg = await update.message.reply_text("Video yuklanmoqda... Iltimos kuting!")
        
        video_url = await download_instagram_video(match.group(0))
        
        if video_url:
            caption = "Eng sara zur qushiqlar https://t.me/mymusicpath\n\nBot yaratuvchi: @mirzohid_iiv"
            
            await update.message.reply_video(
                video=video_url,
                caption=caption,
                supports_streaming=True
            )
            
            await processing_msg.delete()
            
        else:
            await processing_msg.edit_text("Video yuklab olishda xatolik yuz berdi. Iltimos keyinroq urinib ko'ring.")
    
    except Exception as e:
        logger.error(f"Error processing video: {e}")
        await update.message.reply_text("Xatolik yuz berdi. Iltimos keyinroq urinib ko'ring.")

async def download_instagram_video(instagram_url: str) -> str:
    try:
        ydl_opts = {
            'format': 'best',
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(instagram_url, download=False)
            if 'url' in info:
                return info['url']
            elif 'entries' in info:
                return info['entries'][0]['url']
            else:
                return None
                
    except Exception as e:
        logger.error(f"Download error: {e}")
        return None

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(msg="Exception occurred:", exc_info=context.error)

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_instagram_link))
    application.add_error_handler(error_handler)
    
    logger.info("Bot ishga tushdi...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
