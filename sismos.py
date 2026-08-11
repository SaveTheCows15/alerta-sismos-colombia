import os
import requests
import xml.etree.ElementTree as ET

# Configuración
RSS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.atom"
NTFY_TOPIC = "sismoscolombiaalerta998"
# SEEN_FILE = "vistos.txt" # COMENTADO PARA LA PRUEBA (NO GUARDAR MEMORIA)

print("--- INICIANDO RASTREO (MODO DE PRUEBA GLOBAL) ---")

# Para esta prueba, no cargaremos sismos antiguos para que envíe todo lo nuevo
seen_ids = set() 
print("Sismos en memoria (0 cargados para la prueba)")

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

    # Enviaremos solo los primeros 3 para no saturar el teléfono
    limit = 3
    sent_count = 0

    for entry in entries:
        if sent_count >= limit:
            print(f"Límite de prueba alcanzado ({limit}). No se enviarán más.")
            break

        event_id = entry.find('atom:id', ns).text
        title = entry.find('atom:title', ns).text

        # --- PRUEBA GLOBAL: SE ELIMINÓ EL FILTRO DE COLOMBIA ---
        # Enviamos notificación a ntfy de TODO lo que encontremos
        
        print(f"--> ENVIANDO NOTIFICACIÓN GLOBAL: {title}")
        res = requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=title.encode('utf-8'),
            headers={
                "Priority": "5",
                "Tags": "warning,rotating_light",
                "Title": "PRUEBA GLOBAL USGS" # Título especial para saber que es la prueba
            }
        )
        print(f"    Respuesta de ntfy: {res.status_code}")
        sent_count += 1

    if len(entries) == 0:
        print("No se encontraron sismos globales en el feed (¡raro!). Prueba de nuevo en 5 mins.")

    # No guardaremos vistos.txt en la prueba para poder repetirla fácilmente
    # print("--- FIN DEL RASTREO (MODO DE PRUEBA) ---")

except Exception as e:
    print(f"Ocurrió un error: {e}")
