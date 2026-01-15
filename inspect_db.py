import requests
from requests.auth import HTTPBasicAuth

def query_sql(sql, endpoint="http://localhost:8001", ns="test", db="test"):
    url = f"{endpoint}/sql"
    headers = {
        "Accept": "application/json",
        "NS": ns,
        "DB": db
    }
    try:
        response = requests.post(url, data=sql, headers=headers, auth=HTTPBasicAuth("root", "root"))
        if response.status_code == 200:
            return response.json()
        print(f"Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")
    return None

def scan_all(endpoint="http://localhost:8001"):
    print(f"🔍 Scanning SurrealDB at {endpoint}...")
    
    # 1. Get Namespaces
    # Note: "INFO FOR KV" might require being in a context or root?
    # Let's try to just guess specific common ones or rely on `INFO FOR KV` if supported.
    # SurrealDB 2.x `INFO FOR KV` should work setup-less?
    
    res = query_sql("INFO FOR KV;")
    namespaces = []
    if res and res[0]['status'] == 'OK':
         namespaces = list(res[0]['result'].get('namespaces', {}).keys())
    
    if not namespaces:
        # Fallback: check 'lumina', 'test', 'root'
        namespaces = ['lumina', 'test', 'default']

    print(f"Found Namespaces: {namespaces}")

    for ns in namespaces:
        # 2. Get Databases
        res = query_sql(f"USE NS {ns}; INFO FOR NS;", ns=ns)
        dbs = []
        if res and res[0]['status'] == 'OK' and res[0]['result']:
             dbs = list(res[0]['result'].get('databases', {}).keys())
        
        for db in dbs:
            # 3. Get Tables
            res = query_sql(f"USE NS {ns}; USE DB {db}; INFO FOR DB;", ns=ns, db=db)
            tables = []
            if res and res[0]['status'] == 'OK' and res[0]['result']:
                 tables = list(res[0]['result'].get('tables', {}).keys())
            
            print(f"  📂 [{ns} :: {db}] Tables: {tables}")
            
            for tb in tables:
                # 4. Count
                res = query_sql(f"USE NS {ns}; USE DB {db}; SELECT count() FROM {tb};", ns=ns, db=db)
                count = 0
                if res and res[0]['status'] == 'OK':
                    try:
                        val = res[0]['result'][0]
                        count = val['count']
                    except:
                        pass
                
                if count > 0:
                    print(f"     ✅ {tb}: {count} records")

if __name__ == "__main__":
    scan_all()
