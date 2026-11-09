// Lógica pura dos stories do Wrapped. Rodar: node --test tests/js
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { ajustarCor, dataBr, fmtNum, fmtPct, hashNome, inicial, mesAno, pausado, player } from '../../site/app/js/stories/logica.js';

test('avança, volta e para no fim', () => {
  let e = inicial(3);
  e = player(e, { tipo: 'TEMPO' });
  assert.equal(e.i, 1);
  e = player(e, { tipo: 'AVANCAR' });
  e = player(e, { tipo: 'AVANCAR' });
  assert.equal(e.i, 2);
  assert.ok(e.fim && pausado(e));
  e = player(e, { tipo: 'VOLTAR' });
  assert.equal(e.i, 1);
  assert.ok(!e.fim);
  e = player(player(e, { tipo: 'VOLTAR' }), { tipo: 'VOLTAR' });
  assert.equal(e.i, 0);
  assert.equal(player(e, { tipo: 'IR', i: 99 }).i, 2);
});

test('soltar o dedo não retoma a pausa feita de propósito', () => {
  let e = inicial(5);
  e = player(e, { tipo: 'PAUSAR', motivo: 'usuario' });
  e = player(e, { tipo: 'PAUSAR', motivo: 'segurar' });
  e = player(e, { tipo: 'RETOMAR', motivo: 'segurar' });
  assert.ok(pausado(e));
  e = player(e, { tipo: 'RETOMAR', motivo: 'usuario' });
  assert.ok(!pausado(e));
  assert.deepEqual(player(player(e, { tipo: 'PAUSAR', motivo: 'oculta' }), { tipo: 'PAUSAR', motivo: 'oculta' }).motivos, ['oculta']);
});

test('menos movimento começa pausado; replay volta ao início tocando', () => {
  let e = inicial(4, { semMovimento: true });
  assert.ok(pausado(e));
  e = player(player(e, { tipo: 'IR', i: 3 }), { tipo: 'AVANCAR' });
  e = player(e, { tipo: 'REPLAY' });
  assert.equal(e.i, 0);
  assert.ok(!pausado(e));
  assert.equal(player(inicial(2), { tipo: 'ALTERNAR' }).motivos[0], 'usuario');
});

test('formatação igual à do Python (pt-BR)', () => {
  assert.equal(fmtNum(1764.4), '1.764');
  assert.equal(fmtNum(73.56, 1), '73,6');
  assert.equal(fmtPct(0.183), '18%');
  assert.equal(mesAno('2019-12-31T21:00:36'), 'dez/2019');
  assert.equal(dataBr('2021-02-03T10:00:00'), '03/02/2021');
});

test('cor da capa sempre utilizável', () => {
  for (const [r, g, b] of [[0, 0, 0], [255, 255, 255], [128, 128, 128], [250, 20, 20]]) {
    const [r2, g2, b2] = ajustarCor(r, g, b);
    const l = (Math.max(r2, g2, b2) + Math.min(r2, g2, b2)) / 2 / 255;
    assert.ok(l >= 0.34 && l <= 0.61, `luminosidade ${l} para ${[r, g, b]}`);
  }
  assert.equal(hashNome('Legião'), hashNome('Legião'));
  assert.notEqual(hashNome('A'), hashNome('B'));
});
