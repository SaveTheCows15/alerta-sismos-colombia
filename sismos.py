import os
import requests

# API oficial de EMSC (Filtro exacto para coordenadas de Colombia)
EMSC_URL = "https://www.seismicportal.eu/fdsnws/event/1/query?format=json&minlat=-4.5&maxlat=13.5&minlon=-79.5&maxlon=-66.8&limit=10"
NTFY_TOPIC = "sismoscolombiaalerta998"
SEEN_FILE = "vistos.txt"

print("--- INICIANDO RASTREO (COLOMBIA - RED SGC/EMSC) ---")

seen_ids = set()
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, "r") as f:
        seen_ids = set(f.read().splitlines())
    print(f"Sismos en memoria ({len(seen_ids)} cargados)")

try:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    print("Consultando servidor de sismicidad...")
    response = requests.get(EMSC_URL, headers=headers, timeout=10)
    print(f"Estado HTTP: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        features = data.get('features', [])
        print(f"Total de sismos leídos en Colombia: {len(features)}")
        
        new_seen = set(seen_ids)
        
        for feature in features:
            props = feature.get('properties', {})
            event_id = str(feature.get('id') or props.get('unid') or '')
            
            # Datos del sismo
            lugar = props.get('flynn_region') or 'Colombia'
            magnitud = props.get('mag') or 'N/A'
            profundidad = props.get('depth') or 'N/A'
            hora = props.get('time', '').replace('T', ' ')[:16]

            if event_id and event_id not in seen_ids:
                titulo = f"M {magnitud} - {lugar}"
                detalle = f"Profundidad: {profundidad} km\nHora: {hora} UTC"
                
                print(f"--> ¡NUEVO SISMO DETECTADO!: {titulo}")
                print("    Enviando notificación a ntfy...")
                
                mensaje = f"🚨 ALERTA SISMO COLOMBIA\n{titulo}\n{detalle}"
                
                res = requests.post(
                    f"https://ntfy.sh/{NTFY_TOPIC}",
                    data=mensaje.encode('utf-8'),
                    headers={
                        "Priority": "5",
                        "Tags": "warning,rotating_light"
                    }
                )
                print(f"    Respuesta de ntfy: {res.status_code}")
                new_seen.add(event_id)

        # Actualizar memoria
        with open(SEEN_FILE, "w") as f:
            for s_id in new_seen:
                f.write(f"{s_id}\n")

    else:
        print("El servidor no devolvió respuesta 200.")

    print("--- FIN DEL RASTREO ---")

except Exception as e:
    print(f"Error en la consulta: {e}")
