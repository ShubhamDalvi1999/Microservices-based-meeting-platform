# Contributing to the Meeting Scheduler App

Thank you for your interest in contributing to the Meeting Scheduler App! This document provides guidelines for developers looking to contribute to the project.

## 1. Getting Started

### 1.1. Prerequisites

*   Ensure you have Git, Docker, and Docker Compose installed. Refer to the [Deployment Guide](./docs/DEPLOYMENT_GUIDE.md) for setup.
*   Familiarize yourself with the [System Architecture Overview](./docs/SYSTEM_ARCHITECTURE.md).

### 1.2. Setting up the Development Environment

1.  Clone the repository: `git clone <repository_url>`
2.  Navigate to the `backend` directory: `cd <repository_name>/backend`
3.  (Optional but Recommended) Create a `.env` file in the `backend` directory. See the [Deployment Guide](./docs/DEPLOYMENT_GUIDE.md#22-environment-configuration-optional-but-recommended) for an example.
4.  Build and start all services: `docker-compose up --build`

## 2. Development Workflow

### 2.1. Branching Strategy (Example: Gitflow variant)

*   `main` (or `master`): Represents the production-ready state. Merges typically come from `develop` via release branches.
*   `develop`: Main development branch. All feature branches are merged into `develop`.
*   `feature/<feature-name>`: Create a new branch from `develop` for each new feature or bugfix (e.g., `feature/P5-guest-login-proxy`).
*   `release/<version>` (Optional): For preparing a new production release. Branched from `develop`.
*   `hotfix/<issue>` (Optional): For critical bug fixes in production. Branched from `main`.

### 2.2. Making Changes

1.  Ensure your `develop` branch is up-to-date: `git checkout develop && git pull origin develop`.
2.  Create a new feature branch: `git checkout -b feature/your-feature-name`.
3.  Make your code changes. Adhere to coding standards (see below).
4.  Write or update tests for your changes.
5.  Ensure all tests pass locally.
6.  Commit your changes with clear, descriptive messages. (See Commit Message Conventions).

### 2.3. Submitting Pull Requests (PRs)

1.  Push your feature branch to the remote repository: `git push origin feature/your-feature-name`.
2.  Open a Pull Request (PR) from your feature branch to the `develop` branch on the Git hosting platform (e.g., GitHub, GitLab).
3.  Provide a clear title and description for your PR, explaining the changes and referencing any relevant issues (e.g., from `PROJECT_BACKLOG.md`).
4.  Ensure any CI checks (linters, tests) pass for your PR.
5.  Engage in code review if applicable. Address feedback by pushing new commits to your feature branch.
6.  Once approved and checks pass, the PR will be merged into `develop`.

## 3. Coding Standards

*   **Python (Backend):**
    *   Follow PEP 8 style guidelines.
    *   Use a linter like Flake8 and a formatter like Black (configurations to be added).
    *   Write clear, maintainable code with appropriate comments for complex logic.
*   **JavaScript/React (Frontend):**
    *   Follow standard React best practices and the style guide enforced by ESLint (from Create React App).
    *   Use Prettier for code formatting (configuration to be added).
    *   Aim for functional components with Hooks where possible.
*   **General:**
    *   Keep code DRY (Don't Repeat Yourself).
    *   Write meaningful variable and function names.
    *   Ensure documentation (e.g., service READMEs, ADRs if making architectural changes) is updated if your changes affect it.

## 4. Commit Message Conventions (Example: Conventional Commits)

Using a convention helps in generating changelogs and understanding commit history.

Format: `<type>(<scope>): <subject>`

*   **Types:** `feat` (new feature), `fix` (bug fix), `docs` (documentation), `style` (formatting, linting), `refactor`, `test`, `chore` (build changes, etc.).
*   **Scope (Optional):** Module or part of the codebase affected (e.g., `auth-service`, `frontend-login`).
*   **Subject:** Concise description of the change, imperative mood (e.g., "Add guest login endpoint").

Example: `feat(auth-service): Add guest login endpoint`

## 5. Testing

*   **Backend:**
    *   Unit tests (e.g., using `pytest`) should cover individual functions and classes.
    *   Integration tests (planned) to test interactions between components within a service or between services.
*   **Frontend:**
    *   Component tests (e.g., using React Testing Library with Jest) should cover individual React components.
    *   End-to-end tests (planned, e.g., using Cypress or Playwright) to test user flows.

All new features and bug fixes should ideally be accompanied by tests. Run tests locally before submitting PRs.
(Specific test running commands to be added as testing infrastructure is built).

## 6. Documentation

*   If your changes impact system architecture, consider if an ADR is needed or if existing architecture documents need updates.
*   Update service-specific READMEs if API endpoints, configuration, or setup instructions change.
*   Comment your code where necessary.

## 7. Issue Tracking

*   Refer to `PROJECT_BACKLOG.md` for a list of features, tasks, and bugs.
*   If using a formal issue tracker (Jira, GitHub Issues), reference issue numbers in commits and PRs.

By following these guidelines, we can maintain a clean, understandable, and collaborative development process. 