import os
import requests
from datetime import datetime

# API oficial de Sismicidad SGC en la nube de ArcGIS
ARCGIS_SISMOS_URL = (
    "https://services1.arcgis.com/Og2nrTKe5bptW02d/arcgis/rest/services/"
    "Sismicidad_Ultimo_Mes/FeatureServer/0/query"
    "?where=1%3D1&outFields=*&orderByFields=FECHA_UTC+DESC&resultRecordCount=10&f=json"
)

NTFY_TOPIC = "sismoscolombiaalerta998"
SEEN_FILE = "vistos.txt"

print("--- INICIANDO RASTREO (SGC SISMICIDAD ARCGIS) ---")

seen_ids = set()
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, "r") as f:
        seen_ids = set(f.read().splitlines())
    print(f"Sismos en memoria ({len(seen_ids)} cargados)")

try:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    print("Consultando dataset de sismicidad del SGC...")
    response = requests.get(ARCGIS_SISMOS_URL, headers=headers, timeout=12)
    print(f"Estado HTTP: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        features = data.get('features', [])
        print(f"Total de sismos leídos del SGC: {len(features)}")
        
        new_seen = set(seen_ids)
        
        for feature in features:
            attrs = feature.get('attributes', {})
            
            # ID único del evento en SGC
            object_id = str(attrs.get('OBJECTID') or attrs.get('EVENT_ID') or attrs.get('GlobalID') or '')
            
            # Atributos de la capa de Sismicidad
            municipio = attrs.get('MUNICIPIO') or attrs.get('LOCALIZACION') or 'Colombia'
            departamento = attrs.get('DEPARTAMENTO') or ''
            magnitud = attrs.get('MAGNITUD') or attrs.get('MAGNITUDE') or 'N/A'
            profundidad = attrs.get('PROFUNDIDAD') or 'N/A'
            
            # Formatear la fecha si viene en Timestamp Unix (milisegundos)
            fecha_ms = attrs.get('FECHA_UTC') or attrs.get('FECHA')
            fecha_str = ""
            if fecha_ms and isinstance(fecha_ms, (int, float)):
                fecha_str = datetime.utcfromtimestamp(fecha_ms / 1000.0).strftime('%Y-%m-%d %H:%M UTC')

            if object_id and object_id not in seen_ids:
                titulo = f"M {magnitud} - {municipio}"
                if departamento:
                    titulo += f", {departamento}"
                
                detalle = f"Profundidad: {profundidad} km"
                if fecha_str:
                    detalle += f"\nFecha: {fecha_str}"

                print(f"--> ¡NUEVO SISMO DETECTADO!: {titulo}")
                print("    Enviando notificación a ntfy...")
                
                mensaje = f"🚨 ALERTA SGC COLOMBIA\n{titulo}\n{detalle}"
                
                res = requests.post(
                    f"https://ntfy.sh/{NTFY_TOPIC}",
                    data=mensaje.encode('utf-8'),
                    headers={
                        "Priority": "5",
                        "Tags": "warning,rotating_light"
                    }
                )
                print(f"    Respuesta de ntfy: {res.status_code}")
                new_seen.add(object_id)

        # Guardar historial
        with open(SEEN_FILE, "w") as f:
            for s_id in new_seen:
                f.write(f"{s_id}\n")

    else:
        print("No se pudo obtener respuesta del servidor de sismicidad.")

    print("--- FIN DEL RASTREO ---")

except Exception as e:
    print(f"Error consultando ArcGIS SGC: {e}")
