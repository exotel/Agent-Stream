# Wiring into dograh-hq/dograh

Apply these edits when opening the upstream PR. Do not invent extra touch points.

## 1. Copy package

```text
dograh-contribution/providers/exotel/  →  api/services/telephony/providers/exotel/
dograh-contribution/tests/test_provider.py  →  api/tests/telephony/exotel/test_provider.py
```

## 2. Register provider

`api/services/telephony/providers/__init__.py` — add import:

```python
from api.services.telephony.providers import (  # noqa: F401
    ari,
    cloudonix,
    exotel,  # add
    plivo,
    telnyx,
    twilio,
    vobiz,
    vonage,
)
```

## 3. Enum

`api/enums.py` — in `WorkflowRunMode`:

```python
EXOTEL = "exotel"
```

## 4. Schemas

`api/schemas/telephony_config.py`:

- Import `ExotelConfigurationRequest` / `ExotelConfigurationResponse`
- Add request to `TelephonyConfigRequest` union
- Add `exotel: Optional[ExotelConfigurationResponse] = None` on response
- Export in `__all__`

## 5. UI constant (parity)

`ui/src/constants/workflowRunModes.ts`:

```ts
EXOTEL: 'exotel',
```

## 6. Docs (optional but recommended)

- Add `docs/integrations/telephony/exotel.mdx`
- Link from `docs/integrations/telephony/overview.mdx` and `docs/docs.json`

## Do not edit

- `factory.py`
- `audio_config.py`
- `run_pipeline.py`
- `routes/telephony.py` (provider routes auto-mount from `providers/exotel/routes.py`)
- Custom frontend form (UI is metadata-driven)
- DB migrations
