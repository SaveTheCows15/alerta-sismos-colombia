import os
import requests
import time

# Endpoint público del Servicio Geológico Colombiano (SGC)
SGC_API_URL = "https://sgc.gov.co/api/sismos/ultimos"
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
    print("Consultando eventos en el Servicio Geológico Colombiano (SGC)...")
    response = requests.get(SGC_API_URL, headers=headers, timeout=15)
    
    if response.status_code != 200:
        print(f"Error consultando el SGC. Código de respuesta: {response.status_code}")
        exit()

    datos = response.json()
    new_seen = set(seen_ids)

    # Revisamos los 5 eventos sismológicos más recientes del SGC
    for sismo in datos[:5]:
        # Generar un ID único combinando la fecha/hora o ID del registro
        event_id = str(sismo.get('id', sismo.get('fecha_utc', sismo.get('fecha'))))
        municipio = sismo.get('municipio', sismo.get('localizacion', 'Colombia'))
        magnitud = sismo.get('magnitud', 'N/A')
        profundidad = sismo.get('profundidad', 'Superficial')

        if event_id and event_id not in seen_ids:
            mensaje = f"Magnitud: {magnitud} M | Ubicación: {municipio} | Profundidad: {profundidad}"
            print(f"¡NUEVO SISMO DETECTADO!: {mensaje}")

            # Parámetros para forzar sonido e insistencia en ntfy
            ntfy_headers = {
                "Title": f"🚨 ALERTA SISMO COLOMBIA (M{magnitud}) 🚨",
                "Priority": "5",               # Máxima prioridad en iOS/Android
                "Sound": "warning",            # Sonido de sirena/alarma
                "Tags": "warning,earthquake"   # Íconos de alerta
            }

            # Ráfaga 1: Notificación inicial
            requests.post(
                f"https://ntfy.sh/{NTFY_TOPIC}", 
                data=mensaje.encode('utf-8'), 
                headers=ntfy_headers
            )
            
            # Esperar 2 segundos y enviar Ráfaga 2 para mayor insistencia auditiva
            time.sleep(2)
            requests.post(
                f"https://ntfy.sh/{NTFY_TOPIC}", 
                data=f"¡REVISA TU ENTORNO! {mensaje}".encode('utf-8'), 
                headers=ntfy_headers
            )

            new_seen.add(event_id)

    # Actualizar la lista de eventos procesados
    with open(SEEN_FILE, "w") as f:
        for s_id in new_seen:
            f.write(f"{s_id}\n")

except Exception as e:
    print(f"Ocurrió un error inesperado al procesar la alerta: {e}")
