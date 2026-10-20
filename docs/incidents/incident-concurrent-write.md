# Postmortem: concurrent writers corrupted a memory file

**Status:** closed by discipline · **Date:** 2026-10 early (owner-reported) ·
**Evidence level:** owner testimony; no on-disk snapshot of the corrupted file.

## What happened

Two coding-agent sessions were writing to the same Markdown memory file at the
same time. One writer's changes clobbered the other's, and the file was left in
a mixed state. The owner treated a lost memory record as data loss.

## Root cause

The memory layer had no single-writer guarantee: any number of sessions could
open and append to the same file, and "last writer wins" destroyed earlier
records silently.

## The rule it produced

Single-writer, serial writes to shared memory files; one change at a time,
verified before the next one starts. Backups precede every batch write so any
write is reversible.

## What I could not verify

The corrupted intermediate state was not preserved. The incident is recorded
as owner testimony with the discipline it produced, not as a byte-level case.
