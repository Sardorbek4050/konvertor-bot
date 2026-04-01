import os
import zipfile
import json
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image

TOKEN = "7951025614:AAERwb_QDcZsYFKA3wLdDCMQNczXghzH3Tc"
ADMIN_ID = 6218464556

MAX_FILE_SIZE = 15 * 1024 * 1024

UPLOAD_FOLDER = "uploads"
DOWNLOAD_FOLDER = "downloads"
DATA_FILE = "user_data.json"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = str(user.id)
    
    users = load_users()
    if user_id not in users:
        users[user_id] = {
            "first_name": user.first_name,
            "username": user.username,
            "last_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pdf_soni": 0,
            "zip_soni": 0
        }
    else:
        users[user_id]["last_seen"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_users(users)
    
    context.user_data['rasmlar'] = []
    context.user_data['hujjatlar'] = []
    context.user_data['waiting_filename'] = False
    context.user_data['last_file'] = None
    
    await update.message.reply_text(
        "🤖 KONVERTOR BOT\n\n"
        "📸 Rasm -> PDF\n"
        "Bir nechta rasm yuboring (jpg, png).\n\n"
        "📄 Hujjat -> ZIP\n"
        "Word, Excel, PowerPoint fayllarini yuboring.\n\n"
        "⚠️ Hajm chegarasi: 15 MB\n\n"
        "📝 Ishlatish:\n"
        "1. Fayllarni yuboring\n"
        "2. /tayyor yozing\n"
        "3. Fayl nomini kiriting\n\n"
        "👑 Admin: /admin"
    )

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Siz admin emassiz!")
        return
    
    users = load_users()
    total_users = len(users)
    total_pdf = sum(u.get('pdf_soni', 0) for u in users.values())
    total_zip = sum(u.get('zip_soni', 0) for u in users.values())
    
    text = "👑 ADMIN PANEL\n\n"
    text += f"👥 Foydalanuvchilar: {total_users}\n"
    text += f"📸 PDF lar: {total_pdf}\n"
    text += f"📦 ZIP lar: {total_zip}\n\n"
    text += "Foydalanuvchilar:\n"
    text += "------------------------\n"
    
    for uid, info in users.items():
        is_admin = "⭐ ADMIN" if int(uid) == ADMIN_ID else "👤"
        text += f"{is_admin} {info.get('first_name', 'Noma\'lum')}\n"
        text += f"   ID: {uid}\n"
        text += f"   PDF: {info.get('pdf_soni', 0)} | ZIP: {info.get('zip_soni', 0)}\n"
        text += "------------------------\n"
    
    await update.message.reply_text(text)

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    photo = update.message.photo[-1]
    if photo.file_size > MAX_FILE_SIZE:
        await update.message.reply_text("❌ Fayl hajmi 15 MB dan katta!")
        return
    
    file = await context.bot.get_file(photo.file_id)
    path = f"{UPLOAD_FOLDER}/{user_id}_rasm_{len(context.user_data.get('rasmlar', []))}.jpg"
    await file.download_to_drive(path)
    
    if 'rasmlar' not in context.user_data:
        context.user_data['rasmlar'] = []
    context.user_data['rasmlar'].append(path)
    
    son = len(context.user_data['rasmlar'])
    await update.message.reply_text(f"✅ Rasm qabul qilindi! ({son} ta)\n\nYana qo'shing yoki /tayyor")

async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    doc = update.message.document
    nom = doc.file_name
    kengaytma = nom.lower().split('.')[-1]
    
    if doc.file_size > MAX_FILE_SIZE:
        await update.message.reply_text("❌ Fayl hajmi 15 MB dan katta!")
        return
    
    file = await context.bot.get_file(doc.file_id)
    
    if kengaytma in ['jpg', 'jpeg', 'png']:
        path = f"{UPLOAD_FOLDER}/{user_id}_{nom}"
        await file.download_to_drive(path)
        
        if 'rasmlar' not in context.user_data:
            context.user_data['rasmlar'] = []
        context.user_data['rasmlar'].append(path)
        
        son = len(context.user_data['rasmlar'])
        await update.message.reply_text(f"✅ Rasm qabul qilindi! ({son} ta)\n\nYana qo'shing yoki /tayyor")
    
    elif kengaytma in ['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx']:
        path = f"{UPLOAD_FOLDER}/{user_id}_{nom}"
        await file.download_to_drive(path)
        
        if 'hujjatlar' not in context.user_data:
            context.user_data['hujjatlar'] = []
        context.user_data['hujjatlar'].append(path)
        
        son = len(context.user_data['hujjatlar'])
        await update.message.reply_text(f"✅ Hujjat qabul qilindi! ({son} ta)\n\nYana qo'shing yoki /tayyor")
    
    else:
        await update.message.reply_text(f"❌ {kengaytma} format qo'llanilmaydi")

async def tayyor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    rasmlar = context.user_data.get('rasmlar', [])
    hujjatlar = context.user_data.get('hujjatlar', [])
    
    if not rasmlar and not hujjatlar:
        await update.message.reply_text("❌ Hech qanday fayl topilmadi!")
        return
    
    if rasmlar:
        await update.message.reply_text("⏳ PDF tayyorlanmoqda...")
        
        try:
            pdf_nomi = f"{update.message.chat.id}.pdf"
            
            images = []
            for r in rasmlar:
                img = Image.open(r)
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                images.append(img)
            
            if images:
                images[0].save(pdf_nomi, "PDF", save_all=True, append_images=images[1:])
            
            context.user_data['last_file'] = pdf_nomi
            context.user_data['file_type'] = 'pdf'
            context.user_data['waiting_filename'] = True
            context.user_data['temp_rasmlar'] = rasmlar.copy()
            context.user_data['rasmlar'] = []
            
            await update.message.reply_text("✅ PDF tayyor!\n\n📝 Fayl nomini kiriting:")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik: {str(e)}")
    
    elif hujjatlar:
        await update.message.reply_text("⏳ ZIP tayyorlanmoqda...")
        
        try:
            zip_nomi = f"{update.message.chat.id}.zip"
            
            with zipfile.ZipFile(zip_nomi, 'w') as zipf:
                for h in hujjatlar:
                    zipf.write(h, os.path.basename(h))
            
            context.user_data['last_file'] = zip_nomi
            context.user_data['file_type'] = 'zip'
            context.user_data['waiting_filename'] = True
            context.user_data['temp_hujjatlar'] = hujjatlar.copy()
            context.user_data['hujjatlar'] = []
            
            await update.message.reply_text("✅ ZIP tayyor!\n\n📝 Fayl nomini kiriting:")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik: {str(e)}")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    
    if context.user_data.get('waiting_filename'):
        new_name = update.message.text.strip()
        
        if not new_name.replace('_', '').replace('-', '').isalnum():
            await update.message.reply_text("❌ Noto'g'ri nom! Faqat harf, raqam, _ va - ishlating.")
            return
        
        last_file = context.user_data.get('last_file')
        file_type = context.user_data.get('file_type')
        
        if last_file and os.path.exists(last_file):
            new_filename = f"{new_name}.{file_type}"
            new_path = os.path.join(DOWNLOAD_FOLDER, new_filename)
            os.rename(last_file, new_path)
            
            with open(new_path, 'rb') as f:
                await update.message.reply_document(f, filename=new_filename, caption=f"✅ {file_type.upper()} tayyor!")
            
            users = load_users()
            if user_id in users:
                if file_type == 'pdf':
                    users[user_id]['pdf_soni'] = users[user_id].get('pdf_soni', 0) + 1
                else:
                    users[user_id]['zip_soni'] = users[user_id].get('zip_soni', 0) + 1
                save_users(users)
            
            os.remove(new_path)
            
            temp_rasmlar = context.user_data.get('temp_rasmlar', [])
            temp_hujjatlar = context.user_data.get('temp_hujjatlar', [])
            
            for r in temp_rasmlar:
                try: os.remove(r)
                except: pass
            for h in temp_hujjatlar:
                try: os.remove(h)
                except: pass
            
            context.user_data['waiting_filename'] = False
            context.user_data['last_file'] = None
            
            await update.message.reply_text("✅ Fayl yuborildi!")

async def clear_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rasmlar = context.user_data.get('rasmlar', [])
    hujjatlar = context.user_data.get('hujjatlar', [])
    
    for r in rasmlar:
        try: os.remove(r)
        except: pass
    for h in hujjatlar:
        try: os.remove(h)
        except: pass
    
    context.user_data['rasmlar'] = []
    context.user_data['hujjatlar'] = []
    context.user_data['waiting_filename'] = False
    
    await update.message.reply_text("🗑 Barcha fayllar tozalandi!")

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin_start))
app.add_handler(CommandHandler("tayyor", tayyor))
app.add_handler(CommandHandler("clear", clear_handler))
app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
app.add_handler(MessageHandler(filters.Document.ALL, document_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

print("✅ BOT ISHGA TUSHDI!")
app.run_polling()
