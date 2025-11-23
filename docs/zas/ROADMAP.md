# ZAS – 12-MONTH TECHNICAL ROADMAP (V2)

Purpose:
Transform ZAS from an internal Django tool into a production-grade,
AI-assisted network orchestration and intelligence platform.

The roadmap is split into clear evolutionary phases.

------------------------------------------------------------

## Phase 1 (Month 1–2): ZAS becomes rock-solid infrastructure

Mission:
Boring, powerful stability.

Goal:
Make ZAS a clean, professional, production-grade platform that can safely
control real infrastructure.

Mastering in:
- Software Engineering foundations (refresh)
- Clean architecture & separation of concerns
- Proper model relationships
- SOLID principles (especially Single Responsibility)
- Django at a professional level
- Custom User + Roles (admin / operator / viewer)
- Proper API versioning (/api/v1/)
- Relationships: Rack ↔ Device ↔ Interface ↔ VLAN
- Real production architecture

Final infrastructure form:

User
  ↓
Nginx (TLS)
  ↓
Gunicorn (App Server)
  ↓
Django (API + UI)
  ↓
MariaDB / PostgreSQL
  ↓
Redis (cache + Celery broker)
  ↓
Celery (background jobs)

By end of Phase 1, ZAS must be able to:
✅ Know where every device is installed  
✅ Know subnet, VLAN and rack information  
✅ Know device role (core / distribution / access / firewall)  
✅ Store credentials securely (env + encryption / Vault later)  
✅ Trigger background jobs (Celery)  
✅ Be stable, predictable, testable  

------------------------------------------------------------

## Phase 2 (Month 3–4): Network Automation Muscle

Mission:
ZAS starts talking to real devices.

Goal:
Turn ZAS into a network automation engine.

Mastering in:
- Network automation architecture
- Idempotent actions
- Device abstraction
- Error handling / retries / timeout control

To implement inside ZAS:

Automation services:
- ReachabilityService → Ping + timeout + status
- SNMPService → sysName, sysDescr, uptime, interfaces
- ConfigPullService → Running config backup
- VersionCheckService → IOS/NX-OS/Model
- VLANPushService → Create / delete VLANs

Tech:
- Netmiko / NAPALM
- TextFSM
- Multi-threading or Celery workers

ZAS UI concept:
“Scan this rack”
“Scan this VLAN”
“Backup this device”

ZAS flow:
Device selection → Adapter → Data collection → DB update → UI update

By end of Phase 2:
✅ ZAS interacts directly with real devices  
✅ ZAS updates device data dynamically  
✅ ZAS becomes a true orchestration layer  
✅ No more standalone scripts  

------------------------------------------------------------

## Phase 3 (Month 5–6): Data, Observability & Control Loop

Mission:
ZAS becomes aware of time and behaviour.

Goal:
Create a feedback loop between the network and ZAS.

Mastering in:
- Time-series concepts
- Observability (metrics + logs + events)
- Network behaviour over time
- Alerting logic

To implement:

Collectors:
- Interface counters (errors, drops, utilization)
- CPU / memory / temperature (SNMP/API)
- Link state changes
- Reachability history

Storage:
- Time-series DB: VictoriaMetrics or InfluxDB
- Django: relational source of truth

Pipeline:

Devices
  → SNMP / API / CLI
    → ZAS Collector
      → Time-series DB
        → Grafana
      → Django DB

Dashboards:
- Device Health
- Interface Errors
- VLAN usage
- Reachability history
- Top talkers (basic)

Control loop v1:
Collect → Store → Visualize → Learn

By end of Phase 3:
✅ Historical visibility
✅ Trend detection
✅ “Normal vs abnormal” baselines
✅ ZAS becomes a monitoring brain

------------------------------------------------------------

## Phase 4 (Month 7–8): LLM Foundation Layer

Mission:
Give ZAS the ability to understand language + context.

Goal:
Build an internal AI layer that knows your network.

Mastering in:
- Prompt engineering
- Embeddings
- RAG (Retrieval-Augmented Generation)
- Tool calling
- Safe AI design

New app:
llm/

Indexed knowledge:
- Devices
- VLANs
- Rack layouts
- Config snippets
- Error logs
- ZAS documentation

Basic flow:

User question
  → ZAS retrieves context (DB + embeddings)
    → LLM reasoning
      → Network-aware answer

Example questions:
- "Where is switch B-SW-203?"
- "Why is VLAN 2003 used?"
- "Show unhealthy devices today"

By end of Phase 4:
✅ ZAS answers in natural language
✅ Context-aware responses
✅ Infrastructure aware AI assistant

------------------------------------------------------------

## Phase 5 (Month 9–10): Decision & Action Layer

Mission:
ZAS starts recommending AND preparing actions

Goal:
Controlled autonomy with human approval

Flow:

User → Request change
LLM → Generates plan + safe commands
User → Approves
ZAS → Executes via Netmiko/NAPALM
ZAS → Verifies + stores history

Features:
- Diff display
- Validation before run
- Rollback planning
- Approval system
- Version tracking

Rule:
LLM proposes → Human approves → System executes

By end of Phase 5:
✅ Change planning
✅ Safe execution
✅ Full audit
✅ True NetDevOps capability

------------------------------------------------------------

## Phase 6 (Month 11–12): Intelligence & Autonomy

Mission:
ZAS becomes predictive, not only reactive.

Goal:
Prediction, prevention, optimization

Mastering in:
- Anomaly detection
- Behaviour analysis
- Root Cause Automation
- Capacity planning

Features:
- Spike detection
- Degradation trends
- Flapping detection
- Failure prediction

AI-powered RCA:

Input: "Device unreachable"

ZAS checks:
- History
- Neighbors
- Counters
- Logs
- Patterns

Output:
"Probable cause: uplink failure on SW-23 at 12:04"

Optimization suggestions:
- VLAN consolidation
- Unused port detection
- Bottlenecks
- SPOF identification

By end of Phase 6:
✅ Predictive intelligence
✅ Self-diagnosis
✅ Planning assistance
✅ Enterprise-grade internal platform

------------------------------------------------------------

Final Vision:

Human + ZAS + AI = Hybrid Network Intelligence

You = Architect  
ZAS = Brain + Memory + Hands  
Network = Body  

Career-defining system.
