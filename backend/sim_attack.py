import requests
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

base_url = "http://127.0.0.1:8000/api/v1"

accounts = [
    {"email": "harshit2500sharma@gmail.com", "password": "Admin@123"},
]

token = None
logged_role = None
for acc in accounts:
    try:
        resp = requests.post(f"{base_url}/auth/login-password", json=acc, timeout=5)
        if resp.status_code == 200:
            token = resp.json()["access_token"]
            logged_role = resp.json()["user"]["role"]
            print(f"OK Logged in as: {acc['email']} (role: {logged_role})")
            break
        else:
            print(f"FAIL {acc['email']} / {acc['password']}: {resp.status_code} - {resp.json().get('detail','')}")
    except Exception as e:
        print(f"ERROR connecting: {e}")
        break

if not token:
    print("Could not login. Exiting.")
    exit(1)

headers = {"Authorization": f"Bearer {token}"}

if logged_role != "admin":
    print(f"Logged in as {logged_role}, not admin. Simulation requires admin. Skipping sim.")
else:
    print("\nRunning attack simulation...")
    sim_resp = requests.post(f"{base_url}/cases/simulate-attack", headers=headers, timeout=30)
    print(f"Simulation status: {sim_resp.status_code}")
    print(f"Simulation response: {sim_resp.text}")

print("\nFetching clusters...")
cluster_resp = requests.get(f"{base_url}/cases/clusters", headers=headers, timeout=10)
print(f"Clusters status: {cluster_resp.status_code}")
cluster_data = cluster_resp.json()
features = cluster_data.get("features", [])
print(f"Cluster features count: {len(features)}")
for f in features:
    props = f.get("properties", {})
    coords = f.get("geometry", {}).get("coordinates", [])
    print(f"  {props.get('entity_type')}: {props.get('entity_value')} -> {len(props.get('case_numbers', []))} cases, {len(coords)} coordinates")

print("\nFetching spatial data...")
spatial_resp = requests.get(f"{base_url}/cases/spatial", headers=headers, timeout=10)
spatial_data = spatial_resp.json()
print(f"Total cases on map: {len(spatial_data.get('features', []))}")
