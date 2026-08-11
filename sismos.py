import os
import requests
import xml.etree.ElementTree as ET
import time

NTFY_TOPIC = "sismoscolombiaalerta998"
SEEN_FILE = "vistos.txt"

# Endpoint de datos abiertos del SGC y respaldo del USGS
SGC_GEOJSON = "https://sismo.sgc.gov.co/api/v1/sismos/ultimos"
USGS_RSS = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.atom"

seen_ids = set()
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, "r") as f:
        seen_ids = set(f.read().splitlines())

def enviar_alerta(titulo, detalle):
    headers = {
        "Title": f"🚨 {titulo} 🚨",
        "Priority": "5",
        "Sound": "warning",
        "Tags": "warning,earthquake"
    }
    # Ráfaga 1
    requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=detalle.encode('utf-8'), headers=headers)
    time.sleep(2)
    # Ráfaga 2 de insistencia
    requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=f"¡ALERTA MÁXIMA! {detalle}".encode('utf-8'), headers=headers)

new_seen = set(seen_ids)
exito = False

# --- INTENTO 1: Servicio Geológico Colombiano (API Directa) ---
try:
    print("Consultando Servicio Geológico Colombiano (SGC)...")
    headers_req = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json"
    }
    res = requests.get(SGC_GEOJSON, headers=headers_req, timeout=10)
    
    if res.status_code == 200:
        datos = res.json()
        # Procesar si la respuesta viene como lista o diccionario
        eventos = datos if isinstance(datos, list) else datos.get('features', datos.get('data', []))
        
        for sismo in eventos[:5]:
            # Extraer propiedades según estructura JSON
            prop = sismo.get('properties', sismo)
            event_id = str(prop.get('id', prop.get('eventId', prop.get('fecha_utc'))))
            municipio = prop.get('municipio', prop.get('localizacion', 'Colombia'))
            magnitud = prop.get('magnitud', prop.get('mag', 'N/A'))
            
            if event_id and event_id not in seen_ids:
                msg = f"Sismo M{magnitud} en {municipio} (Fuente: SGC)"
                print(f"¡NUEVO SISMO SGC!: {msg}")
                enviar_alerta("ALERTA SISMO COLOMBIA (SGC)", msg)
                new_seen.add(event_id)
        
        exito = True
        print("Consulta a SGC exitosa.")
except Exception as e:
    print(f"Aviso: SGC no disponible en esta iteración ({e}). Usando fuente de respaldo...")

# --- INTENTO 2: Respaldo USGS (Garantiza que nunca falle la ejecución) ---
if not exito:
    try:
        print("Consultando respaldo USGS...")
        res_u = requests.get(USGS_RSS, timeout=10)
        if res_u.status_code == 200:
            root = ET.fromstring(res_u.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            for entry in root.findall('atom:entry', ns):
                event_id = entry.find('atom:id', ns).text
                title = entry.find('atom:title', ns).text
                
                if "colombia" in title.lower() and event_id not in seen_ids:
                    print(f"¡NUEVO SISMO USGS!: {title}")
                    enviar_alerta("ALERTA SISMO COLOMBIA", title)
                    new_seen.add(event_id)
            print("Consulta a USGS exitosa.")
    except Exception as e:
        print(f"Error procesando respaldo: {e}")

# Guardar historial
with open(SEEN_FILE, "w") as f:
    for s_id in new_seen:
        f.write(f"{s_id}\n")

print("Ejecución finalizada con éxito.")
