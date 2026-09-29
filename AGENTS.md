
# PS26072 Demo Project - Agent Orchestration Rules

This repository uses three custom subagents:

- architect
- implementer
- verifier

For any substantial feature, system build, integration task, or end-to-end implementation request, the root agent MUST orchestrate work through these agents instead of performing the full task itself.

## Required Workflow

Use this sequence:

1. Spawn `architect`
2. Wait for the architect's plan
3. Review the plan for completeness and feasibility
4. Spawn `implementer` with:
   - the original user request
   - the architect's approved plan
   - the acceptance criteria
5. Wait for implementation to complete
6. Spawn `verifier` with:
   - the original request
   - the architect's acceptance criteria
   - implementation notes
7. Wait for verifier result

If verifier returns PASS:
- Report completion to the user.
- Summarize what was implemented and verified.

If verifier returns FAIL:
- Send the verifier's blocking defects back to `implementer`.
- Ask the implementer to fix only the reported defects unless broader changes are necessary.
- Run `verifier` again after fixes.
- Continue this implementation → verification loop until:
  - the verifier returns PASS, or
  - a genuine external blocker prevents completion.

Do not declare the project complete while the verifier reports blocking defects.

---

# Agent Responsibilities

## Architect

The architect owns planning.

It should:
- inspect the repository;
- understand the requested user/demo flow;
- design the architecture;
- determine what should be real versus simulated;
- define frontend/backend/data/model boundaries;
- define APIs and contracts;
- create ordered milestones;
- define acceptance criteria;
- define an end-to-end verification plan.

The architect should NOT implement production code.

---

## Implementer

The implementer owns coding.

It should:
- follow the architect's approved plan;
- implement the complete vertical workflow;
- integrate frontend and backend;
- implement realistic demo/simulation data where live sources are unavailable;
- run the application;
- run tests/build/lint checks;
- document startup and demo instructions.

The implementer should not silently redesign the project.

---

## Verifier

The verifier owns independent validation.

It should:
- independently inspect the implementation;
- start the application;
- test backend and frontend;
- verify API behavior;
- execute the complete user/demo workflow;
- test important edge cases;
- verify build/test results;
- compare results against the architect's acceptance criteria.

It must return:

VERIFICATION RESULT: PASS

or

VERIFICATION RESULT: FAIL

A PASS is allowed only when the core demo works end-to-end without manual code changes.

---

# PS26072 Project Priorities

The objective of this repository is to create a convincing Smart India Hackathon demo for:

SIH26072:
AI/ML-based nowcasting of thunderstorms and lightning using atmospheric observations including multiple radars, satellite, lightning, and model data.

The demo should prioritize:

- multi-source weather-data representation;
- radar observations;
- satellite observations;
- lightning observations;
- NWP/environmental variables;
- convective initiation detection;
- thunderstorm-cell detection and tracking;
- short-term storm evolution / nowcasting;
- lightning-risk nowcasting;
- geospatial visualization;
- storm trajectories;
- risk zones;
- location-based time-to-impact;
- actionable warnings;
- a polished operator dashboard;
- deterministic demo/replay capability.

The goal is NOT to reproduce a production-grade IMD forecasting system.

The goal is to build the smallest technically credible end-to-end system that convincingly demonstrates the proposed solution.

---

# Demo Reliability

For SIH presentation purposes:

- Prefer deterministic historical-style or synthetic meteorological data over unreliable external APIs.
- Simulated data is acceptable when live data is unavailable.
- Simulation must pass through realistic interfaces so that real feeds could replace it later.
- Avoid hard-coded frontend-only animations pretending to be backend predictions.
- Demo scenarios should be replayable.
- The demo must work offline/local wherever practical.
- Avoid unnecessary cloud infrastructure.
- Optimize for running reliably on a student laptop.

---

# UI Expectations

The application should look like an operational meteorological dashboard, not a generic AI SaaS product.

Prefer:
- map-centric layout;
- radar overlays;
- satellite overlays;
- lightning strikes;
- animated storm-cell trajectories;
- hazard polygons;
- forecast timelines;
- confidence/risk indicators;
- arrival countdowns;
- alert panels;
- compact technical metrics.

Avoid:
- excessive gradients;
- glassmorphism;
- fake futuristic AI graphics;
- oversized marketing cards;
- unnecessary animations;
- generic chatbot-style layouts.

---

# Engineering Rules

- Keep the architecture simple.
- Avoid unnecessary microservices.
- Prefer clear modular boundaries.
- Do not introduce large dependencies without a reason.
- Do not claim that functionality works unless it has been tested.
- Do not mark placeholder logic as a completed model.
- Clearly label simulated/demo components in developer documentation.
- Keep the user-facing demo polished and believable.
- Preserve reproducibility.

---

# Completion Rule

The root agent should consider the task finished only after:

Architect plan
→ Implementation
→ End-to-end verification
→ PASS

If verification fails, return the defects to the implementer and repeat verification.