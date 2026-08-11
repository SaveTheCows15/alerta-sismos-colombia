# Sismos SGC → ntfy.sh

Bot en GitHub Actions que revisa periódicamente el catálogo de sismos
del Servicio Geológico Colombiano (SGC) y envía una notificación a
[ntfy.sh](https://ntfy.sh) por cada sismo nuevo.

## Cómo funciona

1. Cada 10 minutos, GitHub Actions ejecuta `scripts/check_sismos.py`.
2. El script consulta el servicio ArcGIS público que alimenta el
   visor oficial (`sgc.gov.co/sismos`) y trae los últimos sismos.
3. Compara contra `state/last_sismo.json` (el último sismo ya
   notificado) para saber cuáles son nuevos.
4. Envía una notificación por cada sismo nuevo al topic de ntfy.sh
   configurado.
5. El workflow hace commit del nuevo estado para no repetir avisos.

> **Nota:** el endpoint de ArcGIS que se usa no es una API "oficial"
> documentada por el SGC — es el mismo servicio que consume su propio
> visor web. Es pública y estable en la práctica, pero podría cambiar
> sin aviso. Si un día deja de llegar nada, revisa primero si cambió
> algo en https://srvags.sgc.gov.co/arcgis/rest/services/catalogo_sismos/catalogo_de_sismos_2/FeatureServer/0

## Instalación

1. Crea un repositorio en GitHub y sube estos archivos.
2. Elige un topic de ntfy.sh (por ejemplo `sismos-colombia-tu-nombre-1234`,
   entre más raro mejor, para que no lo adivine nadie más — ntfy.sh es
   público por defecto).
3. En el repo, ve a **Settings → Secrets and variables → Actions** y
   crea un secret llamado `NTFY_TOPIC` con el nombre de tu topic.
4. En **Settings → Actions → General → Workflow permissions**,
   asegúrate de que esté en "Read and write permissions" (para que el
   workflow pueda hacer commit del estado).
5. Instala la app de ntfy en tu celular (o suscríbete desde
   https://ntfy.sh/tu-topic en el navegador) y suscríbete al mismo
   topic.
6. Prueba el workflow manualmente: pestaña **Actions** → "Sismos SGC
   -> ntfy.sh" → **Run workflow**.

## Configuración opcional

- `MIN_MAGNITUDE` (en el workflow): sube este valor si solo te
  interesan los sismos fuertes, por ejemplo `4.5`.
- Frecuencia: cambia el `cron` en `.github/workflows/sismos.yml`
  (mínimo recomendado por GitHub: cada 5 minutos; en la práctica los
  schedules corren con algo de retraso).
- Si usas tu propio servidor ntfy en vez de ntfy.sh, define también el
  secret/variable `NTFY_URL`.

## Probar en local

```bash
pip install -r requirements.txt
export NTFY_TOPIC=tu-topic-de-prueba
python scripts/check_sismos.py
```
