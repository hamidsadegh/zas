
                ┌──────────────────────┐
                │        User          │
                │  Web UI / API / Chat │
                └───────────┬──────────┘
                            │
                    ┌───────▼────────┐
                    │ NGINX (TLS)    │
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
                    │   GUNICORN     │
                    └───────┬────────┘
                            │
                  ┌─────────▼──────────┐
                  │       DJANGO       │
                  │  (ZAS Core + API)  │
                  └───────┬────────────┘
                          │
    ┌──────────────┬──────▼───────┬───────────────┐
    │              │              │               │
┌───▼────┐   ┌─────▼─────┐   ┌────▼────┐   ┌─────▼─────┐
│DEVICES │   │ AUTOMATION│   │   LLM   │   │ MONITORING│
│+VLANS  │   │   + CELERY│   │  BRAIN  │   │  + METRICS│
└───┬────┘   └─────┬─────┘   └────┬────┘   └─────┬─────┘
    │              │              │               │
    │              │              │               │
    │      ┌───────▼────────┐     │       ┌───────▼────────┐
    │      │ NETWORK ADAPTER│     │       │ TIME-SERIES DB │
    │      │ NETMIKO/NAPALM │     │       │ VM/INFLUX/GRAF │
    │      └───────┬────────┘     │       └───────┬────────┘
    │              │              │               │
    │         ┌────▼─────┐        │         ┌─────▼─────┐
    └────────►│ NETWORK  │◄───────┴────────►│  METRICS  │
              │ DEVICES  │                  │  DATA     │
              └──────────┘                  └───────────┘


LOGIC FLOW

User request
   ↓
Django (API / UI / LLM Gateway)
   ↓
 ┌───────────────┬───────────────┬───────────────┐
 │               │               │               │
Device DB     Automation       LLM Engine     Monitoring
(Relational)   (Celery)       (RAG + Tools)     (Time-Series)

System feedback loop:
COLLECT → ANALYZE → DECIDE → EXECUTE → LEARN
