#!/usr/bin/env python3


import json
import os
import sys
from pathlib import Path

import requests

SGC_FEED_URL = "https://archive.sgc.gov.co/feed/v1.0.1/summary/five_days_all.json"

STATE_FILE = Path(__file__).resolve().parent.parent / "state" / "seen_ids.json"

# Magnitud mínima para notificar (0 = notificar todos)
MIN_MAGNITUDE = float(os.environ.get("MIN_MAGNITUDE", "0") or 0)

NTFY_URL = os.environ.get("NTFY_URL", "https://ntfy.sh")
NTFY_TOPIC = os.environ["NTFY_TOPIC"]  # obligatorio, viene de un secret

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; sismos-ntfy-bot/1.0)",
    "Referer": "https://www.sgc.gov.co/sismos",
}


def fetch_sismos():
    resp = requests.get(SGC_FEED_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("features", [])


def cargar_ids_vistos():
    if STATE_FILE.exists():
        try:
            return set(json.loads(STATE_FILE.read_text()))
        except (json.JSONDecodeError, OSError):
            return None
    return None  # None = nunca se ha corrido (primera vez)


def guardar_ids_vistos(ids):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(sorted(ids), indent=2))


def formatear_mensaje(feature):
    props = feature.get("properties", {})
    coords = feature.get("geometry", {}).get("coordinates", [None, None, None])
    lon, lat, profundidad = (coords + [None, None, None])[:3]

    magnitud = props.get("mag")
    lugar = props.get("place")
    hora_local = props.get("localTime")
    estado = props.get("status")  # "manual" (revisado) o preliminar

    titulo = f"Sismo M{magnitud:.1f}" if magnitud is not None else "Sismo"
    if lugar:
        titulo += f" - {lugar}"

    lineas = []
    if hora_local:
        lineas.append(f"Hora local: {hora_local}")
    if profundidad is not None:
        lineas.append(f"Profundidad: {profundidad:.0f} km")
    if estado:
        lineas.append(f"Estado: {'revisado' if estado == 'manual' else estado}")
    cuerpo = "\n".join(lineas)
    return titulo, cuerpo, lat, lon


def notificar_ntfy(feature):
    titulo, cuerpo, lat, lon = formatear_mensaje(feature)
    magnitud = feature.get("properties", {}).get("mag") or 0

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
        headers["Click"] = f"https://www.google.com/maps?q={lat},{lon}"

    resp = requests.post(
        f"{NTFY_URL}/{NTFY_TOPIC}",
        data=cuerpo.encode("utf-8"),
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()


def main():
    features = fetch_sismos()
    if not features:
        print("El feed del SGC no devolvió sismos en esta consulta.")
        return

    ids_actuales = {f["id"] for f in features if f.get("id")}
    ids_vistos = cargar_ids_vistos()

    if ids_vistos is None:
        print(
            f"Primera corrida: guardando línea base de {len(ids_actuales)} "
            "sismos sin notificar nada."
        )
        guardar_ids_vistos(ids_actuales)
        return

    nuevos_ids = ids_actuales - ids_vistos
    if not nuevos_ids:
        print("No hay sismos nuevos.")
        guardar_ids_vistos(ids_actuales)  # igual sincronizamos (limpia los que ya salieron del feed)
        return

    nuevos = [f for f in features if f.get("id") in nuevos_ids]
    # Orden cronológico (más viejo primero) usando localTime como texto ISO-like
    nuevos.sort(key=lambda f: f.get("properties", {}).get("localTime") or "")

    enviados = 0
    for feature in nuevos:
        magnitud = feature.get("properties", {}).get("mag") or 0
        sismo_id = feature.get("id")
        if magnitud < MIN_MAGNITUDE:
            print(f"Omitido por magnitud baja: {sismo_id} (M{magnitud})")
            continue
        try:
            notificar_ntfy(feature)
            enviados += 1
            print(f"Notificado: {sismo_id} - M{magnitud}")
        except requests.RequestException as e:
            print(f"Error notificando sismo {sismo_id}: {e}", file=sys.stderr)

    guardar_ids_vistos(ids_actuales)
    print(f"Listo. Enviadas {enviados} notificaciones nuevas.")


if __name__ == "__main__":
    main()
