---
description: Deliver a change through the gated agentic-delivery flow
argument-hint: "[what to build or fix]"
disable-model-invocation: true
---
Load the `agentic-delivery` skill and deliver this change: $ARGUMENTS

If nothing was given, ask for the one-line change request first. Use the smallest sufficient
set of hats, run an independent review before merge, and stop for human approval on push, merge
and deploy.
