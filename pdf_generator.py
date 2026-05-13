from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm, mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white, black
from PIL import Image
import io
from datetime import datetime
import os

# Colores corporativos Cesar Ortega
COLOR_PRIMARY = HexColor("#153C8D")  # Azul oscuro
COLOR_SECONDARY = HexColor("#222222")  # Gris/Negro
COLOR_WHITE = white
COLOR_TEXT = HexColor("#000000")

class PDFOfferGenerator:
    def __init__(self, logo_path):
        self.logo_path = logo_path
        self.page_width, self.page_height = landscape(A4)
        self.margin = 1 * cm
        
    def _draw_header(self, pdf_canvas):
        """Dibuja el encabezado con logo y nombre empresa"""
        # Fondo azul corporativo
        pdf_canvas.setFillColor(COLOR_PRIMARY)
        pdf_canvas.rect(0, self.page_height - 2.5*cm, self.page_width, 2.5*cm, fill=1)
        
        # Logo
        try:
            if os.path.exists(self.logo_path):
                pdf_canvas.drawImage(self.logo_path, 
                                    self.margin, 
                                    self.page_height - 2.2*cm, 
                                    width=1.8*cm, 
                                    height=1.8*cm,
                                    preserveAspectRatio=True)
        except Exception as e:
            print(f"Error cargando logo: {e}")
        
        # Nombre empresa
        pdf_canvas.setFont("Helvetica-Bold", 24)
        pdf_canvas.setFillColor(COLOR_WHITE)
        pdf_canvas.drawString(2.8*cm, self.page_height - 1.3*cm, "CESAR ORTEGA SL")
        
        pdf_canvas.setFont("Helvetica", 10)
        pdf_canvas.drawString(2.8*cm, self.page_height - 1.8*cm, "Suministraments Industrials")
        
        # Fecha
        fecha = datetime.now().strftime("%d-%m-%y")
        pdf_canvas.setFont("Helvetica", 9)
        pdf_canvas.setFillColor(COLOR_TEXT)
        pdf_canvas.drawString(self.page_width - 3*cm, self.page_height - 1.5*cm, f"Oferta: {fecha}")
    
    def _draw_footer(self, pdf_canvas):
        """Dibuja el pie de página con contacto"""
        footer_y = 0.8*cm
        
        # Línea separadora
        pdf_canvas.setStrokeColor(COLOR_PRIMARY)
        pdf_canvas.setLineWidth(2)
        pdf_canvas.line(self.margin, footer_y + 0.3*cm, self.page_width - self.margin, footer_y + 0.3*cm)
        
        # Información contacto
        pdf_canvas.setFont("Helvetica-Bold", 8)
        pdf_canvas.setFillColor(COLOR_PRIMARY)
        pdf_canvas.drawString(self.margin, footer_y, "CESAR ORTEGA SL • Suministros Industriales")
        
        pdf_canvas.setFont("Helvetica", 7)
        pdf_canvas.setFillColor(COLOR_TEXT)
        pdf_canvas.drawString(self.margin, footer_y - 0.25*cm, "📍 Carrer de la Verge de Montserrat, 31 • Ripollet, 08290 • Barcelona")
        pdf_canvas.drawString(self.margin, footer_y - 0.45*cm, "📞 936917146 • 💬 WhatsApp +34 678429948")
        pdf_canvas.drawString(self.margin, footer_y - 0.65*cm, "🕐 Lun-Vie: 8:00-13:00, 15:00-18:00 • Sáb-Dom: Cerrado")
    
    def generate_pdf(self, products, output_path):
        """
        Genera PDF con layout de 3 columnas
        products: list of dicts con keys: image_path, name, price
        """
        pdf_canvas = canvas.Canvas(output_path, pagesize=landscape(A4))
        
        # Dibujar encabezado y pie
        self._draw_header(pdf_canvas)
        self._draw_footer(pdf_canvas)
        
        # Área disponible para productos
        content_top = self.page_height - 3*cm
        content_bottom = 1.5*cm
        content_height = content_top - content_bottom
        
        # Layout: 3 columnas
        col_width = (self.page_width - (4 * self.margin)) / 3
        col_height = col_width  # Cuadrado
        
        # Espaciado
        padding = 0.3*cm
        
        # Posiciones de columnas
        col_positions = [
            self.margin,
            self.margin + col_width + padding,
            self.margin + (col_width + padding) * 2
        ]
        
        row = 0
        col = 0
        current_y = content_top - padding
        
        for idx, product in enumerate(products):
            # Calcular posición
            x = col_positions[col]
            y = current_y - col_height
            
            # Verificar si necesita nueva página
            if y < content_bottom + 0.5*cm:
                pdf_canvas.showPage()
                self._draw_header(pdf_canvas)
                self._draw_footer(pdf_canvas)
                row = 0
                col = 0
                current_y = content_top - padding
                x = col_positions[col]
                y = current_y - col_height
            
            # Dibujar rectángulo con borde
            pdf_canvas.setStrokeColor(COLOR_PRIMARY)
            pdf_canvas.setLineWidth(2)
            pdf_canvas.rect(x, y, col_width - padding, col_height, fill=0)
            
            # Dibujar imagen
            try:
                if os.path.exists(product['image_path']):
                    # Zona para imagen (80% del área)
                    img_height = (col_height - padding * 2) * 0.75
                    img_width = col_width - padding * 3
                    
                    # Centrar imagen
                    img_x = x + (col_width - padding - img_width) / 2
                    img_y = y + col_height - padding - img_height
                    
                    pdf_canvas.drawImage(product['image_path'],
                                        img_x, img_y,
                                        width=img_width,
                                        height=img_height,
                                        preserveAspectRatio=True)
            except Exception as e:
                print(f"Error cargando imagen {product['image_path']}: {e}")
            
            # Dibujar nombre y precio
            pdf_canvas.setFont("Helvetica-Bold", 10)
            pdf_canvas.setFillColor(COLOR_PRIMARY)
            name_y = y + padding + 0.3*cm
            pdf_canvas.drawString(x + padding, name_y, product.get('name', 'Producto'))
            
            pdf_canvas.setFont("Helvetica-Bold", 12)
            pdf_canvas.setFillColor(COLOR_PRIMARY)
            price_y = y + padding
            pdf_canvas.drawString(x + padding, price_y, f"{product['price']}€")
            
            # Siguiente columna
            col += 1
            if col >= 3:
                col = 0
                current_y -= col_height + padding * 2
        
        pdf_canvas.save()
        print(f"PDF generado: {output_path}")
