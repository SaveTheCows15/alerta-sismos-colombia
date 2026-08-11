import os
import requests

# URL oficial y pública del visor del Servicio Geológico Colombiano
SGC_URL = "https://sgc.gov.co/api/sismos/ultimos"
# URL de respaldo oficial del SGC (GeoServer público)
SGC_URL_ALT = "https://backend.sgc.gov.co/api/v1/sismos"
NTFY_TOPIC = "sismoscolombiaalerta998"
SEEN_FILE = "vistos.txt"

seen_ids = set()
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, "r") as f:
        seen_ids = set(f.read().splitlines())

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

try:
    print("--- INICIANDO RASTREO SGC ---")
    
    # Intentar primera URL
    response = requests.get(SGC_URL, headers=headers, timeout=10)
    
    # Si la primera da 404, intentar la URL alternativa del SGC
    if response.status_code != 200:
        print(f"URL 1 dio estado {response.status_code}. Intentando endpoint alternativo del SGC...")
        response = requests.get(SGC_URL_ALT, headers=headers, timeout=10)

    print(f"Código de respuesta HTTP: {response.status_code}")

    if response.status_code != 200:
        print("No se pudo conectar a los servidores del SGC en este momento.")
        exit(0)

    datos = response.json()
    eventos = datos if isinstance(datos, list) else datos.get('features', datos.get('data', []))
    print(f"Sismos encontrados: {len(eventos)}")

    new_seen = set(seen_ids)

    for i, sismo in enumerate(eventos[:5]):
        prop = sismo.get('properties', sismo)
        
        event_id = str(prop.get('id') or prop.get('eventId') or prop.get('fecha_utc') or f"evt_{i}")
        municipio = prop.get('municipio') or prop.get('localizacion') or 'Colombia'
        magnitud = prop.get('magnitud') or prop.get('mag') or 'N/A'

        print(f"[Sismo #{i+1}] ID: {event_id} | {municipio} | M{magnitud}")

        if event_id not in seen_ids:
            mensaje = f"Sismo M{magnitud} en {municipio} (Fuente: SGC)"
            print(f"--> ¡ENVIANDO ALERTA A NTFY!: {mensaje}")
            
            requests.post(
                f"https://ntfy.sh/{NTFY_TOPIC}",
                data=mensaje.encode('utf-8'),
                headers={
                    "Title": "🚨 ALERTA SISMO SGC 🚨",
                    "Priority": "5",
                    "Sound": "warning",
                    "Tags": "warning,rotating_light"
                }
            )
            new_seen.add(event_id)
        else:
            print("--> Evento ya registrado en vistos.txt")

    with open(SEEN_FILE, "w") as f:
        for s_id in new_seen:
            f.write(f"{s_id}\n")

    print("--- PROCESO COMPLETADO ---")

except Exception as e:
    print(f"Error durante el rastreo: {e}")
