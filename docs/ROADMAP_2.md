### The next big step: make ZAS operationally trustworthy

# Step A — Source-of-truth enforcement (hardening)
- Make invalid states impossible (or loudly rejected) across UI + API + importers:
- Uniqueness and scoping rules (you already started this with “Area must belong to same Site”)
- Validation services at a single entry point (not scattered across views/admin/tasks)
- Idempotent create/update patterns (especially for imports)
- Audit trails for “who changed what” (simple version first)

Deliverable: a “Data Integrity” test suite that prevents regression.

# Phase 1: IPAM foundations (because it powers everything else)
Topology, telemetry, reporting, automation… all become 10x easier when IPAM exists.
Minimal IPAM v1 (don’t boil the ocean)
Prefix (CIDR) scoped to Site (and optionally VLAN)
IPAddress assignment to Interface
Role/status for IPs (reserved, dhcp, static, deprecated)
Simple conflict detection (no duplicate IP in same VRF scope)
Import/export hooks

Deliverable: “Given a device/interface, ZAS knows its IP truth.”

This will feed:
discovery reconciliation
topology (neighbors often share subnets)
telemetry labeling (site/area/device role)
reports (capacity, usage, growth)

# Phase 2: Topology (start with LLDP/CDP, store as facts)
Topology is not a diagram. Topology is relationships + evidence.
- Topology v1 (boring, useful)

NeighborEdge model:
- local_device/interface
- remote_device/interface (or unknown remote endpoint)
- protocol (LLDP/CDP)
- first_seen / last_seen
- raw payload snapshot (optional)
- A topology collector job (scheduled)
- UI: “Neighbors” tab per device + simple site graph later

Deliverable: “ZAS can answer: what’s connected to what, and when did we last verify it?”

# Phase 3: Telemetry (TIG-style, but treat it as a subsystem)
Your TIG idea is sane. The trap is trying to do “all telemetry” at once.
- Telemetry v1: pick 5–10 metrics, make them perfect
- For IOS-XE and NX-OS, start with:
- interface counters (in/out bps, errors, discards)
- device CPU/memory
- temperature / PSU status (where available)
- link up/down events if possible
- uptime / last reboot
- Architecture recommendation
- Collector workers (Celery) pull via:
- streaming telemetry (best long-term)
- or periodic SNMP/CLI as bootstrap

Write path: ZAS → time-series DB (Influx or Postgres+Timescale later)
Read path: Grafana dashboards + small “sparklines” in ZAS UI

Deliverable: “Boss opens Grafana and sees health trends per site. Operators see per-device counters in ZAS.”

# Phase 4: Reporting (make bosses happy early)
Boss reports usually want:
- Inventory status (how many devices, where, what roles)
- Compliance (backup coverage, reachability coverage)
- SLA-ish summaries (uptime/down devices per period)
- Changes (what changed since last month)
- Reporting v1 (quick wins)
- “Reachability coverage”: % devices with reachability tag, % currently down
- “Backup coverage”: % devices with config_backup_tag, last backup age distribution
- “Inventory by site/role/vendor/platform”
- “Top N flapping devices” (once you track transitions)

Deliverable: PDFs/exports (even CSV first) + a dashboard page in ZAS.

# Phase 5: LLM (only after you have trustworthy data + events)
LLMs become powerful when you have:

- clean inventory
- topology edges
- telemetry metrics
- job outcomes
- change history

LLM entry points that won’t break your soul
- “Explain this outage”: summarize last state transitions + topology neighbors + recent config diffs
- “Generate report narrative”: turn stats into human language for bosses
- “Search over configs + jobs”: RAG over configuration history and job logs
- “Assist remediation”: suggest next checks (but keep it advisory)

Deliverable: LLM features that read first; later you can let it recommend.
- Your network scanner / collector idea (and my opinion)
- This is a very practical bridge from reality → SoT. Do it — but do it as a reconciler, not a blind importer.

Rule: discovery should be idempotent and non-destructive by default
Don’t “create everything” forever. Instead:
Step 1 — Create a “DiscoveryRun” + “DiscoveryFact” model (lightweight)

Your collector produces facts:
- discovered hostname, mgmt IP, serial, platform, software version
- interfaces list + MACs
- neighbors (LLDP/CDP)
- optional VLANs

Store facts with:
- run_id, timestamp
- raw payload link (optional)
- confidence score (optional)

Step 2 — Reconciliation logic (the key)
Compare facts to SoT:
- If device exists (match by serial or inventory_number): update safe fields
- If unknown device: create as “staged” / “discovered” status (not “active production truth” yet)
- Generate “diff” records: what would change if applied

Step 3 — Apply policy
- Auto-apply “safe updates” (software version, uptime, interface counters)
- Require approval for “identity changes” (site, role, naming, rack position)
- This prevents discovery from vandalizing your SoT.
- Using API import via ZAS API is a good idea

It forces you to dogfood:
- validation rules
- permissions
- auditing
- idempotency

Just make sure the API supports:
- bulk upserts
- stable natural keys (serial, inventory_number, fqdn)
- tagging and site scoping

### A crisp “next 4 weeks” plan
Week 1:
- IPAM v1 data model + validations + basic Admin/UI/API
- Add “discovered/staged” concept for imported devices (even as a Device.status)

Week 2:
- DiscoveryRun + reconciliation service
- Importer pushes facts → ZAS, creates staged devices

Week 3:
- Topology v1: store neighbor edges + device neighbor UI tab

Week 4:
- Reporting v1 dashboards (coverage + inventory)
- Cleanup policies (reachability history retention) and alert transitions

This gives you: SoT + Discovery + Topology + Boss reports — the platform starts feeling “real”