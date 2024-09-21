from couchbase.exceptions import DocumentNotFoundException
from metrics_calculations import (
    calculate_fortify_score,
    calculate_defect_score,
    calculate_rfc_deployment_score,
    calculate_alarm_score,
    calculate_sonarqube_score,
    calculate_performance_metrics
)
from couchbase_connection import connect_to_couchbase
from datetime import datetime
from config_loader import load_config

# Config dosyasını yüklüyoruz
config = load_config()

# Couchbase bağlantılarını ayarlıyoruz
cluster, bucket = connect_to_couchbase()
services_collection = bucket.scope(config['database']['scope']).collection("services")
reports_collection = bucket.scope(config['database']['scope']).collection("reports")

# Tam tarih ve saati (gün/ay/yıl_saat/dakika/saniye) formatında döndüren fonksiyon
def get_current_timestamp():
    return datetime.now().strftime("%d%m%Y_%H%M%S")

# Sadece gün/ay/yıl_saat formatında döndüren fonksiyon (saat bazlı kontrol için)
def get_current_timestamp_hour():
    return datetime.now().strftime("%d%m%Y_%H")

# Couchbase'den tüm servislerin key'lerini alan fonksiyon
def get_service_keys():
    try:
        query = "SELECT META().id AS service_id FROM `scoreboard`.`scoreboard`.`services`"
        result = cluster.query(query)  # Sorguyu cluster üzerinden çalıştırıyoruz
        service_keys = [row['service_id'] for row in result]
        print(f"Alınan Service Keys: {service_keys}")
        return service_keys
    except Exception as e:
        print(f"Key okuma hatası: {e}")
        return []

# Servis verilerini çekmek için
def get_service_data(service_id):
    try:
        service_result = services_collection.get(service_id)
        service_data = service_result.content_as[dict]
        print(f"{service_id} için alınan Service Data: {service_data}")
        return service_data
    except Exception as e:
        print(f"Servis verisi okuma hatası: {e}")
        return {}

# En güncel raporu bulma fonksiyonu
def find_latest_report_id():
    try:
        query = f"SELECT RAW META().id FROM `scoreboard`.`scoreboard`.`reports` WHERE META().id LIKE 'report_{get_current_timestamp_hour()}%' ORDER BY META().id DESC LIMIT 1"
        result = cluster.query(query)  # Sorguyu cluster üzerinden çalıştırıyoruz
        return list(result)[0]  # En son oluşturulan raporun ID'sini döndürüyoruz
    except Exception as e:
        print(f"En güncel raporu bulma hatası: {e}")
        raise e

# Raporu oluşturup Couchbase'e yazma fonksiyonu
def generate_report(new_report=False):
    # Tam zamanlı rapor ID'sini (gün/ay/yıl_saat/dakika/saniye) oluşturuyoruz
    report_id = f"report_{get_current_timestamp()}"
    config = load_config()

    if not new_report:
        try:
            # Aynı saat içinde rapor olup olmadığını kontrol ediyoruz
            latest_report_id = find_latest_report_id()
            if latest_report_id:
                report = reports_collection.get(latest_report_id)
                print(f"Mevcut rapor bulundu: {latest_report_id}")
                return report.content_as[dict]  # Mevcut raporu döndürüyoruz
        except DocumentNotFoundException:
            print(f"Bu saat için rapor bulunamadı, yeni rapor oluşturuluyor: {report_id}")
        except IndexError:
            print(f"Bu saate uygun rapor bulunamadı, yeni rapor oluşturuluyor: {report_id}")

    # Yeni rapor oluşturma süreci burada başlıyor
    service_keys = get_service_keys()
    if not service_keys:
        print("Servis key'leri alınamadı.")
        return {"error": "Servis key'leri alınamadı."}

    squads = {}

    for service_id in service_keys:
        service = get_service_data(service_id)
        if not service:
            continue
        squad_name = service.get("squad")
        if squad_name not in squads:
            squads[squad_name] = {
                "services_evaluated": 0,
                "metrics": {
                    "fortify_score": 0,
                    "defect_score": 0,
                    "rfc_deployment_score": 0,
                    "alarm_score": 0,
                    "sonarqube_score": 0,
                    "performance_metrics": 0
                },
                "services": [],
                "extra_score": {"total": 0, "details": []}
            }

        squads[squad_name]["services_evaluated"] += 1
        squads[squad_name]["metrics"]["fortify_score"] += calculate_fortify_score(service)
        squads[squad_name]["metrics"]["defect_score"] += calculate_defect_score(service)
        squads[squad_name]["metrics"]["rfc_deployment_score"] += calculate_rfc_deployment_score(service)
        squads[squad_name]["metrics"]["alarm_score"] += calculate_alarm_score(service)
        squads[squad_name]["metrics"]["sonarqube_score"] += calculate_sonarqube_score(service)
        squads[squad_name]["metrics"]["performance_metrics"] += calculate_performance_metrics(service)
        squads[squad_name]["services"].append(service_id)

    print(f"Oluşturulan Squads: {squads}")

    sorted_squads = calculate_ranks_and_scores(squads, config)
    full_report_id = f"report_{get_current_timestamp()}"  # Dakika ve saniye ile tam rapor ID'si

    report_data = {
        "report_date": get_current_timestamp(),  # Raporun tam tarih ve saati
        "squads": sorted_squads,
        "top_3_squads": [{"squad_name": s["squad_name"], "total_score": s["total_score"]} for s in sorted_squads[:3]]
    }

    try:
        reports_collection.upsert(full_report_id, report_data)
        print(f"Rapor başarıyla oluşturuldu: {full_report_id}")
        return report_data
    except Exception as e:
        print(f"Rapor yazma hatası: {e}")
        return {"error": str(e)}

# Rank ve toplam puan hesaplama işlemi
def calculate_ranks_and_scores(squads, config):
    sorted_squads = []
    for squad_name, data in squads.items():
        # Squad başına toplam puanı hesaplıyoruz
        try:
            total_score = (
                (data["metrics"]["fortify_score"] / data["services_evaluated"]) * config['metrics_weights']['fortify_weight'] +
                (data["metrics"]["defect_score"] / data["services_evaluated"]) * config['metrics_weights']['defect_weight'] +
                (data["metrics"]["rfc_deployment_score"] / data["services_evaluated"]) * config['metrics_weights']['rfc_deployment_weight'] +
                (data["metrics"]["alarm_score"] / data["services_evaluated"]) * config['metrics_weights']['alarm_weight'] +
                (data["metrics"]["sonarqube_score"] / data["services_evaluated"]) * config['metrics_weights']['sonarqube_weight'] +
                (data["metrics"]["performance_metrics"] / data["services_evaluated"]) * config['metrics_weights']['performance_weight'] +
                data["extra_score"]["total"]
            )

            # Hesaplanan skor ile squad'ı ekliyoruz
            sorted_squads.append({
                "squad_name": squad_name,
                "total_score": total_score,
                "services": data["services"],
                "services_evaluated": data["services_evaluated"],
                "metrics": data["metrics"],
                "extra_score": data["extra_score"]
            })
        except KeyError as e:
            print(f"Veri eksikliği nedeniyle {squad_name} için hesaplama yapılamadı: {e}")
        except ZeroDivisionError:
            print(f"'{squad_name}' için 'services_evaluated' sıfır olamaz.")

    # Squad'ları puanlarına göre sıralıyoruz
    sorted_squads.sort(key=lambda x: x["total_score"], reverse=True)

    return sorted_squads
