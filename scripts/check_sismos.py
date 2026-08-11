#!/usr/bin/env python3

import json
import os
import sys
from pathlib import Path

import requests

SGC_QUERY_URL = (
    "https://srvags.sgc.gov.co/arcgis/rest/services/"
    "catalogo_sismos/catalogo_de_sismos_2/FeatureServer/0/query"
)

STATE_FILE = Path(__file__).resolve().parent.parent / "state" / "last_sismo.json"

# Cuántos sismos recientes pedir en cada consulta (de más nuevo a más viejo)
FETCH_COUNT = 15

# Magnitud mínima para notificar (None = notificar todos)
MIN_MAGNITUDE = float(os.environ.get("MIN_MAGNITUDE", "0") or 0)

NTFY_URL = os.environ.get("NTFY_URL", "https://ntfy.sh")
NTFY_TOPIC = os.environ["NTFY_TOPIC"]  # obligatorio, viene de un secret


def fetch_ultimos_sismos():
    params = {
        "where": "1=1",
        "outFields": (
            "ESP_ID_EVENTO_TXT,ESP_MAGNITUD,ESP_FUENTE_MAGNITUD,"
            "ESP_PROFUNDIDAD,ESP_FECHA_TXT,ESP_FECHA_LONG,"
            "ESP_LATITUD,ESP_LONGITUD,MUN_CODIGO,DEPT_CODIGO"
        ),
        "orderByFields": "ESP_FECHA_LONG DESC",
        "resultRecordCount": FETCH_COUNT,
        "returnGeometry": "false",
        "f": "json",
    }
    resp = requests.get(SGC_QUERY_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        raise RuntimeError(f"El servicio del SGC devolvió un error: {data['error']}")

    features = data.get("features", [])
    sismos = [f["attributes"] for f in features]
    # Por si el orderByFields no se respeta del todo, ordenamos nosotros también
    sismos.sort(key=lambda s: s.get("ESP_FECHA_LONG") or 0, reverse=True)
    return sismos


def cargar_ultimo_id():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text()).get("last_id")
        except (json.JSONDecodeError, OSError):
            return None
    return None


def guardar_ultimo_id(sismo_id):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({"last_id": sismo_id}, indent=2))


def formatear_mensaje(sismo):
    magnitud = sismo.get("ESP_MAGNITUD")
    profundidad = sismo.get("ESP_PROFUNDIDAD")
    fecha = sismo.get("ESP_FECHA_TXT")
    lat = sismo.get("ESP_LATITUD")
    lon = sismo.get("ESP_LONGITUD")

    titulo = f"Sismo M{magnitud:.1f}" if magnitud is not None else "Sismo"
    cuerpo_lineas = [f"Fecha: {fecha}" if fecha else None]
    if profundidad is not None:
        cuerpo_lineas.append(f"Profundidad: {profundidad:.0f} km")
    if lat is not None and lon is not None:
        cuerpo_lineas.append(f"Ubicación: {lat:.3f}, {lon:.3f}")
    cuerpo = "\n".join(l for l in cuerpo_lineas if l)
    return titulo, cuerpo, lat, lon


def notificar_ntfy(sismo):
    titulo, cuerpo, lat, lon = formatear_mensaje(sismo)
    magnitud = sismo.get("ESP_MAGNITUD") or 0

    # Prioridad y emoji según magnitud
    if magnitud >= 6:
        prioridad, tag = "urgent", "rotating_light"
    elif magnitud >= 4.5:
        prioridad, tag = "high", "warning"
    else:
        prioridad, tag = "default", "earth_americas"

    headers = {
        "Title": titulo.encode("utf-8"),
        "Priority": prioridad,
        "Tags": tag,
    }
    if lat is not None and lon is not None:
        # ntfy soporta adjuntar ubicación como link a un mapa
        headers["Click"] = f"https://www.google.com/maps?q={lat},{lon}"

    resp = requests.post(
        f"{NTFY_URL}/{NTFY_TOPIC}",
        data=cuerpo.encode("utf-8"),
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()


def main():
    sismos = fetch_ultimos_sismos()
    if not sismos:
        print("El SGC no devolvió sismos en esta consulta.")
        return

    ultimo_id_conocido = cargar_ultimo_id()
    print(f"Último ID notificado previamente: {ultimo_id_conocido}")

    # Los sismos vienen del más nuevo al más viejo
    nuevos = []
    for sismo in sismos:
        sismo_id = sismo.get("ESP_ID_EVENTO_TXT")
        if sismo_id == ultimo_id_conocido:
            break
        nuevos.append(sismo)

    if not nuevos:
        print("No hay sismos nuevos.")
        return

    # Notificar del más viejo al más nuevo para que lleguen en orden cronológico
    nuevos.reverse()
    enviados = 0
    for sismo in nuevos:
        magnitud = sismo.get("ESP_MAGNITUD") or 0
        if magnitud < MIN_MAGNITUDE:
            print(f"Omitido por magnitud baja: {sismo.get('ESP_ID_EVENTO_TXT')} (M{magnitud})")
            continue
        try:
            notificar_ntfy(sismo)
            enviados += 1
            print(f"Notificado: {sismo.get('ESP_ID_EVENTO_TXT')} - M{magnitud}")
        except requests.RequestException as e:
            print(f"Error notificando sismo {sismo.get('ESP_ID_EVENTO_TXT')}: {e}", file=sys.stderr)

    # Guardamos como "último visto" el más reciente de todos los que llegaron,
    # se haya notificado o no (para no reintentar cosas por debajo del umbral).
    guardar_ultimo_id(sismos[0].get("ESP_ID_EVENTO_TXT"))
    print(f"Listo. Enviadas {enviados} notificaciones nuevas.")


if __name__ == "__main__":
    main()
