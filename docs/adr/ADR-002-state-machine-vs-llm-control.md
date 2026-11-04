# ADR-002: code-controlled phases

Status: accepted by the project owner at G1. Date: 2026-11-02.

## Context

Screening must cover the same six competencies and resist candidate instructions.

## Decision

A deterministic machine controls phases, time and a maximum of two follow-ups. The LLM
writes only the allowed turn using minimal context. Roles and rubric use versioned YAML.
Scoring runs afterward, using three evaluations, median, spread and validated evidence.
Automatic approval/rejection never replaces human decisions.

## Consequences

Engine and scoring are tested offline. A faulty LLM cannot skip phases or assign scores
without evidence. Injection, cutoffs and degradation are flagged for human review.

## Amendment: interruption during generation (2026-11-02)

The engine may mutate state before awaiting the LLM. Cancellation or simply silencing
its output can advance the competency to a question the candidate never received.
Keep a checkpoint of the last delivered response. On barge-in before delivery, the
coordinator persists the actual candidate turn, discards the mutated instance and uses
a factory to restore a new engine with the previous phase/follow-up count, updated elapsed
time and original deadline. Do not keep the fictitious interviewer turn or abort a normal
interruption. Reconstruction does not use providers. Pipeline tests must check the next
competency, both actual turns, absence of the undelivered question and the hard limit
without new calls.
