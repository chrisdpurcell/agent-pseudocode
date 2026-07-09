#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT/products/vscode-extension"

npm install
npm run package

if command -v code >/dev/null 2>&1; then
  code --install-extension agent-pseudocode-0.6.1.vsix --force
elif command -v codium >/dev/null 2>&1; then
  codium --install-extension agent-pseudocode-0.6.1.vsix --force
else
  echo "No 'code' or 'codium' command found. Install manually from:"
  echo "  $REPO_ROOT/products/vscode-extension/agent-pseudocode-0.6.1.vsix"
  exit 1
fi
