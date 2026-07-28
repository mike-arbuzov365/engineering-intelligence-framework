---
packet: EIF-020-private-workspace
type: packet_index
status: prepared
created: 2026-07-28
---

# EIF 0.2.0 private workspace scope

This packet plans the smallest coherent private workspace vertical slice.
It does not add a fourth EIF layer and it does not turn a private control
repository into a fork of the public framework.

The public EIF release stays canonical. The optional private workspace is
a durable scope inside L2, alongside project-local scope. It stores
owner- or team-specific reusable artifacts and coordinates their
materialization into independent project repositories.

## Reading order

1. `01-CHARTER-020-private-workspace.md`
2. `02-FACTS-020-private-workspace.md`
3. `03-DECISIONS-020-private-workspace.md`
4. `04-ROADMAP-020-private-workspace.md`
5. `05-SELF-REVIEW-020-private-workspace.md`
6. `06-START-HERE-private-workspace.md`

## Session map

| Session | Result |
|---|---|
| 001 | Architecture, terminology and ratified public decision |
| 002 | Schemas, registry migration and compatibility contract |
| 003 | Local private workspace creation and registry lifecycle |
| 004 | Profile resolution, hashed materialization and verification |
| 005 | Plan, apply and detach across registered projects |
| 006 | Documentation, site copy, packaging and capability claims |
| 007 | Full local verification and release-candidate closeout |

## Release boundary

This packet may prepare a local `0.2.0` release candidate. It does not
push, tag, publish, change repository visibility, create a remote
repository, or run hosted CI. Private real-project dogfood is a required
follow-on release gate, but its repository identities and machine
locations belong in a private workspace, never in this public packet.
