import os
import requests

# Endpoint oficial de ArcGIS encontrado
ARCGIS_URL = "https://services1.arcgis.com/Og2nrTKe5bptW02d/arcgis/rest/services/MAPAGEOLOGIA/FeatureServer/1/query?where=1%3D1&outFields=*&outSR=4326&f=json"
NTFY_TOPIC = "sismoscolombiaalerta998"
SEEN_FILE = "vistos.txt"

print("--- INICIANDO RASTREO (ARCGIS REST API) ---")

# Cargar sismos ya procesados
seen_ids = set()
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, "r") as f:
        seen_ids = set(f.read().splitlines())
    print(f"Registros en memoria ({len(seen_ids)} cargados)")

try:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    print("Consultando servidor ArcGIS...")
    response = requests.get(ARCGIS_URL, headers=headers, timeout=12)
    print(f"Estado HTTP: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        features = data.get('features', [])
        print(f"Total de registros leídos desde ArcGIS: {len(features)}")
        
        new_seen = set(seen_ids)
        
        for feature in features:
            attrs = feature.get('attributes', {})
            
            # Obtener ID único del registro
            object_id = str(attrs.get('OBJECTID') or attrs.get('FID') or attrs.get('GlobalID') or '')
            
            # Mapear campos habitualmente presentes en capas sísmicas o geológicas
            municipio = attrs.get('MUNICIPIO') or attrs.get('LOCALIZACION') or attrs.get('Nombre') or attrs.get('TITLE') or 'Colombia'
            departamento = attrs.get('DEPARTAMENTO') or ''
            magnitud = attrs.get('MAGNITUD') or attrs.get('MAGNITUDE') or attrs.get('M') or 'N/A'
            profundidad = attrs.get('PROFUNDIDAD') or attrs.get('DEPTH') or 'N/A'

            if object_id and object_id not in seen_ids:
                titulo = f"M {magnitud} - {municipio}"
                if departamento:
                    titulo += f", {departamento}"
                
                detalle = f"Profundidad: {profundidad} km" if profundidad != 'N/A' else "Reporte de sensor SGC"

                print(f"--> ¡NUEVO EVENTO DETECTADO!: {titulo}")
                print("    Enviando notificación a ntfy...")
                
                # Enviar notificación urgente
                res = requests.post(
                    f"https://ntfy.sh/{NTFY_TOPIC}",
                    data=f"{titulo}\n{detalle}".encode('utf-8'),
                    headers={
                        "Priority": "5",
                        "Tags": "warning,rotating_light",
                        "Title": "🚨 ALERTA SGC (ARCGIS)"
                    }
                )
                print(f"    Respuesta de ntfy: {res.status_code}")
                new_seen.add(object_id)

        # Actualizar lista de vistos
        with open(SEEN_FILE, "w") as f:
            for s_id in new_seen:
                f.write(f"{s_id}\n")

    else:
        print("No se pudo obtener respuesta del servidor ArcGIS.")

    print("--- FIN DEL RASTREO ---")

except Exception as e:
    print(f"Ocurrió un error consultando ArcGIS: {e}")
