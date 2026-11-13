// Development-only copy transformation; resulting source is built normally.
const fs = require('node:fs');
const path = require('node:path');
const ts = require(process.env.HEADPLANE_TS_COMPILER || 'C:/Users/17610/.codex/tmp/headplane-analysis/node_modules/typescript');
const base = path.resolve(__dirname, '..');
const dict = JSON.parse(fs.readFileSync(path.join(base, 'common.zh-CN.json'), 'utf8'));
const dirs = ['components', 'layout', 'routes/auth', 'routes/ssh'];
const files = ['root.tsx', 'utils/toast-provider.tsx', 'utils/host-info.ts', 'utils/acl-policy.ts', 'utils/user.ts'];
function walk(p) {
  for (const ent of fs.readdirSync(p, {withFileTypes: true})) {
    if (ent.isDirectory()) walk(path.join(p, ent.name));
    else if (/\.tsx?$/.test(ent.name)) files.push(path.relative(path.join(base, 'app'), path.join(p, ent.name)));
  }
}
for (const dir of dirs) walk(path.join(base, 'app', dir));
let count = 0;
for (const relative of files) {
  const file = path.join(base, 'app', relative);
  const text = fs.readFileSync(file, 'utf8');
  const ast = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, file.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  const edits = [];
  function visit(node) {
    if (ts.isJsxText(node)) {
      const raw = node.getFullText(ast);
      const normalized = raw.trim().replace(/\s+/g, ' ');
      if (Object.hasOwn(dict, normalized)) {
        const leading = raw.match(/^\s*/)[0], trailing = raw.match(/\s*$/)[0];
        edits.push([node.pos, node.end, leading + dict[normalized] + trailing]);
      }
    } else if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) {
      const parent = node.parent;
      // Never modify keys, imports, type/enum values, or compared program tokens.
      if (ts.isBinaryExpression(parent) || ts.isLiteralTypeNode(parent) || ts.isImportDeclaration(parent) ||
          ts.isElementAccessExpression(parent) || (ts.isPropertyAssignment(parent) && parent.name === node) ||
          (ts.isJsxAttribute(parent) && !['title','label','aria-label','alt','placeholder','description'].includes(parent.name.getText(ast)))) return;
      if (Object.hasOwn(dict, node.text)) {
        let value = JSON.stringify(dict[node.text]);
        if (ts.isJsxAttribute(parent)) value = '"' + dict[node.text].replace(/&/g, '&amp;').replace(/"/g, '&quot;') + '"';
        edits.push([node.getStart(ast), node.end, value]);
      }
    }
    ts.forEachChild(node, visit);
  }
  visit(ast);
  let result = text;
  for (const [start,end,value] of edits.sort((a,b)=>b[0]-a[0])) result = result.slice(0,start)+value+result.slice(end);
  if (result !== text) { fs.writeFileSync(file, result); count += edits.length; }
}
console.log(`Translated ${count} common UI occurrences`);
