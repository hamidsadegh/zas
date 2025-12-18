### As we are impelimenting phpIPAM in our enviornment we will use it as a short/mid-term solution 
## How phpIPAM fits right now

# Short-term coexistence (recommended)
phpIPAM remains the authoritative IPAM
ZAS reads from phpIPAM (via API)
ZAS uses IP data for:
reachability
topology
reporting
discovery reconciliation
ZAS does not write back yet.

# Mid-term transition
ZAS IPAM v1 implemented
Import phpIPAM data into ZAS
Run both in parallel
Detect drift

# Long-term
ZAS becomes SoT
phpIPAM retired or read-only
This is a zero-drama migration path.


# Map phpIPAM → ZAS fields
    | phpIPAM | ZAS       |
    | ------- | --------- |
    | section | site      |
    | subnet  | prefix    |
    | ip      | ipaddress |
    | vlan    | vlan      |
    | device  | device    |
    | port    | interface |


