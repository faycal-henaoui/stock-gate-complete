import sys
import json
import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from PIL import Image as PILImage

def create_pfe_report(image_path, json_path, output_path):
    print(f"[Step 06] Generating PDF Report: {output_path}")
    doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        spaceAfter=20
    )
    story.append(Paragraph("Rapport d'Extraction PFE", title_style))
    story.append(Paragraph(f"Source: {os.path.basename(image_path)}", styles['Normal']))
    story.append(Spacer(1, 12))

    # --- Section 1: Original Image ---
    story.append(Paragraph("1. Document Original (Entrée)", styles['Heading2']))
    story.append(Spacer(1, 10))
    
    if os.path.exists(image_path):
        try:
            pil_img = PILImage.open(image_path)
            w, h = pil_img.size
            aspect = h / w
            
            # Target width: ~450 points
            display_width = 450
            display_height = display_width * aspect
            
            # Limit height to half page
            if display_height > 350:
                 display_height = 350
                 display_width = 350 / aspect
                 
            im = Image(image_path, width=display_width, height=display_height)
            story.append(im)
        except Exception as e:
            story.append(Paragraph(f"Error loading image: {e}", styles['Normal']))
    else:
        story.append(Paragraph("Image not found.", styles['Normal']))
        
    story.append(Spacer(1, 20))

    # Load JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # --- Section 2: Metadata ---
    story.append(Paragraph("2. Métadonnées Extraites", styles['Heading2']))
    fields = data.get("fields", {})
    
    field_data = [] # List of [Key, Value]
    # Header row
    # field_data.append(["Champ", "Valeur Extraite"])
    
    for k, v in fields.items():
        key_label = k.replace("_", " ").title()
        # Translate common keys for PFE demo
        if k == "total_ttc": key_label = "Total TTC"
        if k == "invoice_number": key_label = "Numéro Facture"
        if k == "buyer_name": key_label = "Client / Acheteur"
        
        field_data.append([key_label, v])
        
    if field_data:
        t_fields = Table(field_data, colWidths=[150, 300])
        t_fields.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,-1), colors.whitesmoke),
            ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ]))
        story.append(t_fields)
    
    story.append(Spacer(1, 20))

    # --- Section 3: Table ---
    story.append(Paragraph("3. Tableau Reconstruit", styles['Heading2']))
    
    table_rows = data.get("table", {}).get("rows", [])
    if table_rows:
        # Define headers
        headers = ["Réf", "Désignation", "Qté", "P.U.", "Total"]
        data_matrix = [headers]
        
        for row in table_rows:
            # Wrap description using Paragraph to allow multi-line text
            # Use a smaller style for table content
            cell_style = styles['Normal']
            cell_style.fontSize = 9
            
            desc = Paragraph(str(row.get("description", "")), cell_style)
            ref = str(row.get("reference", ""))
            
            # Format numbers
            qty = str(row.get("quantity", ""))
            price = str(row.get("unit_price", ""))
            total_val = str(row.get("total", ""))
            
            # Validation Highlight?
            # If valid, maybe change color? Not easy in simple matrix.
            
            data_matrix.append([ref, desc, qty, price, total_val])
            
        # Table Layout
        # Page width ~530. 
        # R(40) + D(230) + Q(40) + P(70) + T(70) = 450. OK.
        t_items = Table(data_matrix, colWidths=[50, 250, 40, 70, 80])
        t_items.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            
            # Rows
            ('ALIGN', (0,1), (-1,-1), 'LEFT'),
            ('ALIGN', (2,1), (-1,-1), 'CENTER'), # Qty Center
            ('ALIGN', (3,1), (-1,-1), 'RIGHT'), # Price Right
            ('ALIGN', (4,1), (-1,-1), 'RIGHT'), # Total Right
            
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.whitesmoke]),
        ]))
        story.append(t_items)
        
        # Add Validation Legend
        story.append(Spacer(1, 10))
        story.append(Paragraph("<i>* Les données sont validées automatiquement par cohérence arithmétique.</i>", styles['Italic']))
        
    else:
        story.append(Paragraph("Aucune ligne détectée.", styles['Normal']))

    doc.build(story)
    print(f"PDF generated successfully.")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        # Interactive Check
        # Usage: python step06.py img json out
        print("Usage: python step06_visualize.py <img_path> <json_path> <output_pdf>")
    else:
        create_pfe_report(sys.argv[1], sys.argv[2], sys.argv[3])
