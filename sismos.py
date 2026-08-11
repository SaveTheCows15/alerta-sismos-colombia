import os
import requests

# Endpoint público del Servicio Geológico Colombiano
SGC_JSON_URL = "https://sismo.sgc.gov.co/api/v1/sismos/ultimos"
NTFY_TOPIC = "sismoscolombiaalerta998"
SEEN_FILE = "vistos.txt"

# Cargar eventos ya notificados
seen_ids = set()
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, "r") as f:
        seen_ids = set(f.read().splitlines())

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

try:
    print("--- INICIANDO DIAGNÓSTICO SGC ---")
    response = requests.get(SGC_JSON_URL, headers=headers, timeout=10)
    print(f"Código de respuesta HTTP: {response.status_code}")

    if response.status_code != 200:
        print("El servidor del SGC no respondió con estado 200 OK.")
        exit(0)

    datos = response.json()
    print(f"Tipo de datos recibidos: {type(datos)}")

    # Normalizar lista de datos
    eventos = datos if isinstance(datos, list) else datos.get('features', datos.get('data', []))
    print(f"Cantidad de sismos encontrados en la lista: {len(eventos)}")

    new_seen = set(seen_ids)

    for i, sismo in enumerate(eventos[:5]):
        prop = sismo.get('properties', sismo)
        
        # Probar múltiples posibilidades de nombres de claves que usa el SGC
        event_id = str(prop.get('id') or prop.get('eventId') or prop.get('fechaUtc') or prop.get('fecha') or f"evento_{i}")
        municipio = prop.get('municipio') or prop.get('localizacion') or prop.get('nombre') or 'Colombia'
        magnitud = prop.get('magnitud') or prop.get('mag') or 'N/A'

        print(f"\n[Sismo #{i+1}] ID: {event_id} | Ubicación: {municipio} | Magnitud: {magnitud}")

        if event_id not in seen_ids:
            mensaje = f"Sismo M{magnitud} en {municipio} (Fuente: SGC)"
            print(f"--> ¡EVENTO NUEVO DETECTADO! Enviando alerta a ntfy: {mensaje}")
            
            res_ntfy = requests.post(
                f"https://ntfy.sh/{NTFY_TOPIC}",
                data=mensaje.encode('utf-8'),
                headers={
                    "Title": "🚨 ALERTA SISMO SGC 🚨",
                    "Priority": "5",
                    "Sound": "warning",
                    "Tags": "warning,rotating_light"
                }
            )
            print(f"    Respuesta de ntfy: {res_ntfy.status_code}")
            new_seen.add(event_id)
        else:
            print("--> Evento ya notificado anteriormente. Se omite.")

    # Guardar historial
    with open(SEEN_FILE, "w") as f:
        for s_id in new_seen:
            f.write(f"{s_id}\n")

    print("\n--- DIAGNÓSTICO FINALIZADO CON ÉXITO ---")

except Exception as e:
    print(f"Ocurrió un error inesperado durante el rastreo: {e}")
