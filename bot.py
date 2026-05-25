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

# Estados posibles: 'uploading', 'naming', 'pricing'

def init_user(user_id):
    """Inicializa datos del usuario"""
    user_data[user_id] = {
        'products': [],
        'names': {},
        'prices': {},
        'final_prices': {},
        'current_index': 0,
        'orientation': 'landscape',
        'state': 'uploading'
    }

# ===== HANDLERS =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    init_user(user_id)
    await update.message.reply_text(
        "👋 ¡Bienvenido a CESAR ORTEGA PDF Offers!\n\n"
        "📸 Sube las fotos de los productos"
    )

async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saltar nombre en modo naming"""
    user_id = update.effective_user.id
    if user_id not in user_data:
        return
    
    if user_data[user_id]['state'] == 'naming':
        idx = user_data[user_id]['current_index']
        user_data[user_id]['names'][idx] = f"Producto {idx + 1}"
        await advance_naming(update, context, user_id)

async def receive_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        init_user(user_id)
    
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

async def advance_naming(update_or_query, context, user_id):
    """Avanza al siguiente nombre o pasa a precios"""
    idx = user_data[user_id]['current_index']
    idx += 1
    user_data[user_id]['current_index'] = idx
    
    if idx < len(user_data[user_id]['products']):
        msg = f"📝 Foto {idx + 1}: ¿Nombre?\n(o /skip para 'Producto {idx + 1}')"
        await context.bot.send_message(chat_id=user_id, text=msg)
    else:
        # Pasar a precios
        await start_pricing(context, user_id)

async def start_pricing(context, user_id):
    """Inicia la fase de precios"""
    user_data[user_id]['state'] = 'pricing'
    user_data[user_id]['current_index'] = 0
    
    await context.bot.send_message(
        chat_id=user_id,
        text="💰 Ahora los precios sin IVA (ej: 15.50)\nEl IVA del 21% se añadirá automáticamente"
    )
    
    name = user_data[user_id]['names'].get(0, "Producto 1")
    await context.bot.send_message(
        chat_id=user_id,
        text=f"{name}: ¿Precio (sin IVA)?"
    )

async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja texto según el estado"""
    user_id = update.effective_user.id
    if user_id not in user_data or not user_data[user_id]['products']:
        await update.message.reply_text("Usa /start para comenzar")
        return
    
    state = user_data[user_id]['state']
    text = update.message.text.strip()
    
    if state == 'naming':
        # Guardar nombre
        idx = user_data[user_id]['current_index']
        # Limitar a 40 caracteres
        name = text[:40] if len(text) > 40 else text
        user_data[user_id]['names'][idx] = name
        await update.message.reply_text(f"✅ '{name}' guardado")
        await advance_naming(update, context, user_id)
    
    elif state == 'pricing':
        # Guardar precio
        try:
            price = float(text.replace(',', '.'))
            idx = user_data[user_id]['current_index']
            user_data[user_id]['prices'][idx] = price
            idx += 1
            user_data[user_id]['current_index'] = idx
            
            if idx < len(user_data[user_id]['products']):
                name = user_data[user_id]['names'].get(idx, f"Producto {idx + 1}")
                await update.message.reply_text(f"✅ OK\n\n{name}: ¿Precio (sin IVA)?")
            else:
                # Mostrar resumen y preguntar aumento
                resumen = "📋 Resumen (precios sin IVA):\n\n"
                for i in range(len(user_data[user_id]['products'])):
                    nombre = user_data[user_id]['names'].get(i, f"Producto {i+1}")
                    precio = user_data[user_id]['prices'][i]
                    resumen += f"• {nombre}: {precio:.2f} €\n"
                
                keyboard = [
                    [InlineKeyboardButton("➕ +10%", callback_data='increase_10')],
                    [InlineKeyboardButton("➕ +15%", callback_data='increase_15')],
                    [InlineKeyboardButton("❌ Sin aumento", callback_data='increase_none')]
                ]
                await update.message.reply_text(
                    resumen + "\n¿Aumentar precios?",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        except ValueError:
            await update.message.reply_text("❌ Formato: 15.50")

async def ask_names(query, context, user_id):
    """Pregunta si quiere poner nombres a los productos"""
    n = len(user_data[user_id]['products'])
    keyboard = [
        [InlineKeyboardButton("📝 Sí, poner nombres", callback_data='names_yes')],
        [InlineKeyboardButton("❌ No, dejar Producto 1, 2, 3...", callback_data='names_no')]
    ]
    await query.edit_message_text(
        f"¿Quieres ponerle nombre a los {n} productos?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def ask_format(query, context, user_id):
    """Pregunta el formato del PDF"""
    n_products = len(user_data[user_id]['products'])
    pages_h = max(1, (n_products + 5) // 6) if n_products <= 9 else (n_products + 7) // 8
    pages_v = max(1, (n_products + 7) // 8) if n_products <= 9 else (n_products + 7) // 8
    
    # Layouts dinámicos
    h_info = "1 foto/pág" if n_products == 1 else f"{n_products} foto/pág" if n_products <= 3 else "auto"
    v_info = "1 foto/pág" if n_products == 1 else f"{n_products} foto/pág" if n_products <= 3 else "auto"
    
    keyboard = [
        [InlineKeyboardButton("📄 Horizontal", callback_data='format_landscape')],
        [InlineKeyboardButton("📃 Vertical", callback_data='format_portrait')]
    ]
    
    text = f"📐 ¿Qué formato quieres para el PDF?\n\nLayout adaptado a {n_products} producto(s)"
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == 'done_photos':
        if not user_data.get(user_id, {}).get('products'):
            await query.edit_message_text("❌ Sube fotos primero")
            return
        # Preguntar si quiere nombres
        await ask_names(query, context, user_id)

    elif query.data == 'more_photos':
        await query.edit_message_text("📸 Sube más fotos")

    elif query.data == 'names_yes':
        # Iniciar fase de nombres
        user_data[user_id]['state'] = 'naming'
        user_data[user_id]['current_index'] = 0
        await query.edit_message_text(
            "📝 Vamos a poner nombre a cada producto\n"
            "(escribe el nombre o /skip para mantener 'Producto N')"
        )
        await context.bot.send_message(
            chat_id=user_id,
            text="📝 Foto 1: ¿Nombre?\n(o /skip para 'Producto 1')"
        )

    elif query.data == 'names_no':
        # Saltar nombres, asignar default e ir a precios
        for i in range(len(user_data[user_id]['products'])):
            user_data[user_id]['names'][i] = f"Producto {i + 1}"
        await query.edit_message_text("👍 OK, sin nombres personalizados")
        await start_pricing(context, user_id)

    elif query.data.startswith('increase_'):
        option = query.data.replace('increase_', '')
        if option == 'none':
            user_data[user_id]['final_prices'] = user_data[user_id]['prices'].copy()
        elif option in ['10', '15']:
            pct = float(option) / 100
            for idx, price in user_data[user_id]['prices'].items():
                user_data[user_id]['final_prices'][idx] = round(price * (1 + pct), 2)
        await ask_format(query, context, user_id)

    elif query.data.startswith('format_'):
        orientation = query.data.replace('format_', '')
        user_data[user_id]['orientation'] = orientation
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
                'name': user_data[user_id]['names'].get(i, f"Producto {i+1}"),
                'price': user_data[user_id]['final_prices'].get(i, 0)
            })

        fecha = datetime.now().strftime("%d-%m-%y")
        orientation = user_data[user_id].get('orientation', 'landscape')
        output_path = f"/tmp/oferta_{fecha}_{user_id}.pdf"

        generator = PDFOfferGenerator(logo_path, orientation=orientation)
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
    application.add_handler(CommandHandler('skip', skip_command))
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
