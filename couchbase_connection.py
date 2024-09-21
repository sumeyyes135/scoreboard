from couchbase.cluster import Cluster
from couchbase.auth import PasswordAuthenticator
from couchbase.options import ClusterOptions, ClusterTimeoutOptions
from datetime import timedelta
import traceback
from config_loader import load_config

# Config dosyasını yüklüyoruz
config = load_config()

# Couchbase'e bağlanma fonksiyonu
def connect_to_couchbase():
    auth = PasswordAuthenticator(config['database']['username'], config['database']['password'])
    options = ClusterOptions(auth, timeout_options=ClusterTimeoutOptions(kv_timeout=timedelta(seconds=10)))
    try:
        cluster = Cluster(config['database']['endpoint'], options)
        cluster.wait_until_ready(timedelta(seconds=10))
        bucket = cluster.bucket(config['database']['bucket_name'])
        return cluster, bucket
    except Exception as e:
        traceback.print_exc()
        return None, None