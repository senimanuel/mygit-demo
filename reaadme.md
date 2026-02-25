# EMS Transition Strategy: From Pets to Cattle

## Context

EMS currently operates a hybrid operational model across multiple applications:

* **Flow Control**
* **Marketing**
* **TAPI**
* **Hygiene**

While EMS has begun adopting modern practices in certain areas, the overall infrastructure mindset remains partially aligned with a traditional “Pets” model.

This page outlines:

* The specific challenges EMS faces
* The structural differences across application groups
* The risks of remaining in the current state
* The practical pathway to transition
* The measurable benefits to EMS

---

# 1. Current State at EMS

## 1.1 Flow Control

Flow Control is comparatively mature in delivery practices.

It uses:

* CI/CD pipelines
* Jenkins
* Bitbucket for version control
* Automated deployment model

Flow Control is largely independent from the other application domains.

However:

* Some services run on shared infrastructure (e.g., “Bad Job Servers”)
* Not all services are containerised
* Infrastructure still includes long-lived instances

Flow Control is closest to a “Cattle-ready” workload but not fully there.

---

## 1.2 Marketing, TAPI, Hygiene

These applications exhibit stronger “Pets” characteristics.

Observed traits:

* SME-dependent knowledge
* Manual server configuration
* Vertical scaling (increase CPU/memory instead of scale-out)
* Limited automation
* Long-lived instances

Operational risk is higher because:

* Knowledge concentration is significant
* Automation is limited
* Scaling is constrained
* Drift risk is elevated

---

## 1.3 “Bad Job Servers”

EMS currently operates dedicated “Bad Job Servers.”

Characteristics:

* Shared workloads
* Mixed responsibilities
* Partial Flow Control services
* Internally used applications
* Manually managed services

Risks introduced by this pattern:

* Blurred ownership
* High blast radius during failure
* Difficult isolation of faults
* Hard to scale specific workloads independently
* Increased configuration drift

The naming itself reflects a reactive pattern rather than architectural intent.

---

# 2. Key Challenges EMS Faces

## 2.1 Cultural & Knowledge Dependency

Several applications depend heavily on SMEs.

Risks:

* High bus factor
* Resistance to disposability
* Fear of automation replacing manual control
* Difficulty codifying undocumented processes

Mindset shift required:
Infrastructure should not depend on individual expertise for survival.

---

## 2.2 Vertical Scaling Bias

Current scaling strategy in Marketing, TAPI, and Hygiene largely involves:

* Increasing processor
* Increasing memory
* Maintaining single-instance dependency

Limitations:

* Hardware ceiling constraints
* Higher downtime risk
* Cost inefficiency
* Reduced elasticity

This model does not leverage cloud-native strengths.

---

## 2.3 Application Architecture Constraints

Some EMS applications were designed:

* Without containerisation in mind
* With static configuration assumptions
* With tight server coupling

Transitioning to Cattle may require:

* Refactoring
* Externalising configuration
* Removing local state dependencies
* Redesigning service boundaries

This is not a lift-and-shift problem — it is an architectural evolution.

---

## 2.4 Shared Infrastructure Pattern

“Bad Job Servers” represent a shared-server model where multiple responsibilities coexist.

Problems:

* Scaling one workload affects others
* Troubleshooting becomes complex
* Isolation is limited
* Replacement is risky

This pattern conflicts with immutability and disposability.

---

# 3. EMS Transition Approach

The transition should be phased and pragmatic — not disruptive.

---

## Phase 1: Classification

Group applications into:

1. Cloud-ready (Flow Control candidate)
2. Refactor-required (Marketing, TAPI, Hygiene)
3. Legacy containment workloads

This avoids a one-size-fits-all strategy.

---

## Phase 2: Containerisation Strategy

Where feasible:

* Containerise Java-based packages
* Externalise configuration (env vars, config services)
* Remove local state dependency
* Introduce health checks

This allows:

* Stateless deployment
* Horizontal scaling
* Isolation per service

However, this requires code-level refactoring and reconfiguration effort.

---

## Phase 3: Eliminate Shared “Bad Job” Servers

Move from:

Shared multi-purpose servers

To:

* Isolated service deployments
* Container orchestration (e.g., Kubernetes or managed alternatives)
* Per-service scaling

This reduces blast radius and improves observability.

---

## Phase 4: Enforce Infrastructure as Code

All new infrastructure must be:

* Provisioned via IaC
* Immutable
* Rebuildable
* Drift-detectable

Manual console changes must gradually be eliminated.

---

## Phase 5: Cultural Shift Enablement

Leadership must communicate:

* Automation does not remove ownership
* It increases resilience
* SME knowledge must be codified
* Documentation + pipelines replace tribal knowledge

This is a mindset evolution, not a job displacement.

---

# 4. Benefits to EMS

Transitioning to the Cattle model provides EMS with:

## Operational Benefits

* Reduced MTTR
* Lower incident severity
* Predictable recovery
* Reduced dependency on individual SMEs

---

## Architectural Benefits

* Independent scaling of applications
* Clear service boundaries
* Reduced blast radius
* Improved isolation

---

## Financial Benefits

* Elastic scaling
* Avoidance of over-provisioned vertical machines
* Better resource utilisation
* Lower long-term operational overhead

---

## Governance & Compliance Benefits

* Infrastructure traceability
* Reduced configuration drift
* Improved audit posture
* Clear change tracking

---

# 5. Risks of Not Transitioning

If EMS remains in a partial “Pets” model:

* Shared server fragility increases
* SME dependency grows
* Scaling becomes costlier
* Incident recovery remains manual
* Cloud value remains unrealised

The organisation risks stagnating in a hybrid operational model that captures cost but not capability.

---

# 6. Strategic Position for EMS

Flow Control demonstrates that EMS already has capability in CI/CD and automation.

The next step is consistency across all application domains.

The objective is not to eliminate legacy systems overnight — but to progressively:

* Isolate services
* Containerise where feasible
* Remove shared server dependency
* Codify infrastructure
* Shift scaling from vertical to horizontal

EMS does not need to rebuild everything; it needs to standardise the direction of travel.

