"""Domain errors for invalid repository explainer production manifests."""

from __future__ import annotations


class ManifestError(ValueError):
    """Raised when a project manifest cannot safely drive a deterministic render."""
