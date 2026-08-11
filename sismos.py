import os
import requests
import xml.etree.ElementTree as ET

# Configuración para el Servicio Geológico Colombiano (SGC)
RSS_URL = "https://sismos.sgc.gov.co/rss/sismos.xml"
NTFY_TOPIC = "sismoscolombiaalerta998"
SEEN_FILE = "vistos.txt"

print("--- INICIANDO RASTREO (SGC COLOMBIA) ---")

# Cargar sismos ya notificados
seen_ids = set()
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, "r") as f:
        seen_ids = set(f.read().splitlines())
    print(f"Sismos en memoria ({len(seen_ids)} cargados)")

try:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    print("Consultando feed oficial del SGC...")
    response = requests.get(RSS_URL, headers=headers, timeout=10)
    print(f"Estado HTTP: {response.status_code}")
    
    if response.status_code != 200:
        print("Error consultando el feed del SGC")
        exit()

    root = ET.fromstring(response.content)
    # Los items en la RSS del SGC están bajo channel -> item
    items = root.findall('./channel/item')
    print(f"Total de sismos leídos del SGC: {len(items)}")

    new_seen = set(seen_ids)

    for item in items:
        # Usamos el GUID o Link como ID único del sismo
        guid_elem = item.find('guid')
        link_elem = item.find('link')
        event_id = guid_elem.text if guid_elem is not None else (link_elem.text if link_elem is not None else "")
        
        title_elem = item.find('title')
        description_elem = item.find('description')
        
        title = title_elem.text if title_elem is not None else "Sismo detectado en Colombia"
        description = description_elem.text if description_elem is not None else ""

        if event_id and event_id not in seen_ids:
            print(f"--> ¡NUEVO SISMO REPORTADO POR SGC!: {title}")
            print("    Enviando notificación urgente a ntfy...")
            
            # Enviar notificación a ntfy con información del SGC
            res = requests.post(
                f"https://ntfy.sh/{NTFY_TOPIC}",
                data=f"{title}\n{description}".encode('utf-8'),
                headers={
                    "Priority": "5",
                    "Tags": "warning,rotating_light",
                    "Title": "🚨 ALERTA SGC COLOMBIA"
                }
            )
            print(f"    Respuesta de ntfy: {res.status_code}")
            new_seen.add(event_id)

    if len(new_seen) == len(seen_ids):
        print("No hay sismos nuevos reportados por el SGC.")

    # Guardar historial actualizado
    with open(SEEN_FILE, "w") as f:
        for s_id in new_seen:
            f.write(f"{s_id}\n")

    print("--- FIN DEL RASTREO ---")

except Exception as e:
    print(f"Ocurrió un error leyendo el SGC: {e}")
