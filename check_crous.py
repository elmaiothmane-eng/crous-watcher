import requests
import json
import os
import sys

CROUS_URL = "https://trouverunlogement.lescrous.fr/tools/47/search?bounds=3.8070597_43.6533542_3.9413208_43.5667088&locationName=Montpellier"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "crous-changeme")
STATE_FILE = "previous_listings.json"

def fetch_listings():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    r = requests.get(CROUS_URL, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

def extract_items(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("features", "results", "items", "residences", "logements", "data"):
            if key in data and isinstance(data[key], list):
                return data[key]
    return []

def get_id(item):
    props = item.get("properties", item) if isinstance(item, dict) else {}
    for key in ("id", "cle", "codeLogement", "identifiant", "uid"):
        if key in props:
            return str(props[key])
    return str(hash(json.dumps(item, sort_keys=True)))

def get_label(item):
    props = item.get("properties", item) if isinstance(item, dict) else {}
    parts = []
    for key in ("libelle", "nom", "adresse", "address", "ville", "typeLogement", "loyer", "rent"):
        if key in props:
            parts.append(str(props[key]))
    return " - ".join(parts) if parts else "Nouveau logement disponible"

def send_notification(title, message):
    headers = {"Title": title.encode("utf-8"), "Click": "https://trouverunlogement.lescrous.fr/"}
    requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=message.encode("utf-8"), headers=headers, timeout=15)

def load_previous_ids():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return set(json.load(f))
    return set()

def save_ids(ids):
    with open(STATE_FILE, "w") as f:
        json.dump(sorted(ids), f)

def main():
    try:
        data = fetch_listings()
    except Exception as e:
        print(f"Erreur requête: {e}")
        sys.exit(1)

    items = extract_items(data)
    print(f"{len(items)} logement(s) trouvé(s).")

    current_ids = set()
    id_to_item = {}
    for item in items:
        iid = get_id(item)
        current_ids.add(iid)
        id_to_item[iid] = item

    previous_ids = load_previous_ids()
    new_ids = current_ids - previous_ids

    if previous_ids and new_ids:
        for iid in new_ids:
            label = get_label(id_to_item[iid])
            send_notification("Nouveau logement CROUS !", label)
            print(f"Notif envoyée: {label}")
    elif not previous_ids:
        print("Premier run: état initialisé, pas de notif.")
    else:
        print("Rien de nouveau.")

    save_ids(current_ids)

if __name__ == "__main__":
    main()
