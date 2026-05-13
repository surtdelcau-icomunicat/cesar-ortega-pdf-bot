import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from pdf_generator import PDFOfferGenerator
import requests
from datetime import datetime
import tempfile

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
PORT = int(os.getenv('PORT', 8000))
RENDER_URL = os.getenv('RENDER_EXTERNAL_URL', '')

user_data = {}

# ===== HANDLERS =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {
        'products': [],
        'prices': {},
        'final_prices': {},
        'current_price_index': 0
    }
    await update.message.reply_text(
        "👋 ¡Bienvenido a CESAR ORTEGA PDF Offers!\n\n"
        "📸 Sube las fotos de los productos"
    )

async def receive_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {
            'products': [], 'prices': {},
            'final_prices': {}, 'current_price_index': 0
        }
    try:
        photo_file = await update.message.photo[-1].get_file()
        temp_dir = tempfile.mkdtemp()
        photo_path = os.path.join(temp_dir, f"photo_{len(user_data[user_id]['products'])}.jpg")
        await photo_file.download_to_drive(photo_path)
        user_data[user_id]['products'].append({
            'path': photo_path,
            'index': len(user_data[user_id]['products'])
        })
        await update.message.reply_text(f"✅ Foto {len(user_data[user_id]['products'])} recibida")
        keyboard = [
            [InlineKeyboardButton("✅ Terminé", callback_data='done_photos')],
            [InlineKeyboardButton("➕ Más fotos", callback_data='more_photos')]
        ]
        await update.message.reply_text(
            f"Fotos: {len(user_data[user_id]['products'])}\n¿Qué haces?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error foto: {e}")
        await update.message.reply_text("❌ Error descargando")

async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data or not user_data[user_id]['products']:
        await update.message.reply_text("Usa /start para comenzar")
        return
    try:
        price = float(update.message.text.replace(',', '.'))
        idx = user_data[user_id]['current_price_index']
        user_data[user_id]['prices'][idx] = price
        idx += 1
        user_data[user_id]['current_price_index'] = idx
        if idx < len(user_data[user_id]['products']):
            await update.message.reply_text(f"✅ OK\n\nFoto {idx + 1}: ¿Precio?")
        else:
            text = "📋 Resumen:\n\n"
            for i in range(len(user_data[user_id]['products'])):
                text += f"Foto {i+1}: {user_data[user_id]['prices'][i]}€\n"
            keyboard = [
                [InlineKeyboardButton("➕ +10%", callback_data='increase_10')],
                [InlineKeyboardButton("➕ +15%", callback_data='increase_15')],
                [InlineKeyboardButton("❌ Sin aumento", callback_data='increase_none')]
            ]
            await update.message.reply_text(
                text + "\n¿Aumentar?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except ValueError:
        await update.message.reply_text("❌ Formato: 15.50")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == 'done_photos':
        if not user_data.get(user_id, {}).get('products'):
            await query.edit_message_text("❌ Sube fotos primero")
            return
        user_data[user_id]['current_price_index'] = 0
        await query.edit_message_text("💰 Envía precios (ej: 15.50)")
        await context.bot.send_message(chat_id=user_id, text="Foto 1: ¿Precio?")

    elif query.data == 'more_photos':
        await query.edit_message_text("📸 Sube más fotos")

    elif query.data.startswith('increase_'):
        option = query.data.replace('increase_', '')
        if option == 'none':
            user_data[user_id]['final_prices'] = user_data[user_id]['prices'].copy()
        elif option in ['10', '15']:
            pct = float(option) / 100
            for idx, price in user_data[user_id]['prices'].items():
                user_data[user_id]['final_prices'][idx] = round(price * (1 + pct), 2)
        await generate_pdf(query, context, user_id)

async def generate_pdf(query, context, user_id):
    try:
        await query.edit_message_text("⏳ Generando PDF...")
        logo_path = None
        logo_url = "https://raw.githubusercontent.com/surtdelcau-icomunicat/cesar-ortega-pdf-bot/main/cesar-logo-h.png"
        try:
            r = requests.get(logo_url, timeout=5)
            if r.status_code == 200:
                tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                tmp.write(r.content)
                tmp.close()
                logo_path = tmp.name
        except:
            pass

        products = []
        for i in range(len(user_data[user_id]['products'])):
            products.append({
                'image_path': user_data[user_id]['products'][i]['path'],
                'name': f'Producto {i+1}',
                'price': user_data[user_id]['final_prices'].get(i, 0)
            })

        fecha = datetime.now().strftime("%d-%m-%y")
        output_path = f"/tmp/oferta_{fecha}_{user_id}.pdf"

        generator = PDFOfferGenerator(logo_path)
        generator.generate_pdf(products, output_path)

        with open(output_path, 'rb') as f:
            await context.bot.send_document(
                chat_id=user_id, document=f,
                filename=f"oferta_{fecha}.pdf"
            )
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ ¡PDF listo!\n\nUsa /start para otra oferta"
        )
        if os.path.exists(output_path):
            os.remove(output_path)
    except Exception as e:
        logger.error(f"Error PDF: {e}")
        await context.bot.send_message(chat_id=user_id, text=f"❌ Error: {str(e)}")

# ===== MAIN =====

def main():
    logger.info("🚀 Iniciando bot...")

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.PHOTO, receive_photos))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text))
    application.add_handler(CallbackQueryHandler(button_callback))

    webhook_url = f"{RENDER_URL}/webhook"
    logger.info(f"📡 Webhook: {webhook_url}")

    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="webhook",
        webhook_url=webhook_url
    )

if __name__ == '__main__':
    main()
