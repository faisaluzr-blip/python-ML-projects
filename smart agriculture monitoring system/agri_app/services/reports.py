import csv
from io import BytesIO, StringIO


def build_pdf_report(snapshot, soil, crop):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        return _minimal_pdf(snapshot, soil, crop)
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setTitle("AI Smart Agriculture Report")
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(48, 790, "AI Smart Agriculture Monitoring Report")
    pdf.setFont("Helvetica", 11)
    y = 745
    sections = [
        ("Live Sensor Snapshot", snapshot),
        ("Soil Intelligence", soil),
        ("Crop Recommendation", crop),
    ]
    for title, values in sections:
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(48, y, title)
        y -= 22
        pdf.setFont("Helvetica", 10)
        for key, value in values.items():
            text = f"{key}: {value}"
            pdf.drawString(64, y, text[:95])
            y -= 16
            if y < 70:
                pdf.showPage()
                y = 790
        y -= 10
    pdf.save()
    buffer.seek(0)
    return buffer


def _minimal_pdf(snapshot, soil, crop):
    lines = ["AI Smart Agriculture Monitoring Report", "", "Live Sensor Snapshot"]
    lines += [f"{key}: {value}" for key, value in snapshot.items()]
    lines += ["", "Soil Intelligence"]
    lines += [f"{key}: {value}" for key, value in soil.items()]
    lines += ["", "Crop Recommendation"]
    lines += [f"{key}: {value}" for key, value in crop.items()]
    text = "\\n".join(lines).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 11 Tf 50 790 Td 14 TL ({text}) Tj ET"
    objects = [
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj",
        "4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
        f"5 0 obj << /Length {len(stream)} >> stream\n{stream}\nendstream endobj",
    ]
    pdf = "%PDF-1.4\n" + "\n".join(objects) + "\ntrailer << /Root 1 0 R >>\n%%EOF"
    return BytesIO(pdf.encode("latin-1", errors="ignore"))


def build_sensor_csv(rows):
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()) if rows else ["message"])
    writer.writeheader()
    if rows:
        writer.writerows(rows)
    else:
        writer.writerow({"message": "No rows available"})
    return output.getvalue()
