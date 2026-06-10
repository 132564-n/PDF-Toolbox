import os
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.platypus import Table, TableStyle
from PIL import Image, ImageDraw
from pypdf import PdfWriter, PdfReader
import io

OUTPUT_DIR = Path(r"D:\WorkSpace\pdf-toolbox	est_files")
OUTPUT_DIR.mkdir(exist_ok=True)
W, H = A4

def text_pdf(name, pages=3, title="Test"):
    c = canvas.Canvas(str(OUTPUT_DIR / name), pagesize=A4)
    for p in range(1, pages+1):
        c.setFont("Helvetica-Bold", 20)
        c.drawString(60, H-60, f"{title} - Page {p}")
        c.setFont("Helvetica", 12)
        y = H-100
        for line in [f"Page {p} content line.", f"Page: {p}/{pages}", "", "Hello World!", "Test line 2.", "Test line 3.", "", "Chinese: testing."]:
            c.drawString(60, y, line)
            y -= 20
        c.showPage()
    c.save()
    print(f"OK: {name}")

def table_pdf(name):
    c = canvas.Canvas(str(OUTPUT_DIR / name), pagesize=A4)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(60, H-60, "Sales Report")
    data = [["Product", "Qty", "Price", "Total", "Date"],
            ["Laptop", "5", "5999", "29995", "2026-06-01"],
            ["Keyboard", "20", "399", "7980", "2026-06-02"],
            ["Monitor", "8", "2499", "19992", "2026-06-03"],
            ["Mouse", "50", "99", "4950", "2026-06-04"],
            ["Headphone", "30", "299", "8970", "2026-06-05"],
            ["USB 256G", "100", "159", "15900", "2026-06-06"]]
    t = Table(data, colWidths=[80,50,60,60,80])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),HexColor("#4a90d9")),
        ("TEXTCOLOR",(0,0),(-1,0),HexColor("#ffffff")),
        ("GRID",(0,0),(-1,-1),0.5,HexColor("#cccccc")),
        ("FONTSIZE",(0,0),(-1,-1),10),
        ("ALIGN",(1,0),(-1,-1),"CENTER")]))
    t.wrapOn(c, W-80, H-200)
    t.drawOn(c, 40, H-280)
    c.save()
    print(f"OK: {name}")

def image_pdf(name):
    img = Image.new("RGB", (400,300), (30,102,245))
    d = ImageDraw.Draw(img)
    d.rectangle([30,30,370,270], fill=(60,130,255))
    img_path = OUTPUT_DIR / "_tmp.png"
    img.save(img_path)
    c = canvas.Canvas(str(OUTPUT_DIR / name), pagesize=A4)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(60, H-60, "Image PDF")
    c.drawImage(str(img_path), 60, H-440, width=250, height=187)
    c.drawImage(str(img_path), 330, H-440, width=250, height=187)
    c.showPage()
    c.drawImage(str(img_path), 60, H-400, width=400, height=300)
    c.save()
    img_path.unlink()
    print(f"OK: {name}")

def encrypted_pdf(name, pwd="123456"):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(60, H-60, "Encrypted PDF")
    c.setFont("Helvetica", 14)
    c.drawString(60, H-120, f"Password: {pwd}")
    c.drawString(60, H-160, "If you can read this, decryption works!")
    c.save()
    buf.seek(0)
    reader = PdfReader(buf)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(pwd, None)
    with open(OUTPUT_DIR / name, "wb") as f:
        writer.write(f)
    print(f"OK: {name}")

print("Generating test PDFs...")
text_pdf("01_simple_3pages.pdf", 3, "Simple Doc")
text_pdf("02_merge_partA.pdf", 2, "Merge Part A")
text_pdf("03_merge_partB.pdf", 2, "Merge Part B")
text_pdf("04_large_10pages.pdf", 10, "Large Doc")
table_pdf("05_table_data.pdf")
image_pdf("06_image_rich.pdf")
encrypted_pdf("07_encrypted.pdf", "123456")
print(f"Done! Files in: {OUTPUT_DIR}")
