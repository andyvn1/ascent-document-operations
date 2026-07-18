# Ascent Document Operations — Master Plan

> Source of truth for scope, projects, roadmap, and working method.
> Referenced by `CLAUDE.md`. Task IDs in `config/tasks.yaml` are generated from §8.
> NOTE: Notion synchronization (§9, §11 in part) has been DROPPED. GitHub Issues are
> the only project-management system. Sections are preserved for context.

Act as a senior software architect, technical project manager, Python engineer, cloud engineer, AI engineer, and engineering mentor.

I want you to help me plan and build a real software business while teaching me how every important part works.

My goals are:

1. Build a potentially sellable AI automation product.
2. Learn backend development, cloud architecture, AI engineering, APIs, databases, security, testing, DevOps, and deployment.
3. Create a portfolio-quality software engineering project.
4. Automate my project management.
5. Automatically create GitHub Issues for every development task.
6. Initially run the application using cloud services.
7. Eventually move suitable AI inference workloads to a local AI server.

Do not only generate code for me. Teach me how the system works while we build it incrementally.

---

# 1. Business Idea

The business will be called:

## Ascent Document Operations

The company will provide AI-powered document, email, and workflow automation for small and midsize businesses.

The software should receive business documents or emails, extract important information, validate the information, identify missing or uncertain fields, present the result for human approval, and then send the approved information to another business system.

The customer is not buying access to an AI model or GPU.

The customer is buying outcomes such as:

* Less manual data entry
* Faster document processing
* Fewer mistakes
* Faster customer responses
* Better document organization
* Reduced administrative labor
* Better tracking and audit history
* Easier integration between email, documents, and business software

---

# 2. Initial Product

The first product will focus on:

## Construction Invoice and Change-Order Automation

Construction companies and subcontractors commonly receive:

* Invoices
* Change orders
* Purchase orders
* Vendor quotes
* Inspection reports
* Work orders
* Project-related emails
* Contract documents
* Receipts
* Delivery documents

Employees often manually read these documents and copy information into spreadsheets, accounting systems, project-management systems, or CRMs.

The application should initially automate invoices and change orders.

## Invoice processing

Extract:

* Vendor name
* Invoice number
* Invoice date
* Due date
* Project name
* Customer name
* Purchase-order number
* Subtotal
* Tax
* Total
* Currency
* Payment terms
* Line items
* Quantity
* Unit price
* Description
* Cost code

## Change-order processing

Extract:

* Project name
* Change-order number
* Request date
* Requesting company
* Description
* Reason for the change
* Requested amount
* Schedule impact
* Approver
* Status
* Related contract or purchase order
* Supporting documentation

The product must allow an employee to review and correct the extracted information before approving it.

It must not automatically approve payments, contracts, or legally significant decisions.

---

# 3. Future Product Ideas

Design the architecture so the company can later add the following products.

## Product Idea 1: Distributor Purchase-Order Automation

Target customers:

* Wholesalers
* Equipment distributors
* Parts suppliers
* Industrial suppliers

Functions:

* Read purchase orders from PDFs and emails
* Extract product numbers and quantities
* Match customer product codes
* Validate pricing
* Detect missing information
* Create order records
* Draft confirmation emails
* Flag inventory problems

## Product Idea 2: Property-Management Workflow Automation

Functions:

* Process maintenance requests
* Categorize emergencies
* Extract tenant and property information
* Route requests to vendors
* Search leases and policies
* Process vendor invoices
* Summarize inspection reports
* Track maintenance history

## Product Idea 3: RFP and Security Questionnaire Assistant

Target customers:

* Government contractors
* Software companies
* MSPs
* Engineering firms
* Cybersecurity consultancies

Functions:

* Upload RFPs and questionnaires
* Separate individual questions
* Search approved company answers
* Draft responses
* Cite the source used
* Flag unanswered questions
* Export completed Word or Excel files
* Track approvals and answer history

## Product Idea 4: Accounting Document Intake

Functions:

* Classify invoices and receipts
* Extract accounting information
* Detect duplicate invoices
* Request missing documents
* Prepare bookkeeping entries
* Route exceptions to staff
* Export information to accounting software

## Product Idea 5: Customer Support Document Assistant

Functions:

* Search company manuals and policies
* Read incoming support requests
* Find related historical cases
* Draft responses
* Suggest troubleshooting steps
* Summarize conversations
* Escalate uncertain requests to employees

## Product Idea 6: Email-to-Workflow Automation

Functions:

* Watch a customer-specific inbox
* Classify incoming emails
* Extract attachments
* Create business records
* Assign work
* Draft replies
* Track workflow status
* Notify employees of exceptions

The first implementation must remain focused on construction invoices and change orders, but the architecture should not prevent these future products.

---

# 4. Cloud-First and Local AI Strategy

The system must initially work entirely with cloud services.

Keep the following components in the cloud:

* Public web application
* Customer dashboard
* Public API
* Authentication
* Authorization
* PostgreSQL database
* Object storage
* Background-job queue
* Workflow state
* Audit records
* Monitoring
* Logging
* Billing placeholders
* Webhook delivery
* Email intake
* Customer configuration

Initially use cloud AI APIs for:

* Document classification
* Information extraction
* Structured JSON generation
* Summarization
* Draft email responses
* Embeddings
* Document search

Later, allow suitable AI workloads to move to a local AI server.

Possible local AI workloads:

* Document classification
* Structured extraction
* Embedding creation
* Summarization
* Background processing
* Document search
* Batch evaluation
* Local model inference

Do not move the public application, authentication, database, or critical customer-facing services to the local server.

The local AI server should operate as a private inference worker connected securely to the cloud application.

The system must support:

* Cloud AI as the initial provider
* Local AI as a future provider
* Health checks
* Timeouts
* Retries
* Queued processing
* Cloud fallback
* Provider selection
* Cost tracking
* Latency tracking
* Customer usage limits

---

# 5. Learning Requirement

My goal is to learn while building.

Do not generate the whole application as one unexplained code dump.

For every phase:

1. Explain what we are building.
2. Explain the business reason.
3. Explain the technical concepts.
4. Explain the architecture decision.
5. Show the files being created or modified.
6. Generate the implementation.
7. Walk through the important code.
8. Provide commands to run it.
9. Describe the expected result.
10. Create tests.
11. Give me a practical exercise.
12. Give me a completion checklist.
13. Suggest a Git branch and commit message.

Use this development loop:

```text
Learn the concept
        ↓
Make an architecture decision
        ↓
Implement a small feature
        ↓
Run it locally
        ↓
Test it
        ↓
Inspect the result
        ↓
Complete a learning exercise
        ↓
Commit the working checkpoint
```

Do not assume that I understand a tool only because I have software engineering experience.

Explain important concepts clearly without oversimplifying them.

---

# 6. Learning Objectives

By completing the project, I should understand:

## Product engineering

* Identifying a business problem
* Customer discovery
* Product requirements
* MVP definition
* Non-goals
* Acceptance criteria
* Pilot design
* Measuring business value
* Pricing a software service

## Python engineering

* Python project structure
* Dependency management
* Type hints
* Pydantic
* Protocols and interfaces
* Error handling
* Logging
* Environment variables
* CLI applications
* Unit tests
* Integration tests

## Backend engineering

* REST APIs
* FastAPI
* Request validation
* Response schemas
* Service layers
* Repository layers
* Authentication
* Authorization
* Multitenancy
* Pagination
* File uploads
* Webhooks
* Idempotency
* Background jobs
* Retry handling

## Database engineering

* PostgreSQL
* Data modeling
* Primary keys
* Foreign keys
* Relationships
* Transactions
* Indexes
* Migrations
* Audit logs
* Workflow states
* Duplicate detection
* Tenant isolation

## AI application engineering

* Prompt design
* Structured model output
* JSON schema validation
* Document classification
* Information extraction
* Confidence scoring
* Embeddings
* Retrieval-augmented generation
* Evaluation datasets
* Hallucination control
* Human approval
* Model-provider abstraction
* Local inference
* Cloud inference

## Cloud engineering

* Application hosting
* Managed PostgreSQL
* Object storage
* Job queues
* Secrets management
* Monitoring
* Logging
* Environments
* Backups
* Deployment
* Cost control
* Failure recovery

## DevOps

* Git
* GitHub
* Docker
* Docker Compose
* CI/CD
* GitHub Actions
* Health checks
* Configuration
* Automated testing
* Container deployment
* Release management
* Rollbacks

## Security

* Authentication versus authorization
* Tenant isolation
* Encryption in transit
* Encryption at rest
* Secure file uploads
* File validation
* Rate limiting
* Audit history
* Least privilege
* Secret management
* Threat modeling
* Data retention
* Local server security risks

## Project automation

* GitHub API
* YAML configuration
* Stable IDs
* Idempotent synchronization
* Duplicate prevention
* API pagination
* API rate limits
* Retry strategies
* State files

---

# 7. Main Development Projects

Organize the plan using the following projects.

## Project 1: Business Validation

Goals:

* Define the target customer
* Confirm the document-processing problem
* Interview possible customers
* Identify current manual workflows
* Estimate time and cost savings
* Define the pilot offer
* Create pricing assumptions

Deliverables:

* Customer persona
* Interview questions
* Customer workflow map
* Problem statement
* Value proposition
* Pilot proposal
* Initial pricing sheet
* ROI calculator

## Project 2: Product Requirements and Architecture

Goals:

* Define MVP requirements
* Define non-goals
* Define system boundaries
* Design cloud architecture
* Design the future local AI architecture
* Define acceptance criteria

Deliverables:

* Product requirements document
* System context diagram
* Container diagram
* Data-flow diagram
* Architecture decision records
* Threat model
* API specification
* Database design
* Cloud-to-local-AI migration plan

## Project 3: Project Management Automation

Goals:

* Represent the entire plan in YAML
* Create GitHub Issues automatically
* Keep the YAML plan and GitHub synchronized

Deliverables:

* Project configuration schema
* `tasks.yaml` (plus supporting config files)
* `create_github_issues.py`
* Automated tests
* Setup documentation

## Project 4: Backend Foundation

Goals:

* Create the backend application
* Add configuration
* Add logging
* Add database access
* Add tenant-aware architecture
* Add health checks

Deliverables:

* FastAPI backend
* PostgreSQL connection
* Database migrations
* Core data models
* Service layer
* Repository layer
* Tenant middleware
* Docker Compose
* Test framework

## Project 5: File and Document Intake

Goals:

* Accept PDFs and images
* Store original files securely
* Validate uploads
* Track document-processing status

Deliverables:

* Upload endpoint
* Object-storage interface
* Local development storage
* Cloud-storage adapter
* File-type validation
* File-size validation
* Document records
* Upload tests

## Project 6: AI Provider System

Goals:

* Prevent dependency on one model provider
* Support cloud AI
* Support future local AI
* Add retries and fallback

Deliverables:

* AI provider protocol
* Mock provider
* Cloud provider
* OpenAI-compatible local provider
* Provider router
* Timeout handling
* Retry handling
* Cost tracking
* Usage tracking
* Fallback logic

Use an interface similar to:

```python
from typing import Any, Protocol


class AIProvider(Protocol):
    def generate_structured_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> dict[str, Any]:
        ...

    def generate_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        ...

    def create_embeddings(
        self,
        *,
        texts: list[str],
    ) -> list[list[float]]:
        ...
```

## Project 7: Invoice Processing

Goals:

* Classify invoices
* Extract invoice fields
* Validate values
* Calculate confidence
* Detect duplicate invoices

Deliverables:

* Invoice schema
* Classification prompts
* Extraction prompts
* Structured-output validation
* Business validation rules
* Duplicate-detection logic
* Synthetic test invoices
* Evaluation tests

## Project 8: Change-Order Processing

Goals:

* Classify change orders
* Extract required information
* Validate amounts and dates
* Flag missing approvals
* Connect change orders to projects

Deliverables:

* Change-order schema
* Extraction workflow
* Validation rules
* Confidence scoring
* Synthetic test documents
* Evaluation tests

## Project 9: Human Review Dashboard

Goals:

* Show processed documents
* Highlight uncertain fields
* Allow corrections
* Approve or reject results
* Preserve the complete audit history

Deliverables:

* Review queue
* Document detail page
* Document preview
* Editable extraction form
* Confidence indicators
* Approval workflow
* Rejection workflow
* Audit timeline

## Project 10: Outputs and Integrations

Goals:

* Export approved data
* Send webhooks
* Process email attachments
* Prepare integration adapters

Deliverables:

* CSV export
* Webhook delivery
* Webhook signatures
* Webhook retries
* Email attachment intake
* Integration interface
* Mock accounting integration
* Delivery logs

## Project 11: Security and Reliability

Goals:

* Protect customer information
* Prevent cross-tenant access
* Detect failures
* Recover from outages

Deliverables:

* Authorization checks
* Rate limiting
* Audit logging
* Backup plan
* Data-retention settings
* Secure file rules
* Monitoring
* Alerts
* Incident-response procedure
* Disaster-recovery plan

## Project 12: Cloud Deployment

Goals:

* Deploy the MVP
* Create development and staging environments
* Add automated deployment checks

Deliverables:

* Docker image
* CI pipeline
* Staging deployment
* Database migration workflow
* Secrets configuration
* Monitoring setup
* Deployment guide
* Rollback guide

## Project 13: Local AI Migration

This project must happen after the cloud MVP works.

Goals:

* Run a local OpenAI-compatible inference server
* Connect it securely to the cloud
* Route background jobs to it
* Keep cloud fallback
* Benchmark capacity

Deliverables:

* Local inference deployment
* Docker configuration
* Secure tunnel or VPN design
* Service authentication
* Worker heartbeat
* Job routing
* Cloud fallback
* Model benchmarking
* Cost comparison
* Customer quotas
* Outage procedure

## Project 14: Pilot and Customer Launch

Goals:

* Demonstrate the product
* Onboard the first pilot customer
* Measure the business result

Deliverables:

* Landing page
* Demo environment
* Synthetic demo data
* Pilot proposal
* Onboarding checklist
* Data-processing summary
* Security overview
* Pricing sheet
* Outreach message
* ROI report
* Pilot success report

---

# 8. Thirty-Business-Day Initial Roadmap

Create the first detailed plan around these 30 business days.

## Week 1: Business and Product Definition

### Day 1

* Define the construction customer persona
* Define the invoice-processing problem
* Define the change-order problem
* Write the product vision
* Create the GitHub repository

### Day 2

* Map the current manual workflow
* Define expected business savings
* Write customer interview questions
* Define the pilot offer
* Define initial pricing assumptions

### Day 3

* Define MVP features
* Define non-goals
* Define functional requirements
* Define nonfunctional requirements
* Define acceptance criteria

### Day 4

* Create the cloud architecture
* Define system boundaries
* Define the future local AI role
* Create architecture diagrams
* Start architecture decision records

### Day 5

* Design the database
* Define tenant, user, document, extraction, workflow, and audit models
* Define API endpoints
* Review Week 1
* Complete the Week 1 knowledge check

## Week 2: Project Automation and Backend Foundation

### Day 6

* Create YAML schemas for projects, milestones, epics, and tasks
* Create validation models
* Add stable IDs
* Add dependency validation

### Day 7

* Build GitHub label and milestone setup
* Add dry-run mode
* Validate the full task plan

### Day 8

* Build GitHub Issue creation
* Create labels
* Create milestones
* Add duplicate prevention
* Add update behavior

### Day 9

* Create combined synchronization
* Add state persistence
* Add unit tests
* Create the full GitHub Issue backlog

### Day 10

* Initialize FastAPI
* Add Pydantic settings
* Add logging
* Add tests
* Add Docker Compose
* Review Week 2

## Week 3: Database and Document Intake

### Day 11

* Add PostgreSQL
* Configure migrations
* Create tenant and user models
* Create database tests

### Day 12

* Create document and file models
* Add workflow status
* Add audit-event model
* Add repository layer

### Day 13

* Build file-upload endpoint
* Add PDF and image validation
* Store original files
* Add synthetic fixtures

### Day 14

* Add background-job queue
* Create processing worker
* Add retries
* Add failure statuses
* Add idempotency

### Day 15

* Add authentication placeholder
* Add tenant authorization
* Add upload integration tests
* Review Week 3

## Week 4: AI and Invoice Processing

### Day 16

* Create the AI provider protocol
* Add mock provider
* Add provider configuration
* Add provider tests

### Day 17

* Add cloud AI provider
* Add structured-output validation
* Add timeouts and retries
* Track cost and usage

### Day 18

* Create invoice schema
* Implement invoice classification
* Implement invoice extraction
* Validate required fields

### Day 19

* Add confidence scoring
* Add numerical validation
* Add duplicate detection
* Create evaluation documents

### Day 20

* Run invoice evaluations
* Review extraction failures
* Improve prompts and validation
* Review Week 4

## Week 5: Change Orders and Human Review

### Day 21

* Create change-order schema
* Implement classification
* Implement extraction
* Add validations

### Day 22

* Create review queue API
* Add filtering
* Add pagination
* Add tenant authorization

### Day 23

* Create document detail API
* Allow field correction
* Store original and corrected values
* Add audit events

### Day 24

* Add approval workflow
* Add rejection workflow
* Add reviewer comments
* Add workflow tests

### Day 25

* Build a simple review dashboard
* Show previews
* Highlight low-confidence fields
* Review Week 5

## Week 6: Integration, Deployment, and Demo

### Day 26

* Add CSV export
* Add webhook delivery
* Add webhook signatures
* Add webhook retries

### Day 27

* Add email attachment intake
* Match emails to tenants
* Add integration adapter interface
* Add mock accounting integration

### Day 28

* Add CI
* Add container build
* Add security checks
* Create cloud deployment documentation

### Day 29

* Deploy a staging version
* Build a synthetic customer demo
* Create ROI calculator
* Create pilot and outreach materials

### Day 30

* Run end-to-end tests
* Fix critical defects
* Review MVP acceptance criteria
* Generate the next 30-day backlog
* Prepare a customer demonstration
* Complete the final knowledge check

---

# 9. Project Tracking Requirements (GitHub Issues)

> Notion synchronization has been dropped. GitHub Issues are the single tracker.
> See `CLAUDE.md` §4 for the operational conventions (issue template, marker,
> idempotency rules, labels, milestones, gh commands).

Requirements:

* The entire plan is represented in `config/tasks.yaml` with stable task IDs.
* One GitHub Issue per actionable task.
* Issues carry acceptance criteria, deliverables, dependencies, estimates,
  priority, week/day, and learning objectives.
* Synchronization is idempotent: create missing issues, update managed issues
  when YAML changes, never create duplicates.
* Managed issues are identified by a hidden marker:

```html
<!-- ascent-task-id: TASK-001 -->
```

* Issue title format:

```text
[TASK-001] Define product vision
```

* Supported operations (script or Claude Code driven):

```bash
sync                 # create/update everything
sync --dry-run       # print planned changes, mutate nothing
validate             # YAML schema, duplicate IDs, dependency graph
sync --week 1        # limit scope
sync --project "Invoice Processing"
```

* A provider interface should allow Jira or Linear later; only GitHub is
  implemented now.

---

# 10. Project Configuration

Use YAML files:

```text
config/
├── projects.yaml
├── milestones.yaml
├── epics.yaml
├── tasks.yaml
├── labels.yaml
└── settings.example.yaml
```

Every task must contain:

```yaml
id: TASK-001
title: Define product vision
description: >
  Define the first product, target customer, business problem,
  expected outcome, boundaries, and future product opportunities.
project: Business Validation
epic: Product Definition
milestone: Business and MVP Definition
day: 1
week: 1
priority: high
status: not_started
estimate_hours: 2
labels:
  - type:product
  - priority:high
dependencies: []
acceptance_criteria:
  - The target construction customer is defined.
  - The invoice-processing problem is described.
  - The change-order problem is described.
  - The product boundaries are documented.
deliverables:
  - docs/product-vision.md
learning_objectives:
  - Explain the difference between a product and a technical feature.
  - Explain why the initial product needs a narrow customer niche.
```

Use stable IDs for every project, epic, milestone, and task.

---

# 11. Learning Format for Every Phase

Use this exact structure:

```markdown
# Phase Name

## What You Will Learn

## Business Objective

## Technical Objective

## Concepts Explained

## Architecture Decision

## Files Created or Modified

## Implementation

## Code Walkthrough

## Commands to Run

## Expected Result

## Tests

## Common Errors

## Learning Exercise

## Knowledge Check

## Git Checkpoint

## Completion Checklist
```

For every Git checkpoint provide:

* Branch name
* Suggested commit message
* Files changed
* Tests that should pass
* What the commit represents

Example:

```text
Branch:
feature/document-upload

Commit:
feat: add tenant-aware document upload
```

---

# 12. Exercises and Knowledge Checks

After each major milestone, give one or two exercises using the actual project.

Examples:

* Add another invoice field.
* Add another validation rule.
* Add a new document status.
* Write an additional API test.
* Add a GitHub label.
* Add a new webhook event.
* Add a new AI provider.
* Add property-management maintenance requests as a document type.

For each exercise provide:

* Objective
* Relevant files
* Hints
* Verification instructions

Do not immediately reveal the answer in the main exercise section.

Provide a separate reference solution after the exercise for comparison after attempting it.

At the end of each week, provide five knowledge-check questions and an answer key.

---

# 13. Architecture Decision Records

For every major technical decision create:

```markdown
# Decision

# Context

# Options Considered

# Decision Rationale

# Tradeoffs

# Migration Impact
```

Decisions must include:

* FastAPI selection
* PostgreSQL selection
* Object storage selection
* Background-job queue
* Tenant isolation
* AI provider abstraction
* Human approval
* Cloud-first architecture
* Local AI worker architecture
* Cloud fallback
* GitHub duplicate prevention

---

# 14. Repository Structure

Start with a repository similar to:

```text
ascent-document-operations/
├── apps/
│   ├── api/
│   ├── worker/
│   └── web/
├── config/
│   ├── projects.yaml
│   ├── milestones.yaml
│   ├── epics.yaml
│   ├── tasks.yaml
│   └── labels.yaml
├── scripts/
│   ├── create_github_issues.py
│   └── validate_plan.py
├── src/
│   ├── ascent/
│   │   ├── ai/
│   │   ├── documents/
│   │   ├── invoices/
│   │   ├── change_orders/
│   │   ├── integrations/
│   │   ├── security/
│   │   └── shared/
│   └── project_automation/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/
│   ├── product/
│   ├── architecture/
│   ├── business/
│   ├── security/
│   └── learning/
├── .env.example
├── docker-compose.yml
├── pyproject.toml
├── README.md
└── Makefile
```

Adjust the structure when needed, but explain the reason for every significant change.

---

# 15. Technical Preferences

Use:

* Python 3.12
* FastAPI
* PostgreSQL
* SQLAlchemy
* Alembic
* Pydantic
* `httpx`
* `pytest`
* `ruff`
* `mypy` or `pyright`
* `typer`
* `PyYAML`
* Docker
* Docker Compose
* GitHub Actions

Use a background-job solution appropriate for an MVP and explain the alternatives.

Do not introduce unnecessary enterprise complexity.

For every abstraction, explain:

* Why it is needed
* Whether it is needed now
* What simpler option exists
* What future problem it prevents

---

# 16. Testing Requirements

Create tests for:

* YAML validation
* Duplicate stable IDs
* Missing projects
* Invalid dependencies
* Circular dependencies
* Business-day date calculation
* GitHub Issue creation
* GitHub Issue updates
* GitHub duplicate prevention
* File uploads
* Tenant isolation
* Invoice extraction validation
* Change-order extraction validation
* Duplicate invoices
* Approval workflow
* Webhook retries
* Cloud-provider failures
* Local-provider failures
* Cloud fallback
* Dry-run behavior

Mock external services in unit tests.

---

# 17. Documentation

Create:

```text
docs/
├── product/
│   ├── product-vision.md
│   ├── customer-persona.md
│   ├── requirements.md
│   └── pilot-plan.md
├── architecture/
│   ├── system-architecture.md
│   ├── database-design.md
│   ├── ai-provider-design.md
│   ├── synchronization-design.md
│   └── local-ai-migration-plan.md
├── business/
│   ├── pricing.md
│   ├── customer-interviews.md
│   ├── roi-calculator.md
│   └── outreach-plan.md
├── security/
│   ├── threat-model.md
│   ├── data-protection.md
│   └── incident-response.md
└── learning/
    ├── master-plan.md
    ├── learning-roadmap.md
    ├── backend-concepts.md
    ├── database-concepts.md
    ├── cloud-concepts.md
    ├── ai-engineering-concepts.md
    ├── security-concepts.md
    ├── testing-concepts.md
    ├── devops-concepts.md
    ├── github-api-guide.md
    ├── local-ai-guide.md
    └── interview-review-guide.md
```

The interview guide should help explain:

* The business problem
* Target customer
* Product architecture
* Database design
* Multitenancy
* AI provider abstraction
* Document workflow
* Human approval
* Security
* Testing
* Failure handling
* Cloud deployment
* Local AI migration
* Tradeoffs
* Lessons learned

---

# 18. Required Working Method

Do not immediately generate every application file.

First generate and complete the project automation so the entire plan exists as
GitHub Issues.

Use this order:

## Phase 1

* Finalize business projects
* Create milestones and epics
* Generate the complete YAML task plan
* Validate task dependencies

## Phase 2

* Build GitHub Issue synchronization
* Test it
* Explain GitHub permissions
* Create the tickets

## Phase 3

* Begin the actual product one milestone at a time
* Teach each concept
* Let me run and test each feature
* Give me exercises
* Create Git checkpoints

Do not skip directly to the completed product.

The final outcome must be:

1. A complete GitHub Issue backlog.
2. A cloud-first AI document automation MVP.
3. A future path to local AI inference.
4. A portfolio-quality software project.
5. A structured learning experience that allows Andy to understand and explain what he built.
