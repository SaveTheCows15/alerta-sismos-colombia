import os
import requests

# Configuración
SGC_JSON_URL = "https://sismo.sgc.gov.co/api/v1/sismos/ultimos"
NTFY_TOPIC = "sismoscolombiaalerta998"
SEEN_FILE = "vistos.txt"

# Cargar eventos ya notificados previamente
seen_ids = set()
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, "r") as f:
        seen_ids = set(f.read().splitlines())

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

try:
    response = requests.get(SGC_JSON_URL, headers=headers, timeout=10)
    if response.status_code != 200:
        print(f"Error consultando el SGC: {response.status_code}")
        exit()

    datos = response.json()
    new_seen = set(seen_ids)

    # Si la respuesta es una lista de eventos del SGC
    if isinstance(datos, list):
        for sismo in datos[:5]:
            # Extraer ID y datos del evento
            event_id = str(sismo.get('id', sismo.get('fechaUtc', sismo.get('fecha'))))
            municipio = sismo.get('municipio', sismo.get('localizacion', 'Colombia'))
            magnitud = sismo.get('magnitud', 'N/A')

            # Verificar si no ha sido enviado antes
            if event_id and event_id not in seen_ids:
                mensaje = f"Sismo M{magnitud} en {municipio} (Fuente: SGC)"
                print(f"¡Sismo detectado en Colombia!: {mensaje}")
                
                # Enviar notificación urgente a ntfy
                requests.post(
                    f"https://ntfy.sh/{NTFY_TOPIC}",
                    data=mensaje.encode('utf-8'),
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
