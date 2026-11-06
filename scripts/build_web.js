/**
 * Deterministic React 18 Transpiler for MAS Cockpit Web.
 * Uses vendored Babel standalone to compile app.jsx -> app.js with classic React runtime.
 * Guarantees zero 'import' or 'export' statements so browser script tags load with 100% resilience.
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const rootDir = path.resolve(__dirname, '..');
const babelPath = path.join(rootDir, 'mas', 'web', 'vendor', 'babel.min.js');
const jsxPath = path.join(rootDir, 'mas', 'web', 'app.jsx');
const jsPath = path.join(rootDir, 'mas', 'web', 'app.js');

console.log('Loading vendored Babel standalone...');
const babelSrc = fs.readFileSync(babelPath, 'utf8');
const ctx = { console, process, window: {}, exports: {} };
vm.createContext(ctx);
vm.runInContext(babelSrc, ctx);

const Babel = ctx.Babel || ctx.window.Babel;
if (!Babel) {
  console.error('Babel failed to initialize.');
  process.exit(1);
}

console.log('Reading app.jsx (' + fs.statSync(jsxPath).size + ' bytes)...');
const jsxCode = fs.readFileSync(jsxPath, 'utf8');

console.log('Transpiling with React classic runtime (React.createElement)...');
const result = Babel.transform(jsxCode, {
  presets: [['react', { runtime: 'classic' }]]
});

// Guardrail verification: ensure no unbundled import / export statements exist
const lines = result.code.split('\n');
const offendingLines = lines.filter(l => l.startsWith('import ') || l.startsWith('export '));
if (offendingLines.length > 0) {
  console.error('Fatal: Transpiled code contains module import/export statements:', offendingLines);
  process.exit(1);
}

fs.writeFileSync(jsPath, result.code, 'utf8');
console.log('Successfully wrote mas/web/app.js (' + result.code.length + ' bytes). 0 module imports.');

