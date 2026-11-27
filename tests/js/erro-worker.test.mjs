// A mensagem que os Workers mandam para a tela quando algo falha. Rodar: node --test tests/js
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

import { mensagemDeErro } from '../../site/app/js/worker.js';

test('erro previsto pelo app: só a mensagem em português', () => {
  assert.equal(mensagemDeErro(new Error('O ZIP está inválido.')), 'O ZIP está inválido.');
});

test('erro inesperado: texto genérico com o erro original, para uma captura de tela bastar', () => {
  const m = mensagemDeErro(new TypeError("Cannot read properties of undefined (reading 'map')"));
  assert.match(m, /^Algo deu errado ao processar os arquivos\./);
  assert.ok(m.endsWith("Detalhe técnico: TypeError: Cannot read properties of undefined (reading 'map')"), m);
});

test('erro inesperado sem nome ou com texto enorme', () => {
  assert.ok(mensagemDeErro(undefined).endsWith('Detalhe técnico: undefined'));
  assert.ok(mensagemDeErro(new RangeError('x'.repeat(5000))).length < 400);
});

test('os 4 Workers de cálculo usam a mesma mensagem e deixam o erro no console', () => {
  for (const nome of ['dupla', 'wrapped', 'match', 'batalha']) {
    const s = readFileSync(new URL(`../../site/app/${nome}-worker.js`, import.meta.url), 'utf8');
    assert.match(s, /console\.error\(e\);\s*\n\s*self\.postMessage\(\{ ok: false, erro: mensagemDeErro\(e\) \}\);/, nome);
  }
});
