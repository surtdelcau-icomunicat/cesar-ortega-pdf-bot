from reportlab.lib.pagesizes import A4, landscape, portrait
from reportlab.lib.units import cm, mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white, black, Color
from PIL import Image
import os
from datetime import datetime

# Colores corporativos
COLOR_PRIMARY = HexColor("#153C8D")
COLOR_PRIMARY_DARK = HexColor("#0F2D6B")
COLOR_SECONDARY = HexColor("#222222")
COLOR_LIGHT_GRAY = HexColor("#F5F5F5")
COLOR_BORDER = HexColor("#E0E0E0")
COLOR_WHITE = white
COLOR_TEXT = HexColor("#333333")
COLOR_TEXT_LIGHT = HexColor("#666666")

# IVA
IVA_RATE = 0.21


class PDFOfferGenerator:
    def __init__(self, logo_path, orientation='landscape'):
        """
        orientation: 'landscape' (3x2=6 productos) o 'portrait' (2x4=8 productos)
        """
        self.logo_path = logo_path
        self.orientation = orientation
        
        if orientation == 'portrait':
            self.page_width, self.page_height = portrait(A4)
            self.cards_per_row = 2
            self.rows_per_page = 4
        else:
            self.page_width, self.page_height = landscape(A4)
            self.cards_per_row = 3
            self.rows_per_page = 2
        
        self.margin = 1.2 * cm

    def _draw_header(self, c, page_num=1, total_pages=1):
        """Header profesional"""
        header_height = 3 * cm

        c.setFillColor(COLOR_PRIMARY)
        c.rect(0, self.page_height - header_height, self.page_width, header_height, fill=1, stroke=0)

        c.setFillColor(COLOR_PRIMARY_DARK)
        c.rect(0, self.page_height - header_height - 0.15*cm, self.page_width, 0.15*cm, fill=1, stroke=0)

        # Logo
        logo_size = 2*cm
        logo_x = self.margin
        logo_y = self.page_height - header_height + (header_height - logo_size) / 2

        if self.logo_path and os.path.exists(self.logo_path):
            try:
                c.setFillColor(COLOR_WHITE)
                c.roundRect(logo_x - 0.2*cm, logo_y - 0.2*cm,
                           logo_size + 0.4*cm, logo_size + 0.4*cm,
                           0.2*cm, fill=1, stroke=0)
                c.drawImage(self.logo_path,
                          logo_x, logo_y,
                          width=logo_size, height=logo_size,
                          preserveAspectRatio=True, mask='auto')
            except Exception as e:
                print(f"Error logo: {e}")

        # Nombre empresa
        text_x = logo_x + logo_size + 0.8*cm
        text_y_center = self.page_height - header_height/2

        c.setFillColor(COLOR_WHITE)
        
        # Ajustar tamaño según orientación
        if self.orientation == 'portrait':
            company_font_size = 18
            offer_font_size = 22
        else:
            company_font_size = 22
            offer_font_size = 28
        
        c.setFont("Helvetica-Bold", company_font_size)
        c.drawString(text_x, text_y_center + 0.1*cm, "CESAR ORTEGA SL")

        c.setFont("Helvetica", 10)
        c.setFillColor(HexColor("#B8C5E0"))
        c.drawString(text_x, text_y_center - 0.5*cm, "Suministraments Industrials")

        # OFERTA
        c.setFillColor(COLOR_WHITE)
        c.setFont("Helvetica-Bold", offer_font_size)
        offer_text = "OFERTA"
        offer_width = c.stringWidth(offer_text, "Helvetica-Bold", offer_font_size)
        c.drawString(self.page_width - self.margin - offer_width, text_y_center + 0.1*cm, offer_text)

        # Fecha
        fecha = datetime.now().strftime("%d/%m/%Y")
        c.setFont("Helvetica", 10)
        c.setFillColor(HexColor("#B8C5E0"))
        fecha_text = f"Fecha: {fecha}"
        fecha_width = c.stringWidth(fecha_text, "Helvetica", 10)
        c.drawString(self.page_width - self.margin - fecha_width, text_y_center - 0.5*cm, fecha_text)

    def _draw_footer(self, c, page_num=1, total_pages=1):
        """Footer compacto y limpio"""
        footer_y = 1.8 * cm

        c.setStrokeColor(COLOR_PRIMARY)
        c.setLineWidth(0.8)
        c.line(self.margin, footer_y, self.page_width - self.margin, footer_y)

        c.setFillColor(COLOR_PRIMARY)
        c.rect(self.margin, footer_y - 0.05*cm, 3*cm, 0.1*cm, fill=1, stroke=0)

        # Empresa
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(COLOR_PRIMARY)
        company_name = "CESAR ORTEGA SL"
        c.drawString(self.margin, footer_y - 0.55*cm, company_name)
        name_width = c.stringWidth(company_name, "Helvetica-Bold", 9)

        c.setFont("Helvetica", 8)
        c.setFillColor(COLOR_TEXT_LIGHT)
        c.drawString(self.margin + name_width + 0.3*cm, footer_y - 0.55*cm, "•  Suministros Industriales")

        # Contacto (2 líneas)
        c.setFont("Helvetica", 8)
        c.setFillColor(COLOR_TEXT)

        c.drawString(self.margin, footer_y - 0.95*cm, 
                    "Carrer de la Verge de Montserrat, 31  |  08290 Ripollet, Barcelona")
        c.drawString(self.margin, footer_y - 1.25*cm, 
                    "Tel: 936 917 146  |  WhatsApp: +34 678 429 948  |  suministroscesarortega.com")

        # Página
        c.setFont("Helvetica", 8)
        c.setFillColor(COLOR_TEXT_LIGHT)
        page_text = f"Página {page_num} de {total_pages}"
        page_width = c.stringWidth(page_text, "Helvetica", 8)
        c.drawString(self.page_width - self.margin - page_width, footer_y - 0.55*cm, page_text)

    def _draw_product_card(self, c, product, x, y, width, height):
        """Card con precio sin IVA y con IVA"""
        # Sombra
        c.setFillColor(HexColor("#DDDDDD"))
        c.roundRect(x + 0.08*cm, y - 0.08*cm, width, height, 0.3*cm, fill=1, stroke=0)

        # Fondo blanco
        c.setFillColor(COLOR_WHITE)
        c.setStrokeColor(COLOR_BORDER)
        c.setLineWidth(0.5)
        c.roundRect(x, y, width, height, 0.3*cm, fill=1, stroke=1)

        # Zona imagen (65%)
        img_zone_height = height * 0.65
        img_zone_y = y + height - img_zone_height

        c.setFillColor(COLOR_LIGHT_GRAY)
        c.roundRect(x + 0.15*cm, img_zone_y + 0.15*cm,
                   width - 0.3*cm, img_zone_height - 0.3*cm,
                   0.2*cm, fill=1, stroke=0)

        # Imagen
        if os.path.exists(product['image_path']):
            try:
                img = Image.open(product['image_path'])
                img_w, img_h = img.size
                aspect = img_w / img_h

                padding = 0.4*cm
                max_w = width - 0.6*cm - padding*2
                max_h = img_zone_height - 0.6*cm - padding*2

                if aspect > max_w / max_h:
                    draw_w = max_w
                    draw_h = max_w / aspect
                else:
                    draw_h = max_h
                    draw_w = max_h * aspect

                img_x = x + (width - draw_w) / 2
                img_y = img_zone_y + (img_zone_height - draw_h) / 2

                c.drawImage(product['image_path'],
                          img_x, img_y,
                          width=draw_w, height=draw_h,
                          preserveAspectRatio=True, mask='auto')
            except Exception as e:
                print(f"Error imagen: {e}")

        # Zona info (35%)
        info_y_base = y + 0.4*cm

        # Nombre producto
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(COLOR_SECONDARY)
        product_name = product.get('name', 'Producto')
        max_name_width = width - 0.6*cm
        while c.stringWidth(product_name, "Helvetica-Bold", 10) > max_name_width and len(product_name) > 3:
            product_name = product_name[:-1]
        c.drawString(x + 0.4*cm, info_y_base + 1.5*cm, product_name)

        # Línea separadora
        c.setStrokeColor(COLOR_PRIMARY)
        c.setLineWidth(1.5)
        c.line(x + 0.4*cm, info_y_base + 1.35*cm, x + 1.2*cm, info_y_base + 1.35*cm)

        # Precio sin IVA (pequeño, secundario)
        price_no_iva = product['price']
        price_with_iva = round(price_no_iva * (1 + IVA_RATE), 2)

        c.setFont("Helvetica", 8)
        c.setFillColor(COLOR_TEXT_LIGHT)
        c.drawString(x + 0.4*cm, info_y_base + 0.85*cm, 
                    f"Sin IVA: {price_no_iva:.2f} €")

        # Precio con IVA (grande, destacado)
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(COLOR_PRIMARY)
        c.drawString(x + 0.4*cm, info_y_base + 0.2*cm, 
                    f"{price_with_iva:.2f} €")

        # Etiqueta "IVA incluido"
        c.setFont("Helvetica-Oblique", 7)
        c.setFillColor(COLOR_TEXT_LIGHT)
        c.drawString(x + 0.4*cm, info_y_base - 0.15*cm, "IVA incluido (21%)")

    def generate_pdf(self, products, output_path):
        """Genera PDF con paginación automática"""
        if self.orientation == 'portrait':
            pagesize = portrait(A4)
        else:
            pagesize = landscape(A4)
        
        c = canvas.Canvas(output_path, pagesize=pagesize)

        cards_per_page = self.cards_per_row * self.rows_per_page
        total_pages = (len(products) + cards_per_page - 1) // cards_per_page

        header_height = 3.15 * cm
        footer_height = 2.5 * cm
        content_top = self.page_height - header_height - 0.5*cm
        content_bottom = footer_height + 0.5*cm
        content_height = content_top - content_bottom

        usable_width = self.page_width - (2 * self.margin)
        padding_x = 0.5 * cm
        card_width = (usable_width - (self.cards_per_row - 1) * padding_x) / self.cards_per_row

        padding_y = 0.5 * cm
        card_height = (content_height - (self.rows_per_page - 1) * padding_y) / self.rows_per_page

        current_page = 1
        self._draw_header(c, current_page, total_pages)
        self._draw_footer(c, current_page, total_pages)

        col = 0
        row = 0

        for i, product in enumerate(products):
            x = self.margin + col * (card_width + padding_x)
            y = content_top - card_height - row * (card_height + padding_y)

            self._draw_product_card(c, product, x, y, card_width, card_height)

            col += 1
            if col >= self.cards_per_row:
                col = 0
                row += 1
                if row >= self.rows_per_page and i < len(products) - 1:
                    c.showPage()
                    current_page += 1
                    self._draw_header(c, current_page, total_pages)
                    self._draw_footer(c, current_page, total_pages)
                    row = 0

        c.save()
        print(f"PDF generado: {output_path}")
