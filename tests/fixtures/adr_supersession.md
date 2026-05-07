---
title: ADR-0042 - New Auth Strategy
date: 2026-04-15
status: accepted
---

# ADR-0042: New Auth Strategy

## Context

We need a stronger authentication mechanism for the v2 platform.

## Decision

This ADR supersedes ADR-0028 (legacy session cookies). We will move to
short-lived JWT access tokens plus rotating refresh tokens.

## Consequences

- Mobile clients must implement refresh-token rotation.
- Legacy session-cookie endpoints are deprecated as of this ADR.
