# Recall Project Templates

This directory contains YAML-based project templates for quick project initialization.

## Overview

Recall supports two types of templates:
1. **Built-in hard-coded templates** - 8 common project types defined in `recall_lib/templates.py`
2. **External YAML templates** - Custom templates defined in YAML files (this directory or `~/.config/recall/templates/`)

## Using Templates

```bash
# List all available templates
recall --list-templates

# Create project from template
recall my-project --create --template fastapi-backend

# Create with interactive setup
recall my-project --create
# Then answer template questions
```

## Creating Custom Templates

### Template File Structure

Create a YAML file in this directory (or `~/.config/recall/templates/`):

```yaml
# filename: my-template.yaml
name: "My Custom Template"
description: "Short description of what this template provides"
author: "Your Name"
version: "1.0.0"
tags:
  - tag1
  - tag2

architecture:
  type: "Project Type"
  language: "Programming Language"
  framework: "Framework Name"
  # ... any other architecture details

state:
  status: "Planning"
  phase: "Initial phase"
  current_feature: "What you're working on"

decisions:
  decision_key_1: "Important decision or guideline"
  decision_key_2: "Another architectural decision"

documentation:
  setup_guide: "Path to or description of setup docs"
  api_docs: "Path to or description of API documentation"
```

### Required Fields

- `name`: Human-readable template name
- `description`: Short description shown in template list

### Optional Fields

- `author`: Template author
- `version`: Template version (semver)
- `tags`: List of tags for categorization
- `architecture`: Architecture and tech stack details
- `state`: Initial project state
- `decisions`: Key architectural decisions
- `documentation`: Documentation guidelines

### How It Works

When you create a project with a template:

1. Recall loads the template YAML
2. Creates the project in the database
3. Populates initial context with template data:
   - Architecture → `architecture` context category
   - State → `state` context category
   - Decisions → `decisions` context category
   - Documentation → `documentation` context category
4. Adds template tags to the project

## Built-in Hard-coded Templates

These are always available:

1. **web-app** - Full-stack web application
2. **api-server** - REST or GraphQL API server
3. **cli-tool** - Command-line interface application
4. **data-science** - Data analysis/ML project
5. **mobile-app** - iOS/Android application
6. **library** - Reusable library or package
7. **microservice** - Containerized microservice
8. **static-site** - Static website or docs site

## Example: FastAPI Backend Template

See `fastapi-backend.yaml` for a complete example template.

```yaml
name: "FastAPI Backend"
description: "Modern Python REST API server with FastAPI"
tags: [api, backend, python, fastapi]

architecture:
  language: "Python 3.11+"
  framework: "FastAPI"
  database: "PostgreSQL with SQLAlchemy"

decisions:
  validation: "Use Pydantic models for request/response validation"
  error_handling: "Centralized exception handlers"
```

## Template Discovery Order

Recall searches for templates in this order:

1. Hard-coded templates in `recall_lib/templates.py`
2. YAML templates in `/path/to/recall/templates/` (this directory)
3. YAML templates in `~/.config/recall/templates/` (user templates)

If a YAML template has the same ID (filename) as a hard-coded template, the YAML version takes precedence.

## Best Practices

1. **Use descriptive names** - Make it clear what the template is for
2. **Add relevant tags** - Helps users find templates
3. **Be specific** - Provide concrete recommendations, not vague guidance
4. **Document decisions** - Capture "why" not just "what"
5. **Keep it focused** - Each template should represent one specific project type
6. **Version your templates** - Use semantic versioning for template changes

## Template Ideas

Some ideas for custom templates:

- **nextjs-app** - Next.js React application
- **django-api** - Django REST Framework API
- **rust-cli** - Rust command-line tool
- **svelte-spa** - Svelte single-page application
- **go-microservice** - Go-based microservice
- **electron-app** - Electron desktop application
- **gatsby-blog** - Gatsby blog/content site
- **flask-api** - Flask REST API
- **vue-pwa** - Vue.js progressive web app

## Sharing Templates

To share your templates with others:

1. Create a GitHub repository with your template YAML files
2. Users can clone/download templates to their `~/.config/recall/templates/` directory
3. Consider creating a collection of related templates (e.g., "JavaScript Frameworks", "Python Backends")

## Contributing

To contribute templates to Recall:

1. Create a well-documented YAML template
2. Test it with real project creation
3. Submit a pull request to the Recall repository
4. Include example usage in your PR description

## Support

- Documentation: https://docs.recall.dev/templates
- Issues: https://github.com/anthropics/recall/issues
- Examples: https://github.com/anthropics/recall-templates
