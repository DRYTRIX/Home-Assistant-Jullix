"""Test Jullix API with provided JWT to see actual response structures."""
import json
import urllib.request

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl9pZCI6IjR2cHFLQ3FKZWpwWFVmZFpYb3Y4c2Z6QUg4cnlmcUhCOWZ1aFdYWWxhRldQelJuZ1Z6ZjZvRDU2elZ0WTNWWjEiLCJ1c2VyX2lkIjo2MTksImRlc2NyaXB0aW9uIjoiV2ViQXBwIiwiY3JlYXRlZCI6IjIwMjUtMDctMjlUMDc6MTA6MTMuNTgzNDQ1In0.YQ9bxpBOxPeRKnBptRSOvEJPty_1ZQAWtPR5UatGp40"
BASE = "https://mijn.jullix.be"

def get(path):
    req = urllib.request.Request(BASE + path, headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

def main():
    # 1. Get installations
    print("=== /api/v1/installation/all ===")
    try:
        data = get("/api/v1/installation/all")
        print("Type:", type(data))
        if isinstance(data, list) and data:
            inst = data[0]
            print("First install keys:", list(inst.keys()))
            install_id = inst.get("id") or inst.get("install_id")
            print("First install id:", install_id)
        elif isinstance(data, dict):
            print("Keys:", list(data.keys()))
            insts = data.get("installations") or []
            install_id = data.get("id") or (insts[0].get("id") if insts else None)
        else:
            install_id = None
    except Exception as e:
        print("Error:", e)
        install_id = None

    if not install_id:
        print("No install_id")
        return

    # 2. Power summary
    print("\n=== /api/v1/actual/{}/summary/power ===".format(install_id))
    try:
        data = get("/api/v1/actual/{}/summary/power".format(install_id))
        print(json.dumps(data, indent=2))
    except Exception as e:
        print("Error:", e)

    # 3. Detail battery
    print("\n=== detail/battery ===")
    try:
        data = get("/api/v1/actual/{}/detail/battery".format(install_id))
        print(json.dumps(data, indent=2))
    except Exception as e:
        print("Error:", e)

    # 4. Detail solar
    print("\n=== detail/solar ===")
    try:
        data = get("/api/v1/actual/{}/detail/solar".format(install_id))
        print(json.dumps(data, indent=2))
    except Exception as e:
        print("Error:", e)

    # 5. Detail grid
    print("\n=== detail/grid ===")
    try:
        data = get("/api/v1/actual/{}/detail/grid".format(install_id))
        print(json.dumps(data, indent=2))
    except Exception as e:
        print("Error:", e)

    # 6. Detail home
    print("\n=== detail/home ===")
    try:
        data = get("/api/v1/actual/{}/detail/home".format(install_id))
        print(json.dumps(data, indent=2))
    except Exception as e:
        print("Error:", e)

    # 7. Detail metering
    print("\n=== detail/metering ===")
    try:
        data = get("/api/v1/actual/{}/detail/metering".format(install_id))
        print(json.dumps(data, indent=2))
    except Exception as e:
        print("Error:", e)

    # 8. Chargers
    print("\n=== charger/installation/.../all ===")
    try:
        data = get("/api/v1/charger/installation/{}/all".format(install_id))
        print(json.dumps(data, indent=2))
    except Exception as e:
        print("Error:", e)

    # 9. Plugs
    print("\n=== plug/installation/.../all ===")
    try:
        data = get("/api/v1/plug/installation/{}/all".format(install_id))
        print(json.dumps(data, indent=2))
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()
