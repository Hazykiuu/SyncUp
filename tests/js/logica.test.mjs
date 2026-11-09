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

test('frases de cada faixa (stories 7, 8, 10 e 12)', async () => {
  const L = await import('../../site/app/js/stories/logica.js');
  assert.equal(L.fraseRecorde(13), 'Mais horas de música do que de sono.');
  assert.equal(L.fraseRecorde(11.4), 'Um expediente inteiro de música.');
  assert.equal(L.fraseRecorde(6), 'Dava para ouvir uns 8 álbuns inteiros.');
  assert.equal(L.fraseRecorde(2), 'Um dia intenso, no seu ritmo.');
  assert.equal(L.fraseRepeticao(23), 'Isso não é ouvir, é estudar.');
  assert.equal(L.fraseRepeticao(12), 'Virou a trilha daquele dia.');
  assert.equal(L.fraseRepeticao(3), 'Um dia com trilha sonora definida.');
  assert.equal(L.fraseSequencia(400), 'Um ano inteiro sem um dia de silêncio.');
  assert.equal(L.fraseSequencia(142), '4 meses sem pausa.');
  assert.equal(L.fraseSequencia(45), 'Mais de um mês inteiro, todo dia.');
  assert.equal(L.fraseSequencia(9), 'Uma boa sequência de 9 dias.');
  assert.equal(L.fraseSequencia(3), 'Você ouve no seu ritmo, sem obrigação.');
  assert.equal(L.fraseConstancia(0.95), 'Música é rotina.');
  assert.equal(L.fraseConstancia(0.81), 'Quase todo dia tem trilha.');
  assert.equal(L.fraseConstancia(0.4), 'Você escolhe os momentos.');
  assert.deepEqual(L.habitoDestaque({ pulos: 0.42, aleatorio: 0.61, fim_natural: 0.5, offline: null }), { chave: 'pulos', frase: 'Dedo rápido: 42% das faixas puladas.' });
  assert.equal(L.habitoDestaque({ pulos: 0.1, aleatorio: 0.3, fim_natural: 0.5, offline: 0 }).chave, null);
  assert.equal(L.habitoDestaque({}).frase, 'Equilíbrio: nem pula demais, nem deixa tudo no aleatório.');
  assert.deepEqual(L.descobertasCurta(0.1), { n: 10, frase: 'Você vive caçando som novo.' });
  assert.equal(L.descobertasCurta(0.02).frase, 'Você sabe do que gosta.');
});

test('slides condicionais', async () => {
  const { tiposDoWrapped } = await import('../../site/app/js/stories/logica.js');
  const base = { anos: [{}, {}], quantidade_artistas: 300, habitos: { pulos: 0.2 } };
  assert.equal(tiposDoWrapped(base).length, 14);
  const umAno = tiposDoWrapped({ ...base, anos: [{}] });
  assert.ok(!umAno.includes('anos') && umAno.includes('descobertas'));
  assert.ok(!tiposDoWrapped({ ...base, quantidade_artistas: 5 }).includes('descobertas'));
  assert.ok(!tiposDoWrapped({ ...base, habitos: { pulos: null, offline: null } }).includes('habitos'));
});
