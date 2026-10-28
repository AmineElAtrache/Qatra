# Satellite Earth Engine runbook

The Satellite service is optional at runtime: unit tests and the API continue
to work when Earth Engine is absent or unavailable, returning explicit missing
values. Live Earth Engine access requires:

1. An eligible Google Cloud project with Earth Engine enabled.
2. `GEE_PROJECT_ID` in the backend environment.
3. Application Default Credentials or a service-account JSON file referenced by
   `GEE_CREDENTIALS_PATH`.
4. `earthengine-api` installed from `backend/requirements.txt`.

Do not commit credentials or run interactive authentication from FastAPI.

To test the service with the repository sample (from `backend`, after
installing requirements):

```powershell
@'
import asyncio, json
from pathlib import Path
from app.services.satellite_service import fetch_indices

plot = json.loads(Path('../docs/samples/ma001.geojson').read_text())
result = asyncio.run(fetch_indices(geojson=plot, generate_overlay=False))
print(result)
'@ | python -
```

The result keeps `None` for unavailable indices and records the reason. No
sample value is substituted for a failed live request.
