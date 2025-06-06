from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import uuid
import threading
import time
import camelot
import openpyxl

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
    return jsonify({'status': 'PDF to Excel (Camelot-Only) API is running ✅'}), 200

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
        ws.title = "Extracted_Tables"

        print("🧪 Extracting tables with Camelot (lattice)...")
        tables = camelot.read_pdf(input_pdf, pages='all', flavor='lattice')

        if tables.n == 0:
            print("❌ No tables found.")
            delete_file_later(input_pdf)
            return 'No extractable tables found.', 400

        print(f"✅ Found {tables.n} tables")

        for table_index, table in enumerate(tables):
            ws.append([f"Table {table_index + 1}"])
            for row in table.df.values.tolist():
                ws.append(row)
            ws.append([""])  # Add space between tables

        wb.save(output_excel)

    import traceback

except Exception as e:
    print("❌ Error during Camelot processing:")
    traceback.print_exc()  # <- Shows detailed error in Render logs
    return 'Conversion failed.', 500


    delete_file_later(input_pdf)
    delete_file_later(output_excel)

    return send_file(output_excel, as_attachment=True, download_name='converted.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

if __name__ == '__main__':
    app.run(debug=False)
