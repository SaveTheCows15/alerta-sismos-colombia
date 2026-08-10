import os
import requests
import xml.etree.ElementTree as ET

# Configuración
RSS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.atom"
NTFY_TOPIC = "sismoscolombiaalerta998"
SEEN_FILE = "vistos.txt"

# Cargar eventos ya notificados previamente
seen_ids = set()
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, "r") as f:
        seen_ids = set(f.read().splitlines())

try:
    response = requests.get(RSS_URL, timeout=10)
    if response.status_code != 200:
        print("Error consultando el feed RSS")
        exit()

    root = ET.fromstring(response.content)
    # Namespace de Atom
    ns = {'atom': 'http://www.w3.org/2005/Atom'}

    new_seen = set(seen_ids)

    for entry in root.findall('atom:entry', ns):
        event_id = entry.find('atom:id', ns).text
        title = entry.find('atom:title', ns).text

        # Verificar si menciona a Colombia y si no ha sido enviado antes
        if "colombia" in title.lower() and event_id not in seen_ids:
            print(f"¡Sismo detectado en Colombia!: {title}")
            
            # Enviar notificación urgente a ntfy
            requests.post(
                f"https://ntfy.sh/{NTFY_TOPIC}",
                data=title.encode('utf-8'),
                headers={
                    "Priority": "5",
                    "Tags": "warning,rotating_light"
                }
            )
            new_seen.add(event_id)

    # Actualizar registro de sismos vistos
    with open(SEEN_FILE, "w") as f:
        for s_id in new_seen:
            f.write(f"{s_id}\n")

except Exception as e:
    print(f"Ocurrió un error: {e}")
