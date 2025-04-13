from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import uuid
import threading
import time
import camelot
import openpyxl
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

print("✅ app.py loaded successfully")

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def delete_file_later(path, delay=300):
    def remove():
        time.sleep(delay)
        if os.path.exists(path):
            os.remove(path)
    threading.Thread(target=remove).start()

@app.route('/')
def home():
    return jsonify({'status': 'PDF to Excel (Camelot + OCR Sheet) API is running ✅'}), 200

@app.route('/convert', methods=['POST'])
def convert_pdf_to_excel():
    file = request.files.get('file')
    if not file:
        return 'No file uploaded', 400

    filename = secure_filename(file.filename)
    file_id = str(uuid.uuid4())
    input_pdf = os.path.join(UPLOAD_FOLDER, f"{file_id}_{filename}")
    output_excel = os.path.join(UPLOAD_FOLDER, f"{file_id}_converted.xlsx")
    file.save(input_pdf)

    try:
        wb = openpyxl.Workbook()
        table_ws = wb.active
        table_ws.title = "Tables"
        row_index = 1

        print("🧪 Trying Camelot (lattice)...")
        try:
            tables = camelot.read_pdf(input_pdf, pages='all', flavor='lattice')
            print(f"✅ Camelot found {tables.n} tables")

            if tables.n > 0:
                for table in tables:
                    data = table.df.values.tolist()
                    for row in data:
                        table_ws.append(row)
                        row_index += 1
        except Exception as e:
            print("❌ Camelot failed:", e)

        print("⚙️ Running OCR fallback to extract all text...")
        raw_ws = wb.create_sheet(title="Raw_Text")
        images = convert_from_path(input_pdf)
        for page_num, img in enumerate(images, start=1):
            text = pytesseract.image_to_string(img, lang='eng+hin')
            raw_ws.append([f"-- Page {page_num} --"])
            for line in text.splitlines():
                if line.strip():
                    raw_ws.append([line])

        wb.save(output_excel)

    except Exception as e:
        print("❌ Error during conversion:", e)
        return 'Conversion failed.', 500

    delete_file_later(input_pdf)
    delete_file_later(output_excel)

    return send_file(output_excel, as_attachment=True, download_name='converted.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

if __name__ == '__main__':
    app.run(debug=False)
