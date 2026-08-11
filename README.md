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

