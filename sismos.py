import os
import requests
import xml.etree.ElementTree as ET

# Configuración
RSS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.atom"
NTFY_TOPIC = "sismoscolombiaalerta998"
SEEN_FILE = "vistos.txt"

print("--- INICIANDO RASTREO ---")

# Cargar eventos ya notificados previamente
seen_ids = set()
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, "r") as f:
        seen_ids = set(f.read().splitlines())
    print(f"Sismos en memoria ({len(seen_ids)} cargados)")

try:
    print(f"Consultando feed USGS...")
    response = requests.get(RSS_URL, timeout=10)
    print(f"Estado HTTP: {response.status_code}")
    
    if response.status_code != 200:
        print("Error consultando el feed RSS")
        exit()

    root = ET.fromstring(response.content)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}

    entries = root.findall('atom:entry', ns)
    print(f"Total de sismos globales leídos en la última hora: {len(entries)}")

    new_seen = set(seen_ids)
    colombia_found = False

    for entry in entries:
        event_id = entry.find('atom:id', ns).text
        title = entry.find('atom:title', ns).text

        # Verificar si menciona a Colombia
        if "colombia" in title.lower():
            colombia_found = True
            print(f"--> ¡ENCONTRADO SISMO EN COLOMBIA!: {title}")
            
            if event_id not in seen_ids:
                print("    Enviando notificación a ntfy...")
                res = requests.post(
                    f"https://ntfy.sh/{NTFY_TOPIC}",
                    data=title.encode('utf-8'),
                    headers={
                        "Priority": "5",
                        "Tags": "warning,rotating_light"
                    }
                )
                print(f"    Respuesta de ntfy: {res.status_code}")
                new_seen.add(event_id)
            else:
                print("    (Este sismo ya fue notificado previamente)")

    if not colombia_found:
        print("No se encontraron sismos en Colombia en la última hora.")

    # Actualizar registro de sismos vistos
    with open(SEEN_FILE, "w") as f:
        for s_id in new_seen:
            f.write(f"{s_id}\n")

    print("--- FIN DEL RASTREO ---")

except Exception as e:
    print(f"Ocurrió un error: {e}")
