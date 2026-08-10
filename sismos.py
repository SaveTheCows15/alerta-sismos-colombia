import os
import requests
import xml.etree.ElementTree as ET
import time

# Feed RSS/Atom global en tiempo real de USGS (Sin bloqueos de IP)
RSS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.atom"
NTFY_TOPIC = "sismoscolombiaalerta998"
SEEN_FILE = "vistos.txt"

seen_ids = set()
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, "r") as f:
        seen_ids = set(f.read().splitlines())

try:
    print("Iniciando monitoreo de sismos para Colombia...")
    response = requests.get(RSS_URL, timeout=15)
    
    if response.status_code != 200:
        print(f"Error consultando el servidor sismológico: {response.status_code}")
        exit(0)

    root = ET.fromstring(response.content)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    new_seen = set(seen_ids)

    for entry in root.findall('atom:entry', ns):
        event_id = entry.find('atom:id', ns).text
        title = entry.find('atom:title', ns).text  # Ej: "M 4.2 - 15 km SW of Los Santos, Colombia"

        # Filtro exclusivo para sismos con epicentro o impacto en Colombia
        if "colombia" in title.lower() and event_id not in seen_ids:
            print(f"¡SISMO DETECTADO EN COLOMBIA!: {title}")
            
            headers = {
                "Title": "🚨 ALERTA SISMO COLOMBIA 🚨",
                "Priority": "5",               # Máxima prioridad para sonido continuo
                "Sound": "warning",            # Sonido de alarma/sirena
                "Tags": "warning,earthquake"
            }
            
            # Enviar primera notificación de alerta
            requests.post(
                f"https://ntfy.sh/{NTFY_TOPIC}", 
                data=f"Detalle: {title}".encode('utf-8'), 
                headers=headers
            )
            
            # Segunda ráfaga a los 2 segundos para asegurar el despertar
            time.sleep(2)
            requests.post(
                f"https://ntfy.sh/{NTFY_TOPIC}", 
                data=f"¡REVISA TU ENTORNO! {title}".encode('utf-8'), 
                headers=headers
            )

            new_seen.add(event_id)

    with open(SEEN_FILE, "w") as f:
        for s_id in new_seen:
            f.write(f"{s_id}\n")

    print("Monitoreo ejecutado correctamente sin fallos.")

except Exception as e:
    print(f"Error inesperado procesando los datos: {e}")
