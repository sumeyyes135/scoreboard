from flask import Flask, jsonify, render_template
import traceback
from report_service import generate_report, find_latest_report_id
from couchbase_connection import connect_to_couchbase

app = Flask(__name__)

# Couchbase'e bağlantı ve koleksiyonları tanımlama
cluster, bucket = connect_to_couchbase()  # connect_to_couchbase ile cluster ve bucket'ı alıyoruz
if bucket:
    reports_collection = bucket.scope("scoreboard").collection("reports")  # reports koleksiyonunu tanımlıyoruz

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({"message": "pong"}), 200

@app.route('/generate-report', methods=['POST'])
def create_report():
    try:
        report_data = generate_report()  # Rapor oluştur
        return jsonify(report_data), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Manuel yeni rapor tetikleme
@app.route('/manual-generate-report', methods=['POST'])
def manual_create_report():
    try:
        report_data = generate_report(new_report=True)  # Zorunlu yeni rapor oluştur
        return jsonify(report_data), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# En güncel raporu getirme
@app.route('/latest-report', methods=['GET'])
def get_latest_report():
    try:
        latest_report_id = find_latest_report_id()  # En güncel rapor ID'sini buluyoruz
        report = reports_collection.get(latest_report_id)  # En güncel raporu alıyoruz
        return jsonify(report.content_as[dict]), 200  # JSON formatında raporu geri döndür
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/visualize-report', methods=['GET'])
def visualize_report():
    return render_template('report.html')  # Görselleştirme için HTML sayfasını döndürüyoruz

if __name__ == '__main__':
    app.run(debug=True)