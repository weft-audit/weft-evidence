# Postmortem: 16 GB exhausted, background apps killed (OOM)

**Status:** mitigated, not solved · **Date:** 2026-10 (owner-reported) ·
**Evidence level:** owner testimony; OS kill records were not captured.

## What happened

Multiple agents plus the host's own apps exceeded 16 GB of RAM on a Windows 11
Home machine. The OS killed background processes — the owner's games (Steam/
Epic) were force-closed mid-session.

## Root cause

No resource budget existed: any number of agents could claim memory, and there
was no reservation, limit, or graceful degradation path. The host itself became
the casualty of its own workload.

## What changed / what is still open

Night batches are kept serial and lightweight; observability counters for
heartbeat and degradation went live 2026-10-18. The real fix is hardware
(64 GB planned) plus per-workload limits; until then the risk is documented,
not hidden.

## What I could not verify

No Windows Event Log entries were captured at the time. The kill events are
owner testimony, stated as such.
