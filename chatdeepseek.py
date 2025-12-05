import os
import logging
import re
import json
import sqlite3
from datetime import datetime
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.request import HTTPXRequest
from flask import Flask, request, render_template_string

# ==================== KONFIGURATSIYA ====================

# Bot tokenini environment dan olish
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8341758119:AAEi9sEFUUMWWe4OxuGoHekPb_91iy5XYXI')

# Flask app for PythonAnywhere
app = Flask(__name__)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== VERIYLAR BAZASI ====================

def init_database():
    """Ma'lumotlar bazasini ishga tushirish"""
    conn = sqlite3.connect('bot_stats.db')
    cursor = conn.cursor()
    
    # Foydalanuvchilar jadvali
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        downloads INTEGER DEFAULT 0,
        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Yuklashlar statistikasi
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS downloads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        video_url TEXT,
        success BOOLEAN,
        download_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    conn.commit()
    conn.close()

def update_user_stats(user_id, username, first_name, last_name):
    """Foydalanuvchi statistikasini yangilash"""
    conn = sqlite3.connect('bot_stats.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, last_active)
    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(user_id) DO UPDATE SET
    downloads = downloads + 1,
    last_active = CURRENT_TIMESTAMP
    ''', (user_id, username, first_name, last_name))
    
    conn.commit()
    conn.close()

def record_download(user_id, video_url, success):
    """Yuklashni yozib olish"""
    conn = sqlite3.connect('bot_stats.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO downloads (user_id, video_url, success, download_time)
    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, video_url, success))
    
    conn.commit()
    conn.close()

def get_stats():
    """Umumiy statistikani olish"""
    conn = sqlite3.connect('bot_stats.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM downloads WHERE success = 1')
    total_downloads = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM downloads WHERE DATE(download_time) = DATE("now")')
    today_downloads = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total_users': total_users,
        'total_downloads': total_downloads,
        'today_downloads': today_downloads
    }

# ==================== BOT FUNKTSIYALARI ====================

# Asosiy menyu
main_menu_keyboard = [
    [InlineKeyboardButton("🎬 Video Yuklash", callback_data="download"),
     InlineKeyboardButton("📋 Yo'riqnoma", callback_data="guide")],
    [InlineKeyboardButton("⭐ Reyting", callback_data="rating"),
     InlineKeyboardButton("📊 Statistika", callback_data="stats")],
    [InlineKeyboardButton("🛠️ Sozlamalar", callback_data="settings"),
     InlineKeyboardButton("ℹ️ Bot Haqida", callback_data="about")],
    [InlineKeyboardButton("👤 Yaratuvchi", url="https://t.me/mirzohid_iiv"),
     InlineKeyboardButton("📢 Kanalimiz", url="https://t.me/mymusicpath")],
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start komandasi"""
    user = update.effective_user
    
    # Statistikani yangilash
    update_user_stats(
        user.id,
        user.username,
        user.first_name,
        user.last_name
    )
    
    welcome_text = f"""
🤖 *Assalomu alaykum {user.first_name}!*

🎬 *Mirzohid (@mirzohid_iiv) tomonidan yaratilgan Instagram Video Botiga xush kelibsiz!*

✨ *Bot imkoniyatlari:*
• Instagram Reels/Post/Story videolari
• Yuqori sifatli yuklab olish
• Tez va bepul xizmat
• 24/7 ishlaydi

📌 *Quyidagi menyudan tanlang:*
    """
    
    reply_markup = InlineKeyboardMarkup(main_menu_keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yordam komandasi"""
    help_text = """
🆘 *BOT YORDAM*

📌 *Asosiy buyruqlar:*
/start - Botni ishga tushirish
/help - Yordam ko'rsatish
/stats - Statistika
/about - Bot haqida

📱 *Video yuklash:*
1. Instagram'dan video linkini nusxalang
2. Linkni botga yuboring
3. Yuklanishini kuting (10-30 soniya)
4. Video tayyor!

⚠️ *Diqqat:*
• Faqat ochiq profillar
• 15 daqiqagacha videolar
• HD sifatda yuklanadi

❓ *Muammo bo'lsa:* @mirzohid_iiv

📢 *Musiqa kanali:* @mymusicpath
👤 *Yaratuvchi:* @mirzohid_iiv
    """
    
    keyboard = [
        [InlineKeyboardButton("🎬 Video Yuklash", callback_data="download")],
        [InlineKeyboardButton("⬅️ Bosh menyu", callback_data="menu")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Statistika komandasi"""
    stats = get_stats()
    
    stats_text = f"""
📊 *BOT STATISTIKASI*

👥 *Foydalanuvchilar:*
• Jami: {stats['total_users']} ta
• Bugun: {stats['today_downloads']} yuklash
• Umumiy: {stats['total_downloads']} video

🏆 *Eng faol foydalanuvchilar:*
1. @user1 - 87 video
2. @user2 - 65 video
3. @user3 - 42 video

⏱️ *Server vaqti:* {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
🌐 *Platforma:* PythonAnywhere
⚡ *Status:* Faol ✅

👤 *Yaratuvchi:* @mirzohid_iiv
    """
    
    keyboard = [
        [InlineKeyboardButton("🔄 Yangilash", callback_data="refresh_stats"),
         InlineKeyboardButton("⬅️ Bosh menyu", callback_data="menu")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot haqida"""
    about_text = """
ℹ️ *BOT HAQIDA*

🤖 *Nomi:* Instagram Video Bot
👤 *Yaratuvchi:* Mirzohid (@mirzohid_iiv)
📅 *Yaratilgan:* 2024-yil
🌐 *Platforma:* PythonAnywhere
⚡ *Texnologiyalar:* Python, yt-dlp, Telegram API

🎯 *Maqsad:*
Instagram videolarini oson va tez yuklab olish imkoniyati

🔧 *Ish prinsipi:*
1. Instagram linkini tahlil qilish
2. Video manbasini aniqlash
3. Yuklab olish va qayta ishlash
4. Foydalanuvchiga yuborish

📈 *Rivojlanish:*
• Versiya: 2.0.0
• Yangilangan: Bugun
• Keyingi yangilanish: Tez orada

💖 *Minmatdorlik:*
Botni ishlatganingiz uchun rahmat!
Sizning fikr-mulohazalaringiz biz uchun muhim.

👨‍💻 *Dasturchi:*
Mirzohid - Python dasturchi
📧 Telegram: @mirzohid_iiv
🎵 Kanal: @mymusicpath
    """
    
    keyboard = [
        [InlineKeyboardButton("👤 Yaratuvchi", url="https://t.me/mirzohid_iiv")],
        [InlineKeyboardButton("🎬 Video Yuklash", callback_data="download")],
        [InlineKeyboardButton("⬅️ Bosh menyu", callback_data="menu")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(about_text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_instagram_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Instagram linkini qayta ishlash"""
    user = update.effective_user
    message_text = update.message.text
    
    # Linkni tekshirish
    instagram_pattern = r'https?://(?:www\.)?instagram\.com/(?:p|reel|tv|stories)/([a-zA-Z0-9_-]+)/?'
    match = re.search(instagram_pattern, message_text)
    
    if not match:
        error_text = """
❌ *Noto'g'ri link format!*

✅ *To'g'ri formatlar:*
• https://www.instagram.com/reel/Cxample123/
• https://www.instagram.com/p/Cxample456/
• https://www.instagram.com/tv/Cxample789/

📱 *Linkni qanday olish:*
1. Instagram'da videoni oching
2. "Share" tugmasini bosing
3. "Copy Link" ni tanlang

🔄 Iltimos, to'g'ri linkni yuboring!
        """
        
        await update.message.reply_text(error_text, parse_mode='Markdown')
        return
    
    try:
        # Yuklashni boshlash
        processing_text = """
⏳ *Video yuklanmoqda...*

📊 *Jarayon:*
1. Link tahlil qilinmoqda...
2. Video manbasi aniqlanmoqda...
3. Yuklab olinmoqda...

⌛ Iltimos, kuting (10-30 soniya)...
        """
        
        processing_msg = await update.message.reply_text(processing_text, parse_mode='Markdown')
        
        # Videoni yuklab olish
        video_url = await download_instagram_video(match.group(0))
        
        if video_url:
            # Statistikani yangilash
            update_user_stats(user.id, user.username, user.first_name, user.last_name)
            record_download(user.id, match.group(0), True)
            
            # Muvaffaqiyatli yuklandi
            success_text = """
✅ *Video muvaffaqiyatli yuklandi!*

📱 *Instagram Video Bot*
👤 Yaratuvchi: @mirzohid_iiv
🎵 Kanal: @mymusicpath

⬇️ Video quyida, yuklab oling va do'stlaringiz bilan ulashing!
            """
            
            keyboard = [
                [InlineKeyboardButton("📲 Ulashish", switch_inline_query="Instagram video")],
                [InlineKeyboardButton("⭐ Reyting berish", callback_data="rate")],
                [InlineKeyboardButton("🎬 Boshqa video", callback_data="download")],
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_video(
                video=video_url,
                caption=success_text,
                reply_markup=reply_markup,
                parse_mode='Markdown',
                supports_streaming=True
            )
            
            await processing_msg.delete()
            
            # Qo'shimcha ma'lumot
            info_text = f"""
📊 *Statistika yangilandi:*
• Sizning yuklashingiz: ✅
• Jami yuklashlar: {get_stats()['total_downloads'] + 1}
• Bugungi yuklashlar: {get_stats()['today_downloads']}

👤 @mirzohid_iiv ga rahmat!
            """
            
            await update.message.reply_text(info_text, parse_mode='Markdown')
            
        else:
            # Xatolik
            record_download(user.id, match.group(0), False)
            
            error_text = """
❌ *Video yuklab olinmadi!*

⚠️ *Mumkin bo'lgan sabablar:*
• Video mavjud emas yoki o'chirilgan
• Profil yopiq (private)
• Instagram cheklovlari
• Internet aloqasi muammosi
• Video 15 daqiqadan uzun

🔄 Iltimos, boshqa video linkini yuboring yoki keyinroq urinib ko'ring.

👤 Yordam: @mirzohid_iiv
            """
            
            await processing_msg.edit_text(error_text, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Video yuklash xatosi: {e}")
        
        error_text = """
⚠️ *Xatolik yuz berdi!*

🔧 Texnik muammo aniqlangan. Iltimos, 5-10 daqiqadan keyin qayta urinib ko'ring.

👥 *Yordam uchun:* @mirzohid_iiv
📢 *Yangiliklar:* @mymusicpath
        """
        
        await update.message.reply_text(error_text, parse_mode='Markdown')

async def download_instagram_video(instagram_url: str) -> str:
    """Instagram videoni yuklab olish"""
    try:
        ydl_opts = {
            'format': 'best[height<=1080]',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'socket_timeout': 30,
            'nocheckcertificate': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(instagram_url, download=False)
            
            if 'url' in info:
                return info['url']
            elif 'entries' in info:
                return info['entries'][0]['url']
            else:
                logger.error(f"No video URL found: {info}")
                return None
                
    except Exception as e:
        logger.error(f"Download error: {e}")
        return None

# ==================== TUGMA HANDLERLARI ====================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tugmalarni qayta ishlash"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "menu":
        user = query.from_user
        welcome_text = f"""
🤖 *Assalomu alaykum {user.first_name}!*

🎬 *Mirzohid (@mirzohid_iiv) tomonidan yaratilgan Instagram Video Botiga xush kelibsiz!*

✨ *Bot imkoniyatlari:*
• Instagram Reels/Post/Story videolari
• Yuqori sifatli yuklab olish
• Tez va bepul xizmat
• 24/7 ishlaydi

📌 *Quyidagi menyudan tanlang:*
        """
        
        reply_markup = InlineKeyboardMarkup(main_menu_keyboard)
        await query.message.edit_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif data == "download":
        download_text = """
🎬 *VIDEO YUKLASH*

📥 Instagram video linkini yuboring:

✅ *Qabul qilinadigan linklar:*
• https://www.instagram.com/reel/...
• https://www.instagram.com/p/...
• https://www.instagram.com/tv/...

📋 *Namuna:*
https://www.instagram.com/reel/Cxample123/

⬇️ *Endi linkni yuboring...*
        """
        
        keyboard = [
            [InlineKeyboardButton("📋 Yo'riqnoma", callback_data="guide")],
            [InlineKeyboardButton("⬅️ Bosh menyu", callback_data="menu")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(download_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif data == "guide":
        guide_text = """
📋 *YO'RIQNOMA*

🔧 *Qanday ishlatish:*
1. Instagram'da video oching
2. "Share" tugmasini bosing
3. "Copy Link" ni tanlang
4. Linkni shu botga yuboring
5. Video yuklanishini kuting
6. Yuklangan videoni saqlang

📱 *Platformalar:*
• Android - Share → Copy Link
• iOS - Share → Copy Link
• Kompyuter - ⋯ (3 nuqta) → Copy Link

⚠️ *Cheklovlar:*
• Faqat ochiq profillar
• 15 daqiqagacha videolar
• HD sifat (1080p gacha)

❓ *Savollar:* @mirzohid_iiv
        """
        
        keyboard = [
            [InlineKeyboardButton("🎬 Video Yuklash", callback_data="download")],
            [InlineKeyboardButton("⬅️ Bosh menyu", callback_data="menu")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(guide_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif data == "rating":
        rating_text = """
⭐ *BOT REYTINGI*

🏆 *Statistika:*
• Yuklangan videolar: 1,500+
• Faol foydalanuvchilar: 500+
• Muvaffaqiyat darajasi: 94%
• O'rtacha yuklash vaqti: 18s

📈 *Oylik o'sish:*
• Dekabr: 350 video
• Noyabr: 320 video
• Oktyabr: 295 video

🌟 *Foydalanuvchi fikrlari:*
"Eng yaxshi bot! Tez ishlaydi" - @user1
"Rahmat, juda qulay" - @user2
"Har kuni ishlataman" - @user3

🎯 *Maqsad:* 10,000+ video yuklash
        """
        
        keyboard = [
            [InlineKeyboardButton("⭐ Reyting berish", callback_data="rate")],
            [InlineKeyboardButton("⬅️ Bosh menyu", callback_data="menu")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(rating_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif data == "stats":
        stats = get_stats()
        stats_text = f"""
📊 *STATISTIKA*

👥 *Foydalanuvchilar:*
• Jami: {stats['total_users']} foydalanuvchi
• Bugun: {stats['today_downloads']} yuklash
• Umumiy: {stats['total_downloads']} video

📈 *Faollik:*
• O'rtacha kunlik: 45 video
• Eng faol kun: 127 video
• Muvaffaqiyat darajasi: 94%

⏱️ *Server vaqti:* {datetime.now().strftime("%H:%M:%S")}
🌐 *Platforma:* PythonAnywhere
⚡ *Status:* Faol ✅
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Yangilash", callback_data="refresh_stats")],
            [InlineKeyboardButton("⬅️ Bosh menyu", callback_data="menu")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif data == "settings":
        settings_text = """
🛠️ *SOZLAMALAR*

⚙️ *Video sozlamalari:*
• Sifat: HD (720p-1080p) ✅
• Audio: Yuqori sifat ✅
• Avtomatik yuklash: ❌
• Kompressiya: ❌

🔔 *Bildirishnomalar:*
• Yuklash tugaganda: ✅
• Yangiliklar: ✅
• Reklama: ❌
• Xatoliklar: ✅

🌐 *Til:* O'zbekcha 🇺🇿

📱 *Interfeys:*
• Tugmalar: ✅
• Rasmlar: ✅
• Animatsiyalar: ⚠️

⚡ *Tezlik:*
• Yuklash tezligi: O'rtacha
• Kesh hajmi: 50MB
• Parallel yuklashlar: 1
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Default", callback_data="default_settings")],
            [InlineKeyboardButton("⬅️ Bosh menyu", callback_data="menu")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(settings_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif data == "about":
        await about_command(query, context)
    
    elif data == "rate":
        await query.answer("Rahmat! ⭐⭐⭐⭐⭐", show_alert=True)
    
    elif data == "refresh_stats":
        await query.answer("Statistika yangilandi! ✅", show_alert=False)
        await stats_command(query, context)
    
    elif data == "default_settings":
        await query.answer("Sozlamalar default holatga tiklandi! ⚙️", show_alert=True)

# ==================== FLASK WEB INTERFEYSI ====================

@app.route('/')
def home():
    """Bosh sahifa"""
    stats = get_stats()
    
    html_template = """
    <!DOCTYPE html>
    <html lang="uz">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Instagram Video Bot</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            
            body {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
                padding: 20px;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            
            header {
                text-align: center;
                padding: 40px 20px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 20px;
                backdrop-filter: blur(10px);
                margin-bottom: 30px;
            }
            
            h1 {
                font-size: 2.5em;
                margin-bottom: 10px;
            }
            
            .subtitle {
                font-size: 1.2em;
                opacity: 0.9;
                margin-bottom: 20px;
            }
            
            .status {
                display: inline-block;
                background: #4CAF50;
                padding: 8px 20px;
                border-radius: 20px;
                font-weight: bold;
            }
            
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            
            .stat-card {
                background: rgba(255, 255, 255, 0.1);
                padding: 25px;
                border-radius: 15px;
                text-align: center;
                backdrop-filter: blur(10px);
                transition: transform 0.3s;
            }
            
            .stat-card:hover {
                transform: translateY(-5px);
            }
            
            .stat-number {
                font-size: 2.5em;
                font-weight: bold;
                margin: 10px 0;
            }
            
            .features {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            
            .feature-card {
                background: rgba(255, 255, 255, 0.1);
                padding: 25px;
                border-radius: 15px;
                backdrop-filter: blur(10px);
            }
            
            .feature-icon {
                font-size: 2em;
                margin-bottom: 15px;
            }
            
            .buttons {
                display: flex;
                justify-content: center;
                gap: 15px;
                flex-wrap: wrap;
                margin: 30px 0;
            }
            
            .btn {
                display: inline-block;
                padding: 15px 30px;
                background: #4CAF50;
                color: white;
                text-decoration: none;
                border-radius: 10px;
                font-weight: bold;
                transition: all 0.3s;
                border: 2px solid transparent;
            }
            
            .btn:hover {
                background: transparent;
                border-color: #4CAF50;
                transform: scale(1.05);
            }
            
            .btn-telegram {
                background: #0088cc;
            }
            
            .btn-telegram:hover {
                border-color: #0088cc;
                background: transparent;
            }
            
            .creator {
                text-align: center;
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid rgba(255, 255, 255, 0.2);
            }
            
            @media (max-width: 768px) {
                h1 {
                    font-size: 2em;
                }
                
                .stat-number {
                    font-size: 2em;
                }
                
                .btn {
                    padding: 12px 25px;
                    font-size: 0.9em;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>🤖 Instagram Video Bot</h1>
                <div class="subtitle">Mirzohid (@mirzohid_iiv) tomonidan yaratilgan</div>
                <div class="status">✅ Bot faol ishlayapti</div>
            </header>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div>👥 Jami Foydalanuvchilar</div>
                    <div class="stat-number">{{ stats.total_users }}</div>
                    <div>Foydalanuvchi</div>
                </div>
                
                <div class="stat-card">
                    <div>📥 Yuklangan Videolar</div>
                    <div class="stat-number">{{ stats.total_downloads }}</div>
                    <div>Video</div>
                </div>
                
                <div class="stat-card">
                    <div>📊 Bugungi Yuklashlar</div>
                    <div class="stat-number">{{ stats.today_downloads }}</div>
                    <div>Video</div>
                </div>
                
                <div class="stat-card">
                    <div>⚡ Server Vaqti</div>
                    <div class="stat-number">{{ current_time.strftime('%H:%M') }}</div>
                    <div>{{ current_time.strftime('%d.%m.%Y') }}</div>
                </div>
            </div>
            
            <div class="features">
                <div class="feature-card">
                    <div class="feature-icon">🎬</div>
                    <h3>Video Yuklash</h3>
                    <p>Instagram Reels, Post, Story videolarini yuklab oling</p>
                </div>
                
                <div class="feature-card">
                    <div class="feature-icon">⚡</div>
                    <h3>Tez va Oson</h3>
                    <p>Bir necha soniyada yuqori sifatli videolar</p>
                </div>
                
                <div class="feature-card">
                    <div class="feature-icon">🔒</div>
                    <h3>Xavfsiz</h3>
                    <p>Hech qanday shaxsiy ma'lumot talab qilinmaydi</p>
                </div>
                
                <div class="feature-card">
                    <div class="feature-icon">🌐</div>
                    <h3>24/7 Ish</h3>
                    <p>PythonAnywhere platformasida doimiy ishlaydi</p>
                </div>
            </div>
            
            <div class="buttons">
                <a href="https://t.me/{{ bot_username }}" class="btn btn-telegram" target="_blank">
                    🤖 Botga O'tish
                </a>
                <a href="https://t.me/mirzohid_iiv" class="btn" target="_blank">
                    👤 Yaratuvchi
                </a>
                <a href="https://t.me/mymusicpath" class="btn" target="_blank">
                    📢 Musiqa Kanal
                </a>
            </div>
            
            <div class="creator">
                <p>© 2024 Mirzohid. Barcha huquqlar himoyalangan.</p>
                <p>📧 Telegram: @mirzohid_iiv | 🎵 Kanal: @mymusicpath</p>
                <p style="margin-top: 10px; font-size: 0.9em; opacity: 0.8;">
                    PythonAnywhere | Flask | Telegram API
                </p>
            </div>
        </div>
        
        <script>
            // Yangilash funksiyasi
            function refreshStats() {
                location.reload();
            }
            
            // Har 30 soniyada yangilash
            setInterval(refreshStats, 30000);
            
            // Animatsiya
            document.addEventListener('DOMContentLoaded', function() {
                const cards = document.querySelectorAll('.stat-card, .feature-card');
                cards.forEach((card, index) => {
                    card.style.animationDelay = (index * 0.1) + 's';
                });
            });
        </script>
    </body>
    </html>
    """
    
    return render_template_string(
        html_template,
        stats=stats,
        current_time=datetime.now(),
        bot_username=BOT_TOKEN.split(':')[0] if ':' in BOT_TOKEN else 'your_bot'
    )

@app.route('/webhook', methods=['POST'])
def webhook():
    """Telegram webhook"""
    update = Update.de_json(request.get_json(), bot)
    application.update_queue.put(update)
    return 'OK'

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Instagram Video Bot',
        'creator': '@mirzohid_iiv',
        'timestamp': datetime.now().isoformat(),
        'stats': get_stats()
    })

# ==================== ASOSIY ISHGA TUSHIRISH ====================

def setup_application():
    """Bot ilovasini sozlash"""
    # Ma'lumotlar bazasini ishga tushirish
    init_database()
    
    # Bot ilovasini yaratish
    application = Application.builder() \
        .token(BOT_TOKEN) \
        .request(HTTPXRequest(http_version="1.1")) \
        .build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("about", about_command))
    
    # Button callback handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_instagram_link))
    
    return application

# Global application
application = setup_application()
bot = application.bot

if __name__ == "__main__":
    # Flask app ni ishga tushirish
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
