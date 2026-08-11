import os
import requests
import xml.etree.ElementTree as ET
import time

NTFY_TOPIC = "sismoscolombiaalerta998"
SEEN_FILE = "vistos.txt"

# Feed alternativo que convierte la cuenta de X/Twitter del SGC (@sgccol) en RSS
SGC_TWITTER_RSS = "https://rsshub.app/twitter/user/sgccol"
USGS_RSS = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.atom"

seen_ids = set()
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, "r") as f:
        seen_ids = set(f.read().splitlines())

def enviar_alerta(titulo, detalle):
    headers = {
        "Title": "🚨 ALERTA SISMO COLOMBIA 🚨",
        "Priority": "5",
        "Sound": "warning",
        "Tags": "warning,earthquake"
    }
    # Primera ráfaga
    requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=f"{titulo}\n{detalle}".encode('utf-8'), headers=headers)
    time.sleep(2)
    # Segunda ráfaga de insistencia
    requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=f"¡ALERTA MÁXIMA! {titulo}".encode('utf-8'), headers=headers)

exito_sgc = False
new_seen = set(seen_ids)

# --- INTENTO 1: Twitter del Servicio Geológico Colombiano (@sgccol) ---
try:
    print("Consultando reportes de X/Twitter del SGC...")
    headers_req = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(SGC_TWITTER_RSS, headers=headers_req, timeout=10)
    
    if res.status_code == 200:
        root = ET.fromstring(res.content)
        # Revisamos los últimos tweets
        for item in root.findall('.//item'):
            tweet_id = item.find('guid').text if item.find('guid') is not None else item.find('link').text
            tweet_text = item.find('description').text if item.find('description') is not None else ""
            title_text = item.find('title').text if item.find('title') is not None else ""

            contenido = (title_text + " " + tweet_text).lower()

            # Buscamos tweets que hablen de un sismo recién reportado
            if ("boletín" in contenido or "sismo" in contenido) and tweet_id not in seen_ids:
                print(f"¡NUEVO SISMO PUBLICADO POR EL SGC EN TWITTER!: {title_text}")
                enviar_alerta("Reporte SGC (Oficial)", title_text)
                new_seen.add(tweet_id)
        
        exito_sgc = True
        print("Consulta a X/SGC completada.")

except Exception as e:
    print(f"No se pudo consultar el Twitter del SGC directamente: {e}")

# --- INTENTO 2 (Respaldo USGS): Si X no responde o está saturado ---
if not exito_sgc:
    try:
        print("Usando servidor de respaldo USGS...")
        res_usgs = requests.get(USGS_RSS, timeout=10)
        if res_usgs.status_code == 200:
            root_u = ET.fromstring(res_usgs.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            for entry in root_u.findall('atom:entry', ns):
                event_id = entry.find('atom:id', ns).text
                title = entry.find('atom:title', ns).text
                
                if "colombia" in title.lower() and event_id not in seen_ids:
                    print(f"¡SISMO EN DETECTADO POR USGS!: {title}")
                    enviar_alerta("Alerta Sismológica", title)
                    new_seen.add(event_id)
    except Exception as e:
        print(f"Error en respaldo USGS: {e}")

# Guardar historial
with open(SEEN_FILE, "w") as f:
    for s_id in new_seen:
        f.write(f"{s_id}\n")

print("Ejecución finalizada con éxito.")
