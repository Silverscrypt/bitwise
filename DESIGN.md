# Bitwise — Design & Architecture Plan

**Project:** Bitwise  
**Organization:** BITS  
**Status:** Initial Design / Architecture Planning  
**Version:** 1.2  
**Last updated:** 2026-11-06  
**Primary Platform:** Discord  
**Implementation Language:** Python

---

# 1. Project Overview

## 1.1 Purpose

Bitwise is an internal Discord automation and organization-management bot designed to streamline recruitment, manage organizational roles, coordinate project teams, and automate common administrative tasks.

The primary objective is to reduce manual administrative work while establishing a maintainable system that future organization members can operate and extend.

The architecture should remain configurable, modular, and well-documented to support future organizational leadership and maintenance.

## 1.2 Goals

- Streamline recruitment and onboarding through rolling applications and automated technical assessment verification.
- Simplify organizational role management through Discord slash commands.
- Allow Project Leads and Project Managers to maintain their project rosters.
- Automate onboarding and organizational communications.
- Provide structured communication channels through a ticketing system.
- Reduce repetitive administrative work.
- Establish a maintainable internal tool that can be handed over to future organization members.
- Build recruiting first, so the core onboarding loop works before adding further automations.
- Develop Bitwise as an open-source project that other contributors can set up and extend.

---

# 2. Functional Requirements

Bitwise will initially consist of four major feature categories.

## 2.1 Recruiting and Onboarding

### Objective

Automate the transition from applicant to organization member.

Applicants join the Discord server with limited access and are prompted to go to the BITS website, where they create an account linked to their Discord account and complete onboarding — the online technical assessment and any other onboarding tasks.

Successful assessment completion is recorded by the website in the shared database, and Bitwise detects it there. Applicants who are approved by an Officer's judgement of the other prerequisites are then given the "Freelancer" role, which serves to give access to only view the entire server's list of project channels.

An authorized Officer must review and approve the applicant before membership is granted.

### Proposed Workflow

1. Applicant joins the Discord server with limited access.
2. Bitwise prompts the applicant to visit the BITS website and create an account linked to their Discord account.
3. Applicant completes onboarding on the website: the online technical assessment and any other onboarding tasks.
4. The website records the completed assessment in the shared database.
5. Bitwise detects the recorded result and moves the applicant to a pending approval state.
6. An authorized Officer reviews the applicant's other deliverables.
7. Officer approves or rejects the applicant.
8. Upon approval, Bitwise assigns the `Freelancer` role.
9. Bitwise sends the applicant appropriate onboarding instructions and guides.

### Application States

|                    |                                                                                          |
| ------------------ | ---------------------------------------------------------------------------------------- |
| State              | Description                                                                              |
| Assessment Pending | Applicant has not completed the assessment.                                              |
| Assessment Passed  | Applicant successfully completed the assessment.                                         |
| Pending Approval   | Applicant is awaiting Officer review.                                                    |
| Approved           | Applicant has been accepted into the organization.                                       |
| Rejected           | Applicant was not accepted. May apply again without the need to take another assessment. |

### Requirements

- Assessment results must be associated with the correct Discord member.
- Account linking must use the stable Discord user ID. Discord OAuth is preferred; linking by username alone is fragile because usernames can change.
- Assessment completion must not automatically grant organizational membership.
- Only Officers (or potentially dedicated recruiters) may approve or reject applicants.
- Approval must trigger the appropriate Discord role assignment for access.
- Duplicate assessment events must not result in duplicate approvals or inconsistent state.
- Important application actions must be recorded in an audit log.
- Applicants should receive clear status and onboarding information.

---

## 2.2 Role Automation

### Objective

Provide authorized organization members with tools to manage organizational roles, member competencies, and project rosters.

Role management should be performed through Discord slash commands.

### Role Categories

|                         |                                        |                                                      |
| ----------------------- | -------------------------------------- | ---------------------------------------------------- |
| Category                | Examples                               | Purpose                                              |
| Membership              | Freelancer                             | Identifies organization membership.                  |
| Functional              | Intern, Developer, Designer            | Identifies member competencies and responsibilities. |
| Organizational          | Officer, Project Lead, Project Manager | Establishes organizational authority.                |
| Project                 | Project Alpha, Project Beta            | Identifies working projects.                         |
| Special (Not in effect) | Mentor, Recruiter, etc.                | Identifies additional community responsibilities.    |

### Confirmed Role Rules

- `Freelancer` is the standard verified membership role.
- Members may hold multiple functional roles simultaneously.
- Members may belong to multiple projects, depending on their circumstances.
- Project assignments must be stored independently from functional roles.
- Project Leads and Project Managers may manage only projects to which they are assigned and authorized.
- Lower-level users must not be able to modify higher-level roles or permissions.
- Role assignment must respect Discord's role hierarchy.

### Proposed Slash Commands

|                   |                                             |                               |
| ----------------- | ------------------------------------------- | ----------------------------- |
| Command           | Purpose                                     | Authorization                 |
| `/role add`       | Assign a functional role.                   | Authorized administrators     |
| `/role remove`    | Remove a functional role.                   | Authorized administrators     |
| `/project assign` | Add a member to a project.                  | Authorized project leadership |
| `/project remove` | Remove a member from a project.             | Authorized project leadership |
| `/project roster` | Display a project's members.                | Authorized project leadership |
| `/member info`    | Display relevant member information.        | Permission-dependent          |
| `/setup`          | Diagnose bot configuration and permissions. | Officers / Administrators     |

Command names are preliminary and may change during implementation.

### Permission Hierarchy

The application should distinguish between organizational authority and project-specific authority.

Proposed authority model:

- \***\*Officers:\*\*** Organization-wide administrative authority, including recruitment approval and organizational role management.
- \***\*Project Leads:\*\*** Management authority over their assigned projects.
- \***\*Project Managers:\*\*** Management authority over their assigned projects, subject to configured permissions.
- \***\*Members:\*\*** Standard participation and access based on their assigned roles.

Project Leads and Project Managers must not receive unrestricted organization-wide role-management access merely because of their Discord role.

Bitwise must independently validate authorization before executing administrative commands.

---

## 2.3 Ticketing

### Objective

Provide a structured communication system through temporary private Discord channels.

Members should be able to request assistance, provide feedback, ask questions, and communicate sensitive concerns to the appropriate organization members.

### Ticket Categories

|                 |                                   |
| --------------- | --------------------------------- |
| Category        | Intended Audience                 |
| Suggestions     | Designated organization reviewers |
| Questions       | Relevant support personnel        |
| Community Help  | Mentors                           |
| Appeals / Cases | Officers                          |

### Proposed Ticket Lifecycle

`Open → Assigned → In Progress → Resolved → Closed`

### Requirements

- Members must be able to open tickets through slash commands or Discord interactions.
- Tickets should create private channels.
- Ticket visibility must be restricted to the requester and authorized personnel.
- Ticket permissions must be determined by ticket category.
- Authorized personnel should be able to assign and resolve tickets.
- Ticket history should be retained according to organizational policy.
- Sensitive appeals and cases must have particularly strict access controls.
- Important ticket actions should be recorded.

### Potential Future Features

- Ticket transcripts.
- Mentor assignment.
- Ticket priority.
- Ticket categories and templates.
- Automatic inactivity reminders.
- Ticket statistics and reporting.

---

## 2.4 Automated Messages

### Objective

Reduce repetitive questions and improve onboarding by automatically providing useful information.

### Proposed Messages

- Welcome messages and server navigation guides.
- Instructions for completing the technical assessment.
- Personal project prerequisites.
- Organization participation guidelines.
- Development resources.
- Computer science clubs and opportunities.
- Frequently asked questions.

### Requirements

- Message content should be configurable without modifying Python source code.
- Messages should be triggered by appropriate events or commands.
- Administrative users should be able to update resource information.
- Automated messages should avoid unnecessary repetition or spam.

---

# 3. Non-Functional Requirements

These requirements describe how Bitwise should operate, rather than specific features.

|                 |                                                                                                             |
| --------------- | ----------------------------------------------------------------------------------------------------------- |
| Category        | Requirement                                                                                                 |
| Security        | Administrative commands must enforce authorization checks.                                                  |
| Authorization   | Permissions must be validated by Bitwise, not inferred solely from command visibility.                      |
| Reliability     | Discord API failures must be handled gracefully.                                                            |
| Data Integrity  | Database records and Discord role assignments must remain consistent.                                       |
| Maintainability | Future Officers should be able to configure Bitwise without modifying application code for routine changes. |
| Auditability    | Important administrative actions must be recorded.                                                          |
| Privacy         | Private tickets and applicant information must have restricted access.                                      |
| Recovery        | Important organizational data must be backed up.                                                            |
| Extensibility   | New features should be implementable without major architectural changes.                                   |
| Documentation   | Setup, configuration, deployment, and maintenance procedures must be documented.                            |

---

# 4. Technical Stack

## 4.1 Initial Technology Choices

|                      |                            |                                                                           |
| -------------------- | -------------------------- | ------------------------------------------------------------------------- |
| Component            | Technology                 | Purpose                                                                   |
| Programming Language | Python                     | Main application implementation                                           |
| Discord Integration  | discord.py                 | Discord Gateway, events, slash commands, role management                  |
| Configuration        | python-dotenv              | Local environment configuration                                           |
| Database             | PostgreSQL                 | Persistent organizational data, shared with the BITS website              |
| Website Integration  | Shared PostgreSQL database | Website writes assessment results; Bitwise detects them via LISTEN/NOTIFY |
| Testing              | pytest                     | Automated testing                                                         |
| Version Control      | Git and GitHub             | Source control and collaboration                                          |
| Local Development    | Docker Compose             | One-command PostgreSQL setup for contributors                             |
| Deployment           | To be determined           | Run Bitwise reliably outside development machines                         |

## 4.2 Database Strategy

PostgreSQL will be used from the start.

Reasons:

- The BITS website and Bitwise share one database: the website writes assessment results and member data, and Bitwise reads them.
- It scales for future features and additional contributors.
- It fits an open-source project: contributors can run the full stack locally with Docker Compose.
- Relational modeling, constraints, and transactions are supported natively.
- Starting with PostgreSQL avoids a migration later, when the database already holds live member and application data.

## 4.3 Configuration Strategy

Configuration should be separated from application logic.

Sensitive information and environment-specific settings should be stored in environment variables.

Example `.env.example`:

DISCORD_TOKEN=
GUILD_ID=

DATABASE_URL=postgresql://bitwise:bitwise@localhost:5432/bitwise

ASSESSMENT_API_SECRET=

The actual `.env` file must never be committed to version control.

Discord role IDs, project mappings, and other organizational configuration should eventually be stored in the database or a suitable configuration file rather than scattered throughout the Python source code.

---

# 5. Proposed System Architecture

Bitwise should follow a modular architecture with clear separation of responsibilities.

## 5.1 High-Level Architecture

                  DISCORD SERVER
                        |
                        |
                Discord Interactions
                        |
                        v
              +--------------------+
              | Bitwise Application |
              |      Python        |
              +--------------------+
                        |
          +-------------+-------------+
          |             |             |
          v             v             v
     Recruiting     Role Manager   Ticket Manager
          |             |             |
          +-------------+-------------+
                        |
                        v
                  Messaging System
                        |
                        v
            POSTGRESQL DATABASE
                        |
                        |
                 BITS WEBSITE
                        |
                        v
               Assessment Results

This represents the logical architecture, not necessarily separate deployed services. The website and Bitwise share the same PostgreSQL database: the website writes assessment results, and Bitwise detects them there.

## 5.2 Application Components

### Discord Interface

Responsible for:

- Receiving slash commands.
- Handling Discord events.
- Sending messages and notifications.
- Assigning and removing Discord roles.
- Creating and managing ticket channels.

### Recruiting Service

Responsible for:

- Processing assessment results.
- Tracking application status.
- Handling approval and rejection.
- Triggering onboarding.
- Preventing duplicate processing.

### Role Management Service

Responsible for:

- Assigning functional roles.
- Removing functional roles.
- Managing project assignments.
- Checking authorization.
- Maintaining consistency between database records and Discord roles.

### Ticket Management Service

Responsible for:

- Creating tickets.
- Managing ticket lifecycle.
- Applying channel permissions.
- Assigning tickets to appropriate personnel.
- Recording ticket history.

### Messaging Service

Responsible for:

- Welcome messages.
- Onboarding instructions.
- Resource messages.
- Automated notifications.

### Database Layer

Responsible for:

- Persistent member records.
- Role definitions.
- Project information.
- Project assignments.
- Application records.
- Ticket records.
- Audit logs.

### Website Integration

Responsible for:

- Detecting new assessment results in the shared database.
- Validating recorded results.
- Associating assessment results with Discord identities.
- Passing verified results to the recruiting service.

---

# 6. Database Design

The database should represent organizational relationships rather than storing all information directly inside a member record.

## 6.1 Proposed Tables

|                    |                                                 |
| ------------------ | ----------------------------------------------- |
| Table              | Responsibility                                  |
| `members`          | Discord identities and membership status.       |
| `roles`            | Configured organizational and functional roles. |
| `member_roles`     | Functional role assignments.                    |
| `projects`         | Project information and Discord role mappings.  |
| `project_members`  | Member-to-project relationships.                |
| `project_managers` | Project-specific management authorization.      |
| `applications`     | Assessment results and approval status.         |
| `tickets`          | Ticket metadata and lifecycle.                  |
| `audit_logs`       | Important administrative actions.               |

These are preliminary entities. The exact schema will be established through relational modeling before implementation.

## 6.2 Member Relationships

A member may have:

- One organizational membership status.
- Multiple functional roles.
- Multiple project assignments.
- Additional organizational or special responsibilities.

Example:

Member A
|
+-- Membership
| +-- Freelancer
|
+-- Functional Roles
| +-- Developer
| +-- Designer
|
+-- Projects
+-- Project Alpha
+-- Project Beta

## 6.3 Relational Modeling Principles

The database should use relational tables and foreign keys.

For example:

- A member should have a unique Discord user ID.
- An assessment result should record the Discord user ID, assessment type, result, and timestamp, so duplicate events can be detected and handled safely.
- Functional roles should be represented independently.
- Member-to-role assignments should be represented through a junction table.
- Project assignments should use a separate junction table.
- Project management authorization should be distinct from ordinary project membership.

Avoid storing comma-separated role or project names inside a member record.

Use database constraints and transactions where appropriate to preserve data integrity.

---

# 7. Authorization and Security Design

Security is particularly important because Bitwise will manage membership, organizational permissions, and private communication.

## 7.1 Authorization Principles

1. Apply the principle of least privilege.
2. Validate every administrative action.
3. Separate project-level permissions from organization-wide permissions.
4. Do not rely solely on Discord command visibility.
5. Check Discord role hierarchy before modifying roles.
6. Record important administrative actions.
7. Never expose secrets in source code or logs.

## 7.2 Project-Level Authorization

Project leadership authorization should be associated with specific projects.

For example:

Project Alpha
|
+-- Project Lead A
+-- Project Manager B

Project Beta
|
+-- Project Lead C
+-- Project Manager D

Project Lead A should not automatically have management permissions over Project Beta.

Bitwise should check the requesting user's authorization for the specific project before executing an operation.

## 7.3 Audit Logging

Important actions should generate audit records.

Examples:

- Applicant approved.
- Applicant rejected.
- Membership role assigned.
- Functional role added or removed.
- Project assignment created or removed.
- Project manager authorization changed.
- Ticket opened, assigned, or closed.

Audit records should identify the actor, target, action, timestamp, and relevant context.

---

# 8. Website Integration

The assessment website records successful assessment results in the shared PostgreSQL database, and Bitwise detects them there.

## 8.1 Proposed Workflow

Applicant completes assessment on the website
|
v
Website evaluates result and writes it to the
shared PostgreSQL database
|
v
Bitwise detects the new record (PostgreSQL
LISTEN/NOTIFY, with polling as a fallback)
|
v
Bitwise identifies the applicant by Discord user ID
|
v
Applicant enters pending approval
|
v
Officer reviews application
|
v
Bitwise grants Freelancer upon approval

## 8.2 Security Considerations

- Website writes must come from the authenticated website backend.
- Requests must be validated.
- Discord identities must be linked to assessment accounts securely.
- Discord accounts should be linked via OAuth, so Bitwise can rely on the stable Discord user ID rather than a changeable username.
- Duplicate events must be handled safely.
- Assessment results must not directly grant membership.
- Approval must remain restricted to Officers.
- Important events must be logged.

The BITS website is not built yet, so the record shape for an assessment result (Discord user ID, assessment type, result, timestamp) should be agreed before either side is built.

---

# 9. Project Structure

The application should eventually use a modular Python package structure.

bitwise/
|
+-- bot/
| |
| +-- **init**.py
| +-- main.py
| +-- config.py
| |
| +-- commands/
| | +-- verification.py
| | +-- roles.py
| | +-- projects.py
| | +-- tickets.py
| |
| +-- services/
| | +-- recruiting_service.py
| | +-- role_service.py
| | +-- project_service.py
| | +-- ticket_service.py
| | +-- messaging_service.py
| |
| +-- database/
| | +-- connection.py
| | +-- models.py
| | +-- repositories.py
| |
| +-- integrations/
| | +-- assessment_listener.py
| |
| +-- utils/
| +-- logging.py
|
+-- tests/
| +-- test_roles.py
| +-- test_projects.py
| +-- test_recruiting.py
|
+-- docs/
| +-- requirements.md
| +-- architecture.md
| +-- permissions.md
| +-- setup.md
| +-- maintenance.md
|
+-- data/
|
+-- .env.example
+-- .gitignore
+-- requirements.txt
+-- README.md

This is a target structure. Directories and modules should be introduced as the application grows rather than created prematurely.

---

# 10. Development Roadmap

Development should proceed through small, testable milestones.

## Milestone 1: Bot Foundation

\***\*Status: Completed\*\***

Deliverables:

- Discord application configured.
- Bot installed in test server.
- Python environment configured.
- Gateway connection established.
- Slash commands synchronized.
- `/ping` implemented.
- Basic logging and startup validation.

## Milestone 2: Role Management

\***\*Status: Basic functionality completed; expansion required\*\***

Deliverables:

- `/verify` development command.
- `/setup` diagnostic command.
- Discord role assignment.
- Role hierarchy validation.
- Functional role management.
- Project role management.
- Authorization checks.

Important: The current self-service verification command is for development only. Production membership must require an Officer-approved application.

The permanent membership role will be `Freelancer`.

## Milestone 3: Database

\***\*Status: Next major milestone — current focus, enables recruiting\*\***

Deliverables:

- Relational database design.
- PostgreSQL integration, with Docker Compose for local development.
- Member records.
- Role definitions.
- Functional role assignments.
- Project records.
- Project membership relationships.
- Project management authorization.
- Database constraints and transactions.
- Initial database tests.

## Milestone 4: Recruiting Integration

\***\*Status: Priority after the database — recruiting is built first.\*\***

Deliverables:

- Join gating with limited access and a prompt to the website.
- Discord OAuth account linking.
- Shared-database integration: the website writes assessment results, Bitwise detects them via LISTEN/NOTIFY.
- Application status tracking.
- Officer approval and rejection.
- Automated Freelancer assignment.
- Onboarding notifications.
- Audit logging.

## Milestone 5: Automated Messaging

Deliverables:

- Welcome messages.
- Onboarding instructions.
- Configurable resource messages.
- Organization guides.
- Administrative message configuration.

## Milestone 6: Ticketing

Deliverables:

- Ticket creation.
- Private channel permissions.
- Ticket categories.
- Mentor and Officer access.
- Ticket assignment.
- Ticket lifecycle.
- Ticket history and transcripts.

## Milestone 7: Production Deployment

Deliverables:

- Reliable hosting.
- Secure environment configuration.
- Database backups.
- Logging and monitoring.
- Error handling.
- Deployment documentation.
- Maintenance documentation.
- Organizational handover instructions.

---

# 11. Development Practices

Bitwise should be developed using standard software engineering practices.

## 11.1 Version Control

Use Git for all source code.

Recommended workflow:

git switch -c feature/project-assignments

# Implement and test the feature

git add .
git commit -m "Add project assignment functionality"

git switch main
git merge feature/project-assignments

Use feature branches to isolate changes and keep the main branch stable.

## 11.2 Testing

Use pytest to test application logic.

Prioritize testing:

- Authorization checks.
- Role assignment logic.
- Project membership rules.
- Application approval.
- Invalid inputs.
- Discord API failure handling.
- Database integrity.

Keep business logic sufficiently separate from Discord interactions to make it testable without connecting to Discord.

## 11.3 Documentation

Maintain documentation for:

- Installation.
- Environment configuration.
- Database setup.
- Discord application configuration.
- Permission management.
- Deployment.
- Troubleshooting.
- Backup and recovery.
- Adding new projects and roles.

## 11.4 Code Organization

Follow separation of concerns:

- Commands handle Discord interactions.
- Services implement application logic.
- Repositories handle database operations.
- Integrations communicate with external systems.
- Configuration remains separate from business logic.

Avoid placing the entire application inside a single Python file.

---

# 12. Current Design Decisions and Open Questions

## Confirmed Decisions

|                     |                                                                               |
| ------------------- | ----------------------------------------------------------------------------- |
| Decision            | Current Direction                                                             |
| Deployment scope    | One organizational Discord server                                             |
| Membership role     | Freelancer                                                                    |
| Functional roles    | Members can hold multiple                                                     |
| Project assignments | Members may belong to multiple projects                                       |
| Applicant approval  | Officers only                                                                 |
| Project management  | Restricted to assigned projects                                               |
| Database            | PostgreSQL from the start                                                     |
| Main language       | Python                                                                        |
| Discord library     | discord.py                                                                    |
| Website integration | Shared PostgreSQL database; website writes, Bitwise detects via LISTEN/NOTIFY |
| Maintainability     | Modular, configurable, documented                                             |
| Build order         | Recruiting first                                                              |
| Project license     | Open source                                                                   |
| Account linking     | Discord OAuth preferred over username                                         |

## Open Questions

The following decisions still need to be established.

### Organizational Permissions

- What exact actions can Officers perform?
- Are Project Leads and Project Managers equally privileged?
- Can Project Leads assign Project Managers?
- Who can assign or remove functional roles?
- Who can assign Mentors?

### Project Management

- Can a member have multiple project leadership assignments?
- Can Project Leads delegate permissions?
- Should project assignments automatically grant Discord project roles?
- Who creates and archives projects?

### Recruitment

- Can applicants retake assessments?
- Can rejected applicants reapply?
- Should approved applications retain assessment history?
- What onboarding tasks exist beyond the assessment?
- What should a new joiner with limited access be able to see before completing onboarding?

### Ticketing

- Who can view general questions?
- Can mentors see all Community Help tickets or only assigned tickets?
- How long should tickets and transcripts be retained?
- Who can access closed appeals and cases?

### Deployment

- Where will Bitwise be hosted?
- How frequently should the database be backed up?
- Who will maintain deployment credentials?

These questions should be resolved before the corresponding features are implemented.

---

# 13. Guiding Engineering Principles

Bitwise should follow these principles throughout development:

1. \***\*Simplicity over unnecessary complexity:\*\*** Build for one organization rather than prematurely designing a multi-tenant platform.
2. \***\*Separation of concerns:\*\*** Keep Discord interactions, business logic, database access, and external integrations distinct.
3. \***\*Least privilege:\*\*** Grant only the permissions required for each responsibility.
4. \***\*Data integrity:\*\*** Treat the database as the authoritative record for organizational state, with Discord roles synchronized accordingly.
5. \***\*Configurability:\*\*** Make routine organizational changes possible without modifying source code.
6. \***\*Testability:\*\*** Design business logic so it can be tested independently of Discord.
7. \***\*Maintainability:\*\*** Document decisions and implementation details for future maintainers.
8. \***\*Incremental development:\*\*** Implement, test, and review one feature at a time.

---

# 14. Project Vision

Bitwise is intended to become a central internal automation tool for the BITS organization.

Its initial responsibility is to streamline recruitment and organizational role management.

Over time, it can expand into project roster management, ticketing, onboarding, and additional organizational automations.

The long-term objective is not simply to automate Discord commands. It is to establish a reliable, maintainable foundation that makes organization management easier for both current and future members.

\***\*Bitwise should be understandable, configurable, and maintainable without depending on its original developer.\*\***
