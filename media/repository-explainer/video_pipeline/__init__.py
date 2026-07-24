"""Validated local production configuration for the repository explainer film."""

from .manifest import ManifestError, load_project
from .models import ProjectManifest

__all__ = ["ManifestError", "ProjectManifest", "load_project"]
