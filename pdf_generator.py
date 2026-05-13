from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm, mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white, black, Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image
import os
from datetime import datetime

# Colores corporativos Cesar Ortega
COLOR_PRIMARY = HexColor("#153C8D")      # Azul corporativo
COLOR_PRIMARY_DARK = HexColor("#0F2D6B") # Azul oscuro
COLOR_SECONDARY = HexColor("#222222")    # Gris/Negro
COLOR_LIGHT_GRAY = HexColor("#F5F5F5")   # Gris claro fondo cards
COLOR_BORDER = HexColor("#E0E0E0")       # Gris borde
COLOR_WHITE = white
COLOR_TEXT = HexColor("#333333")
COLOR_TEXT_LIGHT = HexColor("#666666")


class PDFOfferGenerator:
    def __init__(self, logo_path):
        self.logo_path = logo_path
        self.page_width, self.page_height = landscape(A4)
        self.margin = 1.2 * cm

    def _draw_header(self, c, page_num=1, total_pages=1):
        """Header profesional con logo bien posicionado"""
        header_height = 3 * cm

        # Fondo azul corporativo
        c.setFillColor(COLOR_PRIMARY)
        c.rect(0, self.page_height - header_height, self.page_width, header_height, fill=1, stroke=0)

        # Línea acento abajo del header
        c.setFillColor(COLOR_PRIMARY_DARK)
        c.rect(0, self.page_height - header_height - 0.15*cm, self.page_width, 0.15*cm, fill=1, stroke=0)

        # Logo (fondo blanco redondeado para que destaque)
        logo_size = 2*cm
        logo_x = self.margin
        logo_y = self.page_height - header_height + (header_height - logo_size) / 2

        if self.logo_path and os.path.exists(self.logo_path):
            try:
                # Fondo blanco para el logo
                c.setFillColor(COLOR_WHITE)
                c.roundRect(logo_x - 0.2*cm, logo_y - 0.2*cm, 
                           logo_size + 0.4*cm, logo_size + 0.4*cm, 
                           0.2*cm, fill=1, stroke=0)
                # Logo
                c.drawImage(self.logo_path, 
                          logo_x, logo_y,
                          width=logo_size, height=logo_size,
                          preserveAspectRatio=True, mask='auto')
            except Exception as e:
                print(f"Error logo: {e}")

        # Texto empresa (al lado del logo)
        text_x = logo_x + logo_size + 0.8*cm
        text_y_center = self.page_height - header_height/2

        c.setFillColor(COLOR_WHITE)
        c.setFont("Helvetica-Bold", 22)
        c.drawString(text_x, text_y_center + 0.1*cm, "CESAR ORTEGA SL")

        c.setFont("Helvetica", 10)
        c.setFillColor(HexColor("#B8C5E0"))
        c.drawString(text_x, text_y_center - 0.5*cm, "Suministraments Industrials")

        # Título "OFERTA" a la derecha
        c.setFillColor(COLOR_WHITE)
        c.setFont("Helvetica-Bold", 28)
        offer_text = "OFERTA"
        offer_width = c.stringWidth(offer_text, "Helvetica-Bold", 28)
        c.drawString(self.page_width - self.margin - offer_width, text_y_center + 0.1*cm, offer_text)

        # Fecha
        fecha = datetime.now().strftime("%d/%m/%Y")
        c.setFont("Helvetica", 10)
        c.setFillColor(HexColor("#B8C5E0"))
        fecha_text = f"Fecha: {fecha}"
        fecha_width = c.stringWidth(fecha_text, "Helvetica", 10)
        c.drawString(self.page_width - self.margin - fecha_width, text_y_center - 0.5*cm, fecha_text)

    def _draw_footer(self, c, page_num=1, total_pages=1):
        """Footer profesional sin emojis"""
        footer_y = 1.5 * cm

        # Línea decorativa
        c.setStrokeColor(COLOR_PRIMARY)
        c.setLineWidth(0.8)
        c.line(self.margin, footer_y, self.page_width - self.margin, footer_y)

        # Acento de color
        c.setFillColor(COLOR_PRIMARY)
        c.rect(self.margin, footer_y - 0.05*cm, 3*cm, 0.1*cm, fill=1, stroke=0)

        # Nombre empresa
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(COLOR_PRIMARY)
        company_name = "CESAR ORTEGA SL"
        c.drawString(self.margin, footer_y - 0.55*cm, company_name)
        name_width = c.stringWidth(company_name, "Helvetica-Bold", 9)
        
        c.setFont("Helvetica", 8)
        c.setFillColor(COLOR_TEXT_LIGHT)
        c.drawString(self.margin + name_width + 0.3*cm, footer_y - 0.55*cm, "•  Suministros Industriales")

        # Información de contacto en una línea limpia
        c.setFont("Helvetica", 8)
        c.setFillColor(COLOR_TEXT)
        
        info_line_1 = "Carrer de la Verge de Montserrat, 31  |  08290 Ripollet, Barcelona"
        info_line_2 = "Tel: 936 917 146  |  WhatsApp: +34 678 429 948  |  suministroscesarortega.com"
        info_line_3 = "Horario: Lunes a Viernes 8:00-13:00 y 15:00-18:00  |  Sábado y Domingo cerrado"
        
        c.drawString(self.margin, footer_y - 0.95*cm, info_line_1)
        c.drawString(self.margin, footer_y - 1.25*cm, info_line_2)
        
        c.setFillColor(COLOR_TEXT_LIGHT)
        c.setFont("Helvetica-Oblique", 7)
        c.drawString(self.margin, footer_y - 1.55*cm, info_line_3)

        # Número de página a la derecha
        c.setFont("Helvetica", 8)
        c.setFillColor(COLOR_TEXT_LIGHT)
        page_text = f"Página {page_num}"
        page_width = c.stringWidth(page_text, "Helvetica", 8)
        c.drawString(self.page_width - self.margin - page_width, footer_y - 0.55*cm, page_text)

    def _draw_product_card(self, c, product, x, y, width, height):
        """Dibuja una card de producto con diseño profesional"""
        # Sombra suave (rectángulo gris desplazado)
        c.setFillColor(HexColor("#DDDDDD"))
        c.roundRect(x + 0.08*cm, y - 0.08*cm, width, height, 0.3*cm, fill=1, stroke=0)
        
        # Fondo blanco card
        c.setFillColor(COLOR_WHITE)
        c.setStrokeColor(COLOR_BORDER)
        c.setLineWidth(0.5)
        c.roundRect(x, y, width, height, 0.3*cm, fill=1, stroke=1)

        # Zona de imagen (parte superior 70%)
        img_zone_height = height * 0.72
        img_zone_y = y + height - img_zone_height
        
        # Fondo gris claro para zona de imagen
        c.setFillColor(COLOR_LIGHT_GRAY)
        c.roundRect(x + 0.15*cm, img_zone_y + 0.15*cm, 
                   width - 0.3*cm, img_zone_height - 0.3*cm, 
                   0.2*cm, fill=1, stroke=0)

        # Dibujar imagen producto
        if os.path.exists(product['image_path']):
            try:
                # Obtener dimensiones reales de la imagen
                img = Image.open(product['image_path'])
                img_w, img_h = img.size
                aspect = img_w / img_h
                
                # Calcular tamaño para que quepa con padding
                padding = 0.4*cm
                max_w = width - 0.6*cm - padding*2
                max_h = img_zone_height - 0.6*cm - padding*2
                
                if aspect > max_w / max_h:
                    # Limitado por ancho
                    draw_w = max_w
                    draw_h = max_w / aspect
                else:
                    # Limitado por alto
                    draw_h = max_h
                    draw_w = max_h * aspect
                
                # Centrar
                img_x = x + (width - draw_w) / 2
                img_y = img_zone_y + (img_zone_height - draw_h) / 2
                
                c.drawImage(product['image_path'], 
                          img_x, img_y,
                          width=draw_w, height=draw_h,
                          preserveAspectRatio=True, mask='auto')
            except Exception as e:
                print(f"Error imagen: {e}")

        # Zona de información (parte inferior 30%)
        info_y = y + 0.5*cm

        # Nombre producto
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(COLOR_SECONDARY)
        product_name = product.get('name', 'Producto')
        # Truncar si es muy largo
        max_name_width = width - 0.6*cm
        while c.stringWidth(product_name, "Helvetica-Bold", 11) > max_name_width and len(product_name) > 3:
            product_name = product_name[:-1]
        c.drawString(x + 0.4*cm, info_y + 0.7*cm, product_name)

        # Línea separadora
        c.setStrokeColor(COLOR_PRIMARY)
        c.setLineWidth(1.5)
        c.line(x + 0.4*cm, info_y + 0.5*cm, x + 1.2*cm, info_y + 0.5*cm)

        # Precio (destacado)
        c.setFont("Helvetica-Bold", 16)
        c.setFillColor(COLOR_PRIMARY)
        price_text = f"{product['price']:.2f} €"
        c.drawString(x + 0.4*cm, info_y, price_text)

        # IVA incluido / no incluido (pequeño)
        c.setFont("Helvetica-Oblique", 7)
        c.setFillColor(COLOR_TEXT_LIGHT)
        c.drawString(x + 0.4*cm, info_y - 0.3*cm, "IVA no incluido")

    def generate_pdf(self, products, output_path):
        """Genera el PDF con todas las ofertas"""
        c = canvas.Canvas(output_path, pagesize=landscape(A4))

        # Calcular cuántas páginas necesitamos
        cards_per_row = 3
        rows_per_page = 2
        cards_per_page = cards_per_row * rows_per_page
        total_pages = (len(products) + cards_per_page - 1) // cards_per_page

        # Área disponible para cards
        header_height = 3.15 * cm
        footer_height = 3.2 * cm
        content_top = self.page_height - header_height - 0.5*cm
        content_bottom = footer_height + 0.5*cm
        content_height = content_top - content_bottom

        # Dimensiones de cada card
        usable_width = self.page_width - (2 * self.margin)
        padding_x = 0.5 * cm
        card_width = (usable_width - (cards_per_row - 1) * padding_x) / cards_per_row
        
        padding_y = 0.5 * cm
        card_height = (content_height - (rows_per_page - 1) * padding_y) / rows_per_page

        current_page = 1
        self._draw_header(c, current_page, total_pages)
        self._draw_footer(c, current_page, total_pages)

        col = 0
        row = 0

        for i, product in enumerate(products):
            # Calcular posición
            x = self.margin + col * (card_width + padding_x)
            y = content_top - card_height - row * (card_height + padding_y)

            # Dibujar card
            self._draw_product_card(c, product, x, y, card_width, card_height)

            # Avanzar
            col += 1
            if col >= cards_per_row:
                col = 0
                row += 1
                if row >= rows_per_page and i < len(products) - 1:
                    # Nueva página
                    c.showPage()
                    current_page += 1
                    self._draw_header(c, current_page, total_pages)
                    self._draw_footer(c, current_page, total_pages)
                    row = 0

        c.save()
        print(f"PDF generado: {output_path}")
