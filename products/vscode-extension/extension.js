'use strict';

const fs = require('node:fs');
const path = require('node:path');
const childProcess = require('node:child_process');
const vscode = require('vscode');
const { LanguageClient } = require('vscode-languageclient/node');

let client;

async function activate(context) {
  context.subscriptions.push(
    vscode.commands.registerCommand('agentPseudocode.restartLanguageServer', async () => {
      await stopClient();
      await startClient(context);
      vscode.window.showInformationMessage('Agent Pseudocode language server restarted.');
    }),
    vscode.commands.registerCommand('agentPseudocode.showLanguageServerOutput', () => {
      if (client && client.outputChannel) {
        client.outputChannel.show(true);
      }
    }),
    vscode.commands.registerCommand('agentPseudocode.formatDocument', async () => {
      await vscode.commands.executeCommand('editor.action.formatDocument');
    }),
    vscode.commands.registerCommand('agentPseudocode.explainRule', async (ruleCode) => {
      await explainRule(context, ruleCode);
    }),
    vscode.commands.registerCommand('agentPseudocode.reviewProject', async () => {
      await runProjectReview(context);
    })
  );

  await startClient(context);
}

async function deactivate() {
  await stopClient();
}

async function startClient(context) {
  if (client) {
    return;
  }

  const serverOptions = resolveServerOptions(context);
  const config = vscode.workspace.getConfiguration('agentPseudocode');
  const documentSelector = [
    { scheme: 'file', language: 'agent-pseudocode' },
    { scheme: 'untitled', language: 'agent-pseudocode' }
  ];
  if (config.get('server.enableMarkdown', true)) {
    documentSelector.push(
      { scheme: 'file', language: 'markdown' },
      { scheme: 'untitled', language: 'markdown' }
    );
  }
  const clientOptions = {
    documentSelector,
    synchronize: {
      configurationSection: 'agentPseudocode',
      fileEvents: vscode.workspace.createFileSystemWatcher('**/{.apseudo-lint.toml,apseudo.toml,pyproject.toml}')
    }
  };

  client = new LanguageClient(
    'agentPseudocode',
    'Agent Pseudocode Language Server',
    serverOptions,
    clientOptions
  );
  context.subscriptions.push(client);
  await client.start();
}

async function stopClient() {
  if (!client) {
    return;
  }
  const oldClient = client;
  client = undefined;
  await oldClient.stop();
}

function resolveServerOptions(context) {
  const config = vscode.workspace.getConfiguration('agentPseudocode');
  const trace = Boolean(config.get('server.trace', false));
  const workspaceRoot = getWorkspaceRoot();
  const configuredCommand = config.get('server.command', '');
  const configuredArgs = config.get('server.args', []);
  const cwd = config.get('server.cwd', '') || workspaceRoot || context.extensionPath;

  let command;
  let args;

  if (configuredCommand) {
    command = configuredCommand;
    args = Array.isArray(configuredArgs) ? configuredArgs.slice() : [];
  } else {
    const sourceTreeScript = findSourceTreeServerScript(context, workspaceRoot);
    if (sourceTreeScript) {
      command = sourceTreeScript;
      args = [];
    } else if (workspaceRoot && fs.existsSync(path.join(workspaceRoot, 'pyproject.toml'))) {
      command = 'uv';
      args = ['run', 'apseudo-lsp'];
    } else {
      command = 'apseudo-lsp';
      args = [];
    }
  }

  const runArgs = trace && !args.includes('--trace') ? [...args, '--trace'] : args;
  const options = { cwd, env: process.env };

  return {
    run: { command, args: runArgs, options },
    debug: { command, args: runArgs.includes('--trace') ? runArgs : [...runArgs, '--trace'], options }
  };
}

function findSourceTreeServerScript(context, workspaceRoot) {
  return findSourceTreeScript(context, workspaceRoot, 'apseudo-lsp');
}

function findSourceTreeScript(context, workspaceRoot, name) {
  const candidates = [];
  if (workspaceRoot) {
    candidates.push(path.join(workspaceRoot, 'scripts', platformScriptName(name)));
  }
  candidates.push(path.resolve(context.extensionPath, '..', 'scripts', platformScriptName(name)));

  for (const candidate of candidates) {
    if (candidate && fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return undefined;
}

async function explainRule(context, ruleCode) {
  const code = typeof ruleCode === 'string' && ruleCode ? ruleCode : await vscode.window.showInputBox({
    title: 'Explain APSEUDO rule',
    prompt: 'Enter a rule code, for example APSEUDO-WHILE-001'
  });
  if (!code) {
    return;
  }
  await runToolAndShowMarkdown(context, 'apseudo-explain', [code], `Agent Pseudocode: ${code}`);
}

async function runProjectReview(context) {
  await runToolAndShowMarkdown(context, 'apseudo-review', [], 'Agent Pseudocode Project Review');
}

async function runToolAndShowMarkdown(context, toolName, args, title) {
  const workspaceRoot = getWorkspaceRoot();
  const script = findSourceTreeScript(context, workspaceRoot, toolName);
  const command = script || toolName;
  const cwd = workspaceRoot || context.extensionPath;
  childProcess.execFile(command, args, { cwd }, async (error, stdout, stderr) => {
    const body = stdout || stderr || (error ? String(error) : 'No output.');
    const document = await vscode.workspace.openTextDocument({ content: body, language: 'markdown' });
    await vscode.window.showTextDocument(document, { preview: true });
    if (error) {
      vscode.window.showWarningMessage(`${title} exited with status ${error.code || 1}.`);
    }
  });
}

function platformScriptName(name) {
  return process.platform === 'win32' ? `${name}.cmd` : name;
}

function getWorkspaceRoot() {
  const folders = vscode.workspace.workspaceFolders;
  if (!folders || folders.length === 0) {
    return undefined;
  }
  return folders[0].uri.fsPath;
}

module.exports = { activate, deactivate };
