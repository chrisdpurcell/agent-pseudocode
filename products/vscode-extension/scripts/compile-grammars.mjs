#!/usr/bin/env node
import { readdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import yaml from 'js-yaml';

const here = path.dirname(new URL(import.meta.url).pathname);
const extensionRoot = path.resolve(here, '..');
const syntaxDir = path.join(extensionRoot, 'syntaxes');

let converted = 0;

for (const entry of await readdir(syntaxDir)) {
  if (!entry.endsWith('.tmLanguage.yaml')) {
    continue;
  }

  const yamlPath = path.join(syntaxDir, entry);
  const jsonPath = path.join(syntaxDir, entry.replace(/\.yaml$/, '.json'));
  const raw = await readFile(yamlPath, 'utf8');
  const parsed = yaml.load(raw, { filename: yamlPath });

  await writeFile(jsonPath, `${JSON.stringify(parsed, null, 2)}\n`, 'utf8');
  console.log(`compiled ${path.relative(extensionRoot, yamlPath)} -> ${path.relative(extensionRoot, jsonPath)}`);
  converted += 1;
}

if (converted === 0) {
  console.warn('No .tmLanguage.yaml files found.');
}
