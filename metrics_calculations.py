# Fortify puanını hesaplayan fonksiyon
def calculate_fortify_score(service):
    fortify_scans = service.get("fortify_scans", {})
    if not fortify_scans:
        return 100
    severity_weight = {"critical": -10, "high": -7, "medium": -3, "low": -1}
    severity = fortify_scans.get("severity", "low")
    count = fortify_scans.get("count", 0)
    score = 100 + severity_weight.get(severity, 0) * count
    return max(score, 0)

# Defect puanını hesaplayan fonksiyon
def calculate_defect_score(service):
    defects = service.get("defect", [])
    if not defects:
        return 100
    score = 100
    for defect in defects:
        if not defect.get("sla_met", True):
            score -= 10
    return max(score, 0)

# RFC/Deployment puanını hesaplayan fonksiyon
def calculate_rfc_deployment_score(service):
    changes = service.get("changes", [])
    score = 100
    for change in changes:
        if change.get("status") == "rollback":
            score -= 20
        elif change.get("deployments", 0) > 3:
            score -= 5
    return max(score, 0)

# Alarm puanını hesaplayan fonksiyon
def calculate_alarm_score(service):
    alarms = service.get("alarming", [])
    return 50 if len(alarms) > 3 else 100

# SonarQube puanını hesaplayan fonksiyon
def calculate_sonarqube_score(service):
    sonar_scan = service.get("sonarqube_scans", {})
    coverage = sonar_scan.get("coverage", 100)
    return 70 if coverage < 80 else 100

# Performans metriklerini hesaplayan fonksiyon
def calculate_performance_metrics(service):
    performance = service.get("performance_metrics", {})
    response_time = performance.get("response_time", 100)
    error_ratio = performance.get("error_ratio", 1)
    return 50 if response_time > 300 or error_ratio > 1.0 else 100