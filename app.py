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
    return jsonify({'status': 'PDF to Excel (Camelot + OCR fallback) API is running ✅'}), 200

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
        ws = wb.active
        row_index = 1
        text_found = False

        # Try to extract tables using Camelot (lattice)
        try:
            tables = camelot.read_pdf(input_pdf, pages='all', flavor='lattice')
            if tables and tables.n > 0:
                for table in tables:
                    data = table.df.values.tolist()
                    for row in data:
                        ws.append(row)
                        row_index += 1
                text_found = True
        except Exception as e:
            print("❌ Camelot failed:", e)

        # OCR fallback if no tables found
        if not text_found:
            images = convert_from_path(input_pdf)
            for img in images:
                text = pytesseract.image_to_string(img, lang='eng+hin')
                for line in text.splitlines():
                    ws.append([line])
                    row_index += 1
            text_found = True

        if not text_found:
            delete_file_later(input_pdf)
            return 'No extractable content found.', 400

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
