# Agent Pseudocode MCP Server

**Command:** `scripts/apseudo-mcp`  
**Python entry point:** `apseudo-mcp`  
**Transport:** stdio newline-delimited JSON-RPC

## Purpose

The MCP server exposes the same validator, formatter, rule catalog, templates, Mermaid renderer, and project review to AI agents. It is an agent-facing control plane, not the final enforcement boundary. Hooks, pre-commit, and CI remain the hard gates.

## Tools

| Tool | Purpose |
|---|---|
| `validate_text` | Validate raw pseudocode or Markdown text. |
| `validate_file` | Validate one file. |
| `format_text` | Format raw pseudocode or Markdown text. |
| `format_file` | Format one file; writes only when `write=true`. |
| `explain_rule` | Explain an APSEUDO-* diagnostic. |
| `list_rules` | List rule metadata. |
| `generate_template` | Emit a named process template. |
| `render_mermaid` | Render a visualization aid. |
| `review_project` | Review project completeness and diagnostics. |

## Claude Code configuration

The repository includes `.mcp.json`:

```json
{
  "mcpServers": {
    "agent-pseudocode": {
      "type": "stdio",
      "command": "bash",
      "args": [
        "-lc",
        "cd \"${CLAUDE_PROJECT_DIR:-$(pwd)}\" && exec ./scripts/apseudo-mcp"
      ]
    }
  }
}
```

After trusting the workspace, use Claude Code's MCP UI/commands to confirm that `agent-pseudocode` is connected.

## Codex configuration

The repository includes `.codex/config.toml`:

```toml
[mcp_servers.agent_pseudocode]
command = "bash"
args = ["-lc", "cd \"$(git rev-parse --show-toplevel)\" && exec ./scripts/apseudo-mcp"]
startup_timeout_sec = 10
tool_timeout_sec = 60
default_tools_approval_mode = "approve"
enabled = true
```

In Codex CLI, use `/mcp` to verify the server. The server instructions tell Codex to prefer validation tools when editing pseudocode.

## Protocol notes

The server writes only valid JSON-RPC messages to stdout and logs only to stderr. That is required for stdio MCP interoperability.

## Manual smoke test

```bash
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | scripts/apseudo-mcp
```
