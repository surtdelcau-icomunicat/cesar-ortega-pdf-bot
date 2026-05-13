
import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram.constants import ChatAction
from pdf_generator import PDFOfferGenerator
from PIL import Image
import io
import requests
from datetime import datetime
from rembg import remove
import tempfile

# Cargar variables de entorno
load_dotenv()

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
RENDER_EXTERNAL_URL = os.getenv('RENDER_EXTERNAL_URL', 'http://localhost:5000')

# Estados de conversación
UPLOAD_PHOTOS, ASK_PRICE, ASK_INCREASE, CONFIRM = range(4)

class OfferBot:
    def __init__(self):
        self.user_data = {}
        self.logo_path = None
        self.app = None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Comando /start"""
        await update.message.reply_text(
            "👋 ¡Bienvenido a CESAR ORTEGA PDF Offers!\n\n"
            "Este bot te ayuda a crear ofertas en PDF con nuestros colores corporativos.\n\n"
            "📸 Sube las fotos de los productos que quieras incluir en la oferta.\n"
            "(Puedes enviar varias fotos de una vez)"
        )
        
        user_id = update.effective_user.id
        self.user_data[user_id] = {
            'products': [],
            'prices': {},
            'final_prices': {}
        }
        
        return UPLOAD_PHOTOS
    
    async def receive_photos(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Recibe fotos del usuario"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                'products': [],
                'prices': {},
                'final_prices': {}
            }
        
        try:
            # Descargar foto
            photo_file = await update.message.photo[-1].get_file()
            
            # Crear temp file
            temp_dir = tempfile.mkdtemp()
            photo_path = os.path.join(temp_dir, f"photo_{len(self.user_data[user_id]['products'])}.jpg")
            
            await photo_file.download_to_drive(photo_path)
            
            # Procesar con rembg (eliminar fondo)
            try:
                input_img = Image.open(photo_path)
                output_img = remove(input_img)
                
                # Guardar con fondo eliminado
                output_path = photo_path.replace('.jpg', '_processed.png')
                output_img.save(output_path)
                
                self.user_data[user_id]['products'].append({
                    'original_path': photo_path,
                    'processed_path': output_path,
                    'index': len(self.user_data[user_id]['products'])
                })
                
                await update.message.reply_text(f"✅ Foto {len(self.user_data[user_id]['products'])} recibida y procesada")
            
            except Exception as e:
                logger.error(f"Error procesando con rembg: {e}")
                await update.message.reply_text(f"⚠️ Error procesando la foto, pero la guardo igual.")
                self.user_data[user_id]['products'].append({
                    'original_path': photo_path,
                    'processed_path': photo_path,
                    'index': len(self.user_data[user_id]['products'])
                })
        
        except Exception as e:
            logger.error(f"Error descargando foto: {e}")
            await update.message.reply_text("❌ Error descargando la foto. Intenta de nuevo.")
            return UPLOAD_PHOTOS
        
        # Opciones para el usuario
        keyboard = [
            [InlineKeyboardButton("✅ Terminé de subir fotos", callback_data='done_photos')],
            [InlineKeyboardButton("➕ Subir más fotos", callback_data='more_photos')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Fotos subidas: {len(self.user_data[user_id]['products'])}\n\n"
            "¿Qué quieres hacer?",
            reply_markup=reply_markup
        )
        
        return UPLOAD_PHOTOS
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Maneja botones"""
        query = update.callback_query
        user_id = query.from_user.id
        
        await query.answer()
        
        if query.data == 'done_photos':
            if not self.user_data[user_id]['products']:
                await query.edit_message_text("❌ Debes subir al menos una foto.")
                return UPLOAD_PHOTOS
            
            # Ir a precios
            return await self.ask_prices(query, context, user_id)
        
        elif query.data == 'more_photos':
            await query.edit_message_text("📸 Sube más fotos (o haz /done cuando termines)")
            return UPLOAD_PHOTOS
        
        elif query.data.startswith('price_'):
            # El usuario ya envió precio por texto
            pass
        
        elif query.data == 'done_prices':
            return await self.ask_increase(query, context, user_id)
        
        elif query.data.startswith('increase_'):
            option = query.data.replace('increase_', '')
            return await self.handle_increase(query, context, user_id, option)
    
    async def ask_prices(self, query, context, user_id):
        """Pregunta precio de cada foto"""
        await query.edit_message_text(
            "💰 Ahora, dame el precio de cada foto:\n\n"
            f"Tienes {len(self.user_data[user_id]['products'])} fotos.\n\n"
            "Envía los precios uno por uno (ej: 15.50, 22.00, etc.)"
        )
        
        self.user_data[user_id]['current_price_index'] = 0
        
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=f"Foto {1}: ¿Cuál es el precio?"
        )
        
        return ASK_PRICE
    
    async def receive_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Recibe precios"""
        user_id = update.effective_user.id
        
        try:
            price = float(update.message.text.replace(',', '.'))
            
            idx = self.user_data[user_id]['current_price_index']
            self.user_data[user_id]['prices'][idx] = price
            
            idx += 1
            self.user_data[user_id]['current_price_index'] = idx
            
            if idx < len(self.user_data[user_id]['products']):
                await update.message.reply_text(f"✅ Precio {idx} guardado\n\nFoto {idx + 1}: ¿Cuál es el precio?")
                return ASK_PRICE
            else:
                # Todos los precios recibidos
                # Mostrar resumen y preguntar por aumento
                text = "📋 Resumen de precios:\n\n"
                for i, product in enumerate(self.user_data[user_id]['products']):
                    text += f"Foto {i+1}: {self.user_data[user_id]['prices'][i]}€\n"
                
                keyboard = [
                    [InlineKeyboardButton("➕ +10% a todos", callback_data='increase_10')],
                    [InlineKeyboardButton("➕ +15% a todos", callback_data='increase_15')],
                    [InlineKeyboardButton("🎯 Precios individuales", callback_data='increase_individual')],
                    [InlineKeyboardButton("❌ Sin aumentos", callback_data='increase_none')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(text + "\n¿Quieres aumentar precios?", reply_markup=reply_markup)
                
                return ASK_INCREASE
        
        except ValueError:
            await update.message.reply_text("❌ Precio inválido. Usa formato: 15.50")
            return ASK_PRICE
    
    async def handle_increase(self, query, context, user_id, option):
        """Maneja aumento de precios"""
        if option == 'none':
            self.user_data[user_id]['final_prices'] = self.user_data[user_id]['prices'].copy()
        elif option in ['10', '15']:
            percentage = float(option) / 100
            for idx, price in self.user_data[user_id]['prices'].items():
                self.user_data[user_id]['final_prices'][idx] = round(price * (1 + percentage), 2)
        elif option == 'individual':
            await query.edit_message_text("🎯 Envía los nuevos precios uno por uno")
            self.user_data[user_id]['current_price_index'] = 0
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text=f"Nuevo precio Foto 1:"
            )
            return ASK_INCREASE
        
        # Generar PDF
        return await self.generate_pdf(query, context, user_id)
    
    async def generate_pdf(self, query, context, user_id):
        """Genera el PDF final"""
        await query.edit_message_text("⏳ Generando PDF...")
        
        try:
            # Descargar logo
            if not self.logo_path:
                logo_url = "https://raw.githubusercontent.com/suministraces/cesar-ortega-pdf-bot/main/logo.jpg"
                try:
                    logo_response = requests.get(logo_url)
                    temp_logo = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                    temp_logo.write(logo_response.content)
                    temp_logo.close()
                    self.logo_path = temp_logo.name
                except:
                    logger.warning("No se pudo descargar logo")
                    self.logo_path = None
            
            # Preparar productos
            products = []
            for i, product in enumerate(self.user_data[user_id]['products']):
                products.append({
                    'image_path': product['processed_path'],
                    'name': f'Producto {i+1}',
                    'price': self.user_data[user_id]['final_prices'].get(i, self.user_data[user_id]['prices'].get(i, 0))
                })
            
            # Generar PDF
            fecha = datetime.now().strftime("%d-%m-%y")
            output_path = f"/tmp/oferta_{fecha}_{user_id}.pdf"
            
            generator = PDFOfferGenerator(self.logo_path)
            generator.generate_pdf(products, output_path)
            
            # Enviar PDF
            await context.bot.send_document(
                chat_id=user_id,
                document=open(output_path, 'rb'),
                filename=f"oferta_{fecha}.pdf"
            )
            
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ ¡PDF generado correctamente!\n\n"
                "¿Quieres crear otra oferta? Usa /start"
            )
            
            # Limpiar
            if os.path.exists(output_path):
                os.remove(output_path)
            
            return ConversationHandler.END
        
        except Exception as e:
            logger.error(f"Error generando PDF: {e}")
            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ Error generando PDF: {str(e)}"
            )
            return ConversationHandler.END
    
    async def done_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Comando /done para terminar de subir fotos"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_data or not self.user_data[user_id]['products']:
            await update.message.reply_text("❌ Debes subir al menos una foto. Usa /start")
            return UPLOAD_PHOTOS
        
        return await self.ask_prices_direct(update, context, user_id)
    
    async def ask_prices_direct(self, update, context, user_id):
        """Pregunta precios directamente"""
        await update.message.reply_text(
            "💰 Ahora, dame el precio de cada foto:\n\n"
            f"Tienes {len(self.user_data[user_id]['products'])} fotos.\n\n"
            "Envía los precios uno por uno (ej: 15.50)"
        )
        
        self.user_data[user_id]['current_price_index'] = 0
        
        await context.bot.send_message(
            chat_id=user_id,
            text=f"Foto 1: ¿Cuál es el precio?"
        )
        
        return ASK_PRICE
    
    def setup_handlers(self):
        """Configura los handlers de conversación"""
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                UPLOAD_PHOTOS: [
                    MessageHandler(filters.PHOTO, self.receive_photos),
                    CommandHandler('done', self.done_command),
                ],
                ASK_PRICE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_price),
                ],
                ASK_INCREASE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_price),
                ],
            },
            fallbacks=[CommandHandler('start', self.start)],
        )
        
        self.app.add_handler(conv_handler)
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
    
    async def run(self):
        """Inicia el bot"""
        self.app = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Handlers
        self.app.add_handler(CommandHandler('start', self.start))
        self.app.add_handler(MessageHandler(filters.PHOTO, self.receive_photos))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_price))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
        self.app.add_handler(CommandHandler('done', self.done_command))
        
        # Webhook para Render
        PORT = int(os.getenv('PORT', 5000))
        
        await self.app.bot.set_webhook(url=f"{RENDER_EXTERNAL_URL}/webhook")
        
        async with self.app:
            await self.app.start()
            print("✅ Bot iniciado")
            
            # Mantener bot corriendo
            while True:
                await asyncio.sleep(1)

if __name__ == '__main__':
    import asyncio
    from telegram.ext import CallbackQueryHandler
    
    bot = OfferBot()
    asyncio.run(bot.run())
