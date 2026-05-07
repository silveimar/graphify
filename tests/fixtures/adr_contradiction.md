---
title: Proposal - Drop Refresh Tokens
date: 2026-05-01
status: proposed
---

# Proposal: Drop Refresh Tokens

## Context

Refresh tokens are introducing storage and rotation complexity.

## Decision

This proposal directly contradicts ADR-0042's claim that refresh-token
rotation is required. We argue that opaque session tokens with strict
TTLs are sufficient for our threat model.

## Consequences

- Re-evaluation of ADR-0042 is required before adoption.
