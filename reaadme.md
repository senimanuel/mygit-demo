# EMS Transition Strategy: From Pets to Cattle

## Context

EMS operates a mixed infrastructure model across multiple application domains:

* **Flow Control**
* **Marketing**
* **TAPI**
* **Hygiene**

While EMS has adopted modern delivery practices in certain areas, infrastructure management across the organisation still reflects elements of the traditional “Pets” model.

This page outlines:

* EMS’s current state
* The specific challenges unique to EMS
* A pragmatic transition approach
* How EMS can leverage existing assets (including test servers)
* The measurable benefits of adopting a Cattle mindset

---

# 1. Current State at EMS

## 1.1 Flow Control

Flow Control demonstrates a more modern delivery approach.

It currently uses:

* CI/CD pipelines
* Jenkins
* Bitbucket for version control
* Automated deployment patterns

Flow Control operates relatively independently from other EMS applications and is the closest workload to being “Cattle-ready.”

However:

* Some services still run on long-lived instances
* Full immutability has not yet been adopted
* Infrastructure may still depend on instance-level configuration

Flow Control provides a strong foundation for broader transformation.

---

## 1.2 Marketing, TAPI, Hygiene

These applications exhibit stronger “Pets” characteristics.

Common patterns include:

* Heavy SME dependency
* Manual server configuration
* Limited automation
* Long-lived servers
* Vertical scaling (increasing CPU/memory rather than scaling out)

Operational implications:

* High knowledge concentration
* Greater configuration drift risk
* Limited elasticity
* Slower recovery during incidents

These workloads represent the primary transformation challenge for EMS.

---

## 1.3 “Bad Job Servers” — Repositioned as a Strategic Asset

The “Bad Job Servers” are primarily used for:

* Testing purposes
* Internal workloads
* Partial service execution
* Non-production scenarios

They are not core production-critical infrastructure.

This significantly lowers transition risk and creates a strategic opportunity.

Rather than viewing them as architectural debt, EMS can treat them as:

* A containerisation test bed
* A refactoring validation platform
* A CI/CD expansion environment
* A controlled innovation sandbox

If formalised properly, they become an enabler of transformation rather than a liability.

---

# 2. Key Challenges EMS Faces

## 2.1 Cultural & Knowledge Dependency

Several applications rely heavily on SMEs for operational continuity.

Risks include:

* High bus factor
* Undocumented server configurations
* Resistance to disposability
* Perceived loss of control with automation

The mindset shift required is significant: infrastructure resilience must not depend on individual expertise.

---

## 2.2 Vertical Scaling Bias

Marketing, TAPI, and Hygiene predominantly scale by:

* Increasing processor allocation
* Increasing memory
* Maintaining single-instance architecture

Limitations of this approach:

* Hardware ceiling constraints
* Higher downtime risk
* Reduced elasticity
* Inefficient cloud cost utilisation

This pattern underutilises cloud-native strengths.

---

## 2.3 Application Architecture Constraints

Some EMS applications were not designed for:

* Containerisation
* Stateless execution
* Dynamic configuration
* Independent scaling

Transitioning to Cattle will require:

* Externalising configuration
* Removing local state dependencies
* Refactoring tightly coupled services
* Redefining service boundaries

This is architectural evolution, not simple migration.

---

## 2.4 Inconsistent Delivery Practices

Flow Control uses CI/CD and version-controlled deployments, while other applications rely more heavily on manual processes.

This inconsistency:

* Slows standardisation
* Increases operational risk
* Creates uneven maturity levels
* Complicates governance enforcement

Standardisation is critical for organisation-wide transformation.

---

# 3. EMS Transition Approach

The transition must be phased, controlled, and pragmatic.

It should prioritise learning and validation before broad enforcement.

---

## Phase 1: Classification & Maturity Mapping

Group EMS applications into:

1. **Cloud-ready (Flow Control candidates)**
2. **Refactor-required (Marketing, TAPI, Hygiene)**
3. **Legacy containment workloads**

This enables targeted strategy rather than blanket mandates.

---

## Phase 2: Use “Bad Job Servers” as a Pilot Platform

Formalise these test servers as a containerisation sandbox.

Actions:

* Identify Java-based components suitable for containerisation
* Package services into Docker images
* Externalise configuration
* Introduce health checks
* Validate stateless execution

This approach:

* Minimises production risk
* Demonstrates feasibility
* Builds internal engineering confidence
* Reduces SME resistance

---

## Phase 3: Expand CI/CD Beyond Flow Control

Extend the existing Jenkins + Bitbucket model to:

* Marketing
* TAPI
* Hygiene

Begin with non-production deployments.

Objective:

* Remove manual deployment steps
* Codify infrastructure changes
* Standardise delivery practices

---

## Phase 4: Shift from Vertical to Horizontal Scaling

Where feasible:

* Run multiple service instances
* Introduce load balancing
* Test failure scenarios
* Validate automated recovery

Even within test environments, this begins mindset transformation.

---

## Phase 5: Enforce Infrastructure as Code

Gradually introduce:

* Immutable deployments
* Drift detection
* Reduced manual console access
* Standardised build pipelines

Automation should become the default path.

---

# 4. Benefits to EMS

## Operational Benefits

* Reduced MTTR
* Lower incident severity
* Predictable recovery
* Reduced SME dependency

---

## Architectural Benefits

* Independent scaling per application
* Clear service isolation
* Reduced blast radius
* Greater system resilience

---

## Financial Benefits

* Elastic resource utilisation
* Reduced over-provisioning
* Better alignment of cost to demand
* Lower long-term operational overhead

---

## Governance & Compliance Benefits

* Improved infrastructure traceability
* Stronger audit posture
* Reduced configuration drift
* Standardised deployment evidence

---

# 5. Risks of Not Transitioning

If EMS maintains the current mixed model:

* SME dependency will deepen
* Shared infrastructure fragility will persist
* Vertical scaling costs will increase
* Incident recovery will remain manual
* Cloud value will remain partially unrealised

The organisation risks absorbing cloud cost without achieving cloud capability.

---

# 6. Strategic Position for EMS

EMS is not starting from zero.

Flow Control already demonstrates:

* CI/CD maturity
* Version-controlled deployments
* Automation capability

The opportunity now is to:

* Extend this maturity consistently
* Leverage test environments for innovation
* Containerise selectively and pragmatically
* Reduce vertical scaling dependency
* Standardise infrastructure governance

EMS does not need disruptive transformation.

It needs structured progression.

The objective is steady, measurable movement from long-lived, manually managed infrastructure toward immutable, automated, horizontally scalable systems.
