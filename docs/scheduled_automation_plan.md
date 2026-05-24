# Scheduled Automation Plan

## Purpose

This document describes future options for recurring Colombia data maintenance. No scheduler is currently active. The recommended operating model remains manual controlled updates until IT/Data support is in place.

## Option A - Manual Controlled Update

Current recommended approach.

Pros:

- Lowest operational risk.
- Keeps database promotion under human review.
- Works with the current local and Streamlit Cloud setup.
- Avoids storing credentials or secrets.

Cons:

- Requires a person to run the process.
- Update frequency depends on team discipline.
- Not ideal for long-term production.

Requirements:

- Local Python environment.
- Access to the project repository.
- Ability to run the maintenance runbook.

Risks:

- Manual steps may be skipped if the checklist is not followed.

Recommendation:

- Use this approach for the next internal demo cycles and monthly controlled updates.

## Option B - Local Windows Task Scheduler

Future possible option.

Pros:

- Simple to configure on a controlled Windows machine.
- Can run commands at a fixed cadence.

Cons:

- Depends on one machine being available.
- Harder to monitor centrally.
- Credentials and network access must be managed carefully.

Requirements:

- Stable local machine or internal workstation.
- Service account or user account policy review.
- Logging and alerting plan.

Risks:

- Missed runs if the machine is off.
- Local environment drift.

Recommendation:

- Acceptable only as an interim internal automation after IT review.

## Option C - Internal Server Or VM

Better corporate option.

Pros:

- More reliable than a personal machine.
- Easier to monitor, secure, and document.
- Better handoff path for IT/Data.

Cons:

- Requires infrastructure support.
- Requires deployment, access, backup, and monitoring decisions.

Requirements:

- Internal server or VM.
- Approved Python runtime.
- Network access to public Fasecolda sources.
- Repository access.
- Operational owner.

Risks:

- Needs formal ownership and support.

Recommendation:

- Preferred next step once the MVP is accepted for broader internal use.

## Option D - GitHub Actions

Possible for code checks and selected maintenance tasks.

Pros:

- Good for automated linting, compile checks, and release checks.
- Easy to connect to pull requests.

Cons:

- Data downloads, generated files, and database commits need strict governance.
- Public source downloads can be brittle.
- Secrets and repository storage policies must be handled carefully.

Requirements:

- GitHub Actions enabled for the private repository.
- Clear workflow permissions.
- Rules that prevent raw files, metadata, backups, and candidate databases from being committed accidentally.

Risks:

- Accidental data artifact commits if workflow permissions are too broad.
- Provider limits or site changes can break unattended downloads.

Recommendation:

- Use for code quality checks first. Treat data refresh automation as a later governed step.

## Option E - Cloud Job Or Managed Scheduler

Future robust option.

Pros:

- Best path for reliable scheduled operations.
- Can include monitoring, alerts, retries, and logs.
- Better production-readiness path.

Cons:

- Requires corporate cloud design.
- Requires secrets management and environment governance.
- Requires ownership by IT/Data or platform team.

Requirements:

- Approved cloud environment.
- Secrets management.
- Logging and monitoring.
- Deployment model for candidate and promoted databases.

Risks:

- Over-building before data methodology and ownership are finalized.

Recommendation:

- Target this only after internal users validate the MVP and IT/Data defines the production hosting approach.

## Recommended Path

For now:

1. Keep manual controlled updates.
2. Use `docs/maintenance_runbook.md` for each data refresh.
3. Use `docs/release_checklist.md` before every push/reboot.
4. Discuss internal server or managed scheduler options with IT/Data before enabling unattended automation.

