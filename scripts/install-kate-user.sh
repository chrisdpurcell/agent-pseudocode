#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE_FILE="$REPO_ROOT/products/kate-integration/agent-pseudocode.xml"
TARGET_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/org.kde.syntax-highlighting/syntax"

mkdir -p "$TARGET_DIR"
cp "$SOURCE_FILE" "$TARGET_DIR/agent-pseudocode.xml"

echo "Installed Agent Pseudocode Kate syntax definition to:"
echo "  $TARGET_DIR/agent-pseudocode.xml"
echo
echo "Restart Kate, then open a .apseudo file. If needed, select:"
echo "  Tools → Highlighting → Scripts → Agent Pseudocode"
