import assert from 'node:assert/strict';
import test from 'node:test';
import { deflateSync } from 'node:zlib';

import { gerarConvite, lerConvite, PREFIXO, separarConvites } from '../../site/app/js/convite.js';

const perfil = {
  nome: '  Ana 🎸  ',
  top_artistas: { short_term: ['Zé', 'Ａ Banda'], medium_term: [], long_term: ['Lia'] },
  top_musicas: { short_term: [{ musica: 'Ação & "aspas"', artista: 'Zé' }], medium_term: [], long_term: [] },
};
const codigo = (obj) => PREFIXO + deflateSync(Buffer.from(JSON.stringify(obj))).toString('base64url');

test('convite: ida e volta mantém os rankings e corta o nome', async () => {
  const p = await lerConvite(await gerarConvite(perfil));
  assert.equal(p.nome, 'Ana 🎸');
  assert.deepEqual(p.top_artistas, perfil.top_artistas);
  assert.deepEqual(p.top_musicas, perfil.top_musicas);
  const longo = await lerConvite(await gerarConvite({ ...perfil, nome: '🎸'.repeat(70) }));
  assert.equal([...longo.nome].length, 60);
});

test('convite: aceita quebras de linha no meio do código', async () => {
  const c = await gerarConvite(perfil);
  assert.equal((await lerConvite(`${c.slice(0, 20)}\n ${c.slice(20)}`)).nome, 'Ana 🎸');
});

test('convite: recusa prefixo errado, código alterado, cortado, bomba e sem artistas', async () => {
  const c = await gerarConvite(perfil);
  await assert.rejects(lerConvite('oi'), /não parece um convite/);
  await assert.rejects(lerConvite(c.slice(0, -6)), /incompleto ou foi alterado/);
  await assert.rejects(lerConvite(`${c}AAAA`), /incompleto ou foi alterado/);
  await assert.rejects(lerConvite(codigo({ n: 'A', a: { short_term: ['x'.repeat(200_000)] }, m: {} })), /incompleto ou foi alterado/);
  await assert.rejects(lerConvite(codigo({ n: 'A', a: { short_term: ['x'.repeat(201)] }, m: {} })), /incompleto ou foi alterado/);
  await assert.rejects(lerConvite(codigo({ n: 'A', a: {}, m: {} })), /não tem nenhum ranking/);
  await assert.rejects(lerConvite(codigo([1])), /incompleto ou foi alterado/);
  await assert.rejects(lerConvite(PREFIXO + 'A'.repeat(20_001)), /grande demais/);
});

test('convite: separa vários códigos colados, com pedaços quebrados', () => {
  assert.deepEqual(separarConvites(`${PREFIXO}abc\ndef  ${PREFIXO}xyz\n`), [`${PREFIXO}abcdef`, `${PREFIXO}xyz`]);
  assert.deepEqual(separarConvites('  '), []);
});

// R1-10: a mesma tabela de tests/test_convite.py.
test('música malformada recusa o convite', async () => {
  const { deflateSync } = await import('node:zlib');
  const { lerConvite } = await import('../../site/app/js/convite.js');
  for (const musica of ['lixo', [1], ['a', 'b', 'c'], { x: 1 }]) {
    const dados = { n: 'Teste', a: { short_term: ['Banda A'] }, m: { short_term: [['Faixa 1', 'Banda A'], musica] } };
    await assert.rejects(lerConvite(`SYNCUP1.${deflateSync(JSON.stringify(dados)).toString('base64url')}`), /incompleto ou foi alterado/);
  }
});
