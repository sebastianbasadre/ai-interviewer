# ADR-003: consent and complete dataset deletion

Status: accepted by the project owner at G1. Date: 2026-11-02.

## Context

An interview contains personal data, audio and text. The pilot needs simple limits and
verifiable deletion. This ADR defines engineering requirements; it does not replace legal review.

## Decision

Require versioned consent before capture or provider calls. Use random 32-byte invitation
tokens, persist only their hashes, expire them after seven days and claim them atomically
for single use. Protect IP addresses with HMAC. Default retention is 30 days: delete
candidate, consent, turns, report and files, keeping only anonymous statistics. Requested
deletion uses the same idempotent operation. Calculate the deadline from closure, or
creation if the interview never started. Backups must expire and respect a deletion
ledger on restore. Never store sensitive data in logs.

## Consequences

Storage needs consent, concurrency, retention and file-deletion tests. The pilot cannot
start until data access, providers, privacy contact, backup policy and AI disclosure are
documented. Persisted video recording awaits a G1 scope decision.
