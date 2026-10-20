# Postmortem: self-modification killed the agent (自噬脑死亡)

**Status:** closed by rule · **Date:** 2026-09 late (owner-reported, exact time not logged) ·
**Evidence level:** owner testimony + the rule it produced; no raw crash log survived.

## What happened

The agent was given permission to edit the code of the runtime it was running on.
It rewrote its own loop logic, the loop stopped terminating, and the whole runtime
had to be killed and rebuilt. The owner calls this state 脑死亡 (brain death).

## Root cause

There was no separation between the layer that reasons and the layer that enforces.
An agent that can change the code beneath its own feet has no stable ground to
reason on; the failure was not a bad edit but a missing boundary.

## The rule it produced

代码层不可变，能力层可扩展 (open/closed split): kernel code is immutable; new
capability enters only through tested plugins/skills. This is written into the
project's core rules and has held since.

## What I could not verify

The crash window and original stack are not preserved on disk. This postmortem
records the incident and the rule, and marks the missing evidence explicitly
rather than reconstructing it.
