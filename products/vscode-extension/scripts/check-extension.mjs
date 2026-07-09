#!/usr/bin/env node
import { readFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';

const here = path.dirname(new URL(import.meta.url).pathname);
const extensionRoot = path.resolve(here, '..');

function requireFile(relativePath) {
  const fullPath = path.join(extensionRoot, relativePath);
  if (!existsSync(fullPath)) {
    throw new Error(`Missing required file: ${relativePath}`);
  }
  return fullPath;
}

const packageJson = JSON.parse(await readFile(requireFile('package.json'), 'utf8'));

if (packageJson.main) {
  requireFile(packageJson.main);
}


for (const language of packageJson.contributes.languages ?? []) {
  if (language.configuration) {
    requireFile(language.configuration);
  }
}

for (const grammar of packageJson.contributes.grammars ?? []) {
  const grammarPath = requireFile(grammar.path);
  JSON.parse(await readFile(grammarPath, 'utf8'));
}

for (const snippet of packageJson.contributes.snippets ?? []) {
  const snippetPath = requireFile(snippet.path);
  JSON.parse(await readFile(snippetPath, 'utf8'));
}

console.log('Extension manifest, grammar JSON, and snippets are present and parseable.');
