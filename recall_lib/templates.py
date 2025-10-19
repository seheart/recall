#!/usr/bin/env python3
"""
Project Templates - Pre-configured templates for common project types
"""
from typing import Dict, List
from .logger import get_logger

logger = get_logger(__name__)


# Template definitions
TEMPLATES = {
    "web-app": {
        "name": "Web Application",
        "description": "Full-stack web application with frontend and backend",
        "tags": ["web", "fullstack"],
        "architecture": {
            "type": "Full-stack Web Application",
            "frontend": "React/Vue/Svelte (choose one)",
            "backend": "Node.js/Python/Go (choose one)",
            "database": "PostgreSQL/MongoDB (choose one)",
            "deployment": "Docker + Cloud Platform"
        },
        "state": {
            "status": "Planning",
            "phase": "Architecture Design"
        },
        "decisions": {
            "authentication": "To be decided - consider JWT or session-based",
            "api_style": "RESTful API recommended"
        },
        "documentation": {
            "api_docs": "Document endpoints in /docs/api.md",
            "setup_guide": "Create SETUP.md for development environment"
        }
    },

    "api-server": {
        "name": "API Server",
        "description": "RESTful or GraphQL API server",
        "tags": ["api", "backend"],
        "architecture": {
            "type": "API Server",
            "language": "Node.js/Python/Go (choose one)",
            "framework": "Express/FastAPI/Gin (choose one)",
            "database": "PostgreSQL recommended for relational data",
            "authentication": "JWT tokens recommended",
            "api_style": "REST or GraphQL"
        },
        "state": {
            "status": "Planning",
            "current_feature": "API design and schema definition"
        },
        "decisions": {
            "validation": "Use schema validation (Joi, Pydantic, etc.)",
            "error_handling": "Implement centralized error handling middleware"
        }
    },

    "cli-tool": {
        "name": "CLI Tool",
        "description": "Command-line interface application",
        "tags": ["cli", "tool"],
        "architecture": {
            "type": "CLI Application",
            "language": "Python/Go/Rust (choose one)",
            "framework": "Click/Cobra/Clap (choose one)",
            "packaging": "pip/cargo/go install",
            "config": "YAML or TOML configuration file"
        },
        "state": {
            "status": "Planning",
            "current_feature": "Command structure and help text"
        },
        "decisions": {
            "argument_parsing": "Use a well-established CLI framework",
            "output_format": "Support both human-readable and JSON output"
        }
    },

    "data-science": {
        "name": "Data Science Project",
        "description": "Data analysis, ML/AI project with Jupyter notebooks",
        "tags": ["data-science", "ml", "python"],
        "architecture": {
            "type": "Data Science Project",
            "language": "Python",
            "framework": "Pandas, NumPy, Scikit-learn, TensorFlow/PyTorch",
            "environment": "Jupyter Lab or VS Code with notebooks",
            "data_storage": "CSV, Parquet, or database",
            "visualization": "Matplotlib, Seaborn, Plotly"
        },
        "state": {
            "status": "Data Exploration",
            "phase": "Understanding the dataset"
        },
        "decisions": {
            "notebook_structure": "Separate notebooks for EDA, modeling, evaluation",
            "reproducibility": "Use requirements.txt and random seeds"
        }
    },

    "mobile-app": {
        "name": "Mobile Application",
        "description": "iOS/Android mobile application",
        "tags": ["mobile", "app"],
        "architecture": {
            "type": "Mobile Application",
            "framework": "React Native/Flutter/Native (choose one)",
            "backend": "Firebase or custom API",
            "state_management": "Redux/MobX/Provider (choose one)",
            "platform": "iOS and/or Android"
        },
        "state": {
            "status": "Planning",
            "current_feature": "UI/UX mockups and navigation structure"
        },
        "decisions": {
            "navigation": "Choose navigation pattern (tabs, stack, drawer)",
            "offline_support": "Consider offline-first architecture"
        }
    },

    "library": {
        "name": "Library/Package",
        "description": "Reusable library or package for distribution",
        "tags": ["library", "package"],
        "architecture": {
            "type": "Library/Package",
            "language": "Python/JavaScript/Go/Rust (choose one)",
            "packaging": "npm/PyPI/crates.io/Go modules",
            "documentation": "README + API docs + examples",
            "testing": "Unit tests + integration tests"
        },
        "state": {
            "status": "Development",
            "phase": "Core API design"
        },
        "decisions": {
            "api_design": "Keep API simple and intuitive",
            "versioning": "Follow semantic versioning (semver)",
            "dependencies": "Minimize external dependencies"
        }
    },

    "microservice": {
        "name": "Microservice",
        "description": "Containerized microservice component",
        "tags": ["microservice", "backend", "docker"],
        "architecture": {
            "type": "Microservice",
            "language": "Node.js/Python/Go (choose one)",
            "containerization": "Docker + Docker Compose",
            "orchestration": "Kubernetes (optional)",
            "communication": "REST, gRPC, or message queue",
            "database": "Dedicated database per service principle"
        },
        "state": {
            "status": "Planning",
            "phase": "Service boundaries definition"
        },
        "decisions": {
            "service_discovery": "Consider Consul or Kubernetes DNS",
            "monitoring": "Implement health checks and metrics endpoints",
            "logging": "Structured logging with correlation IDs"
        }
    },

    "static-site": {
        "name": "Static Website",
        "description": "Static website or documentation site",
        "tags": ["web", "static", "documentation"],
        "architecture": {
            "type": "Static Website",
            "generator": "Hugo/Jekyll/Next.js/Gatsby (choose one)",
            "hosting": "GitHub Pages/Netlify/Vercel",
            "styling": "Tailwind CSS or custom CSS",
            "content": "Markdown-based content"
        },
        "state": {
            "status": "Setup",
            "phase": "Site structure and theme selection"
        },
        "decisions": {
            "seo": "Implement proper meta tags and sitemap",
            "analytics": "Consider privacy-friendly analytics"
        }
    }
}


def get_template(template_name: str) -> Dict:
    """
    Get a template by name

    Args:
        template_name: Name of the template

    Returns:
        Template dictionary or None if not found
    """
    return TEMPLATES.get(template_name.lower())


def list_templates() -> List[Dict]:
    """
    List all available templates

    Returns:
        List of template info dicts
    """
    return [
        {
            "id": key,
            "name": template["name"],
            "description": template["description"],
            "tags": template["tags"]
        }
        for key, template in TEMPLATES.items()
    ]


def apply_template(project_memory, project_name: str, template_name: str) -> bool:
    """
    Apply a template to a project

    Args:
        project_memory: ProjectMemory instance
        project_name: Name of the project
        template_name: Name of the template to apply

    Returns:
        True if successful, False otherwise
    """
    template = get_template(template_name)
    if not template:
        logger.error(f"❌ Template '{template_name}' not found")
        return False

    # Apply architecture
    if "architecture" in template:
        project_memory.update_architecture(project_name, template["architecture"])

    # Apply state
    if "state" in template:
        project_memory.update_state(project_name, template["state"])

    # Apply decisions
    if "decisions" in template:
        for key, value in template["decisions"].items():
            project_memory.record_decision(project_name, key, value)

    # Apply documentation links (as context)
    if "documentation" in template:
        project = project_memory.db.get_project(project_name)
        if project:
            for key, value in template["documentation"].items():
                project_memory.db.set_context(project['id'], "documentation", key, value)

    # Apply tags
    if "tags" in template:
        for tag in template["tags"]:
            project_memory.add_tag(project_name, tag)

    logger.info(f"✅ Applied '{template['name']}' template to '{project_name}'")
    return True
