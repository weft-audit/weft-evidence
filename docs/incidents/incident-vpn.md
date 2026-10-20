# Postmortem: global VPN broke model API calls

**Status:** mitigated by policy · **Date:** 2026-10 (owner-reported) ·
**Evidence level:** owner testimony + auditor conclusion in incident-002.

## What happened

With a global VPN enabled, calls to the DeepSeek API intermittently failed or
hung. In the 10-15 cascade the auditor judged VPN a possible contributing
factor, not the primary cause, and found no direct log evidence either way.

## Root cause

Routing model traffic through an unnecessary global tunnel added a failure
surface with no benefit: the API endpoints were directly reachable. The system
had no per-app routing policy, so one switch affected everything.

## The rule it produced

Before heavy runs, disable global VPN and unrelated GPU apps (Wallpaper
Engine); prefer direct routes for model traffic. The rule is listed as a
preventive step in the 10-18 desktop-crash audit.

## What I could not verify

No captured packet-level evidence. Attribution of individual failures to the
VPN is inference, and is labeled as such.
