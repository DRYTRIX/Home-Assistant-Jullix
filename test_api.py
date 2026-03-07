"""Manual script to probe Jullix API response shapes (optional).

Usage:
  Set JULLIX_TOKEN env var with your API token, then:
    python test_api.py

For automated tests, run: python -m pytest tests/ -v
"""

import json
import os
import urllib.request

TOKEN = os.environ.get("JULLIX_TOKEN", "")
BASE = "https://mijn.jullix.be"


def get(path):
    if not TOKEN:
        raise SystemExit("Set JULLIX_TOKEN environment variable")
    req = urllib.request.Request(
        BASE + path,
        headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def main():
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

    print("\n=== /api/v1/actual/{}/summary/power ===".format(install_id))
    try:
        data = get("/api/v1/actual/{}/summary/power".format(install_id))
        print(json.dumps(data, indent=2))
    except Exception as e:
        print("Error:", e)

    print("\n=== charger/installation/.../all ===")
    try:
        data = get("/api/v1/charger/installation/{}/all".format(install_id))
        print(json.dumps(data, indent=2))
    except Exception as e:
        print("Error:", e)

    print("\n=== plug/installation/.../all ===")
    try:
        data = get("/api/v1/plug/installation/{}/all".format(install_id))
        print(json.dumps(data, indent=2))
    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    main()
