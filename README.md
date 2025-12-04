# consultor-porcentaje-avance-proc-inteligente

> Microservicio HTTP (Google Cloud) para consultar el último evento `progress` de un `run_id` en Cloud Logging.

Descripción
- Este pequeño servicio busca en Cloud Logging la última entrada de log con `event_type: "progress"` para un `run_id` dado y devuelve `percent`, `step` y `ts_utc` si está disponible.

Archivos incluidos
- `consultor-porcentaje-avance-proc-inteligente.py`: función HTTP implementada con `functions_framework`.
- `requirements.txt`: dependencias necesarias.

Requisitos previos
- Python 3.11+ (recomendado)
- `pip` y `virtualenv` (opcional)
- `gcloud` y/o `gh` si desea desplegar desde la CLI
- Cuenta de GCP con permisos adecuados y el SDK configurado

Instalación local

1. Crear y activar un entorno virtual (opcional):
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
2. Instalar dependencias:
```
pip install -r requirements.txt
```

Ejecución local
- Usando `functions-framework` para probar localmente:
```
functions-framework --target=progress_consultor --debug
```
Esto expondrá la función en `http://localhost:8080` por defecto.

Ejemplo de petición de prueba
```
curl -X POST "http://localhost:8080/" -H "Content-Type: application/json" -d '{"run_id":"mi-run-id"}'
```

Despliegue a Cloud Functions (ejemplo)
```
gcloud functions deploy progress_consultor \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --region=us-central1 \
  --entry-point=progress_consultor
```

Notas importantes
- La función utiliza las credenciales por defecto de Google (`google.auth.default()`). El entorno donde se despliegue debe tener un `project_id` resolvible y un service account con permisos para leer logs (`roles/logging.viewer`).
- Por defecto el filtro busca `resource.type="cloud_run_revision"`. Puede pasar `resource_type` y `service_name` en el cuerpo JSON para filtrar.

Contribuciones y siguientes pasos
- Se puede añadir un `README` más detallado, tests unitarios, CI, y una política de protección de ramas.

Contacto
- Si necesitas que lo despliegue con parámetros concretos o añada un `README` en inglés, dímelo y lo hago.
