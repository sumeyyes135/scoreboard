from couchbase.cluster import Cluster
from couchbase.auth import PasswordAuthenticator
from couchbase.options import ClusterOptions, ClusterTimeoutOptions
from datetime import timedelta
import traceback

# Capella bağlantı ayarları
endpoint = "couchbases://cb.ekkz0hb5oum6mphw.cloud.couchbase.com"
username = "scoreboard"
password = "Scoreboard135!"

# Couchbase'e bağlanma fonksiyonu
def connect_to_couchbase():
    auth = PasswordAuthenticator(username, password)
    options = ClusterOptions(auth, timeout_options=ClusterTimeoutOptions(kv_timeout=timedelta(seconds=10)))
    try:
        cluster = Cluster(endpoint, options)
        cluster.wait_until_ready(timedelta(seconds=10))
        bucket = cluster.bucket("scoreboard")
        return cluster, bucket  # Hem cluster hem bucket'ı döndür
    except Exception as e:
        traceback.print_exc()
        return None, None