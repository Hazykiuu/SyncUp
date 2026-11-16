// Lógica da Batalha (modo Grupo do app web). Rodar: node --test tests/js/*.test.mjs
import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  arredondar, campeoes, CORES, janelaComum, maisAfinada, medalhas, montarBatalha, numerosDoLutador, posicoes,
  recortar, rodadas, validarNomes,
} from '../../site/app/js/batalha.js';

// Números de um lutador como o Worker extrai do calcularWrapped (unidades de tela: horas e %).
const lutador = (nome, numeros = {}) => ({
  nome,
  numeros: { horas: 10, plays: 100, artistas: 20, musicas: 50, sequencia: 3, dia: 2, coruja: 5, repeteco: 4, fa: 10, paciencia: 20, ...numeros },
});
const rodada = (lista, chave) => rodadas(lista).dentro.find((r) => r.chave === chave);
const fora = (lista, chave) => rodadas(lista).fora.find((r) => r.chave === chave);

// Colunas mínimas de lerHistorico: um evento por linha [utc, ms, musica, artista].
const HORA = 3_600_000;
function colunas(eventos) {
  const c = { utc: [], local: [], ms: [], musica: [], artista: [], uri: [], pulada: [], aleatorio: [], offline: [], plataforma: [], motivo: [] };
  for (const [utc, ms, musica, artista] of eventos) {
    c.utc.push(utc); c.local.push(utc - 3 * HORA); c.ms.push(ms); c.musica.push(musica); c.artista.push(artista);
    c.uri.push(null); c.pulada.push(null); c.aleatorio.push(null); c.offline.push(null); c.plataforma.push(null); c.motivo.push(null);
  }
  c.contadores = { validos: eventos.length };
  return c;
}

test('arredonda na casa que a tela mostra', () => {
  assert.equal(arredondar(14.249, 1), 14.2);
  assert.equal(arredondar(14.25, 1), 14.3);
  assert.equal(arredondar(2.5, 0), 3);
  assert.equal(arredondar(0, 1), 0);
});

test('valores que só diferem nas casas escondidas empatam', () => {
  const r = rodada([lutador('Ana', { fa: 14.21 }), lutador('Bia', { fa: 14.24 }), lutador('Caio', { fa: 9 })], 'fa');
  assert.deepEqual(r.valores, [14.2, 14.2, 9]);
  assert.deepEqual(r.posicoes, [1, 1, 3]);
});

test('posição olímpica: 1, 1, 1, 4 e 1, 2, 2, 4', () => {
  assert.deepEqual(posicoes([5, 5, 5, 2], false), [1, 1, 1, 4]);
  assert.deepEqual(posicoes([9, 5, 5, 2], false), [1, 2, 2, 4]);
  assert.deepEqual(posicoes([1, 3, 2], true), [1, 3, 2]); // menor vence
});

test('três empatados em primeiro levam ouro e ninguém leva prata nem bronze', () => {
  const m = medalhas([{ posicoes: [1, 1, 1, 4] }]);
  assert.deepEqual(m, [
    { ouro: 1, prata: 0, bronze: 0 }, { ouro: 1, prata: 0, bronze: 0 },
    { ouro: 1, prata: 0, bronze: 0 }, { ouro: 0, prata: 0, bronze: 0 },
  ]);
  assert.deepEqual(medalhas([{ posicoes: [1, 2, 2, 4] }]).map((x) => x.prata), [0, 1, 1, 0]);
});

test('Paciência: menor vence, e sai se alguém não tem o dado de pulos', () => {
  const r = rodada([lutador('Ana', { paciencia: 0 }), lutador('Bia', { paciencia: 12 }), lutador('Caio', { paciencia: 30 })], 'paciencia');
  assert.deepEqual(r.posicoes, [1, 2, 3]); // 0% de verdade ganha
  const f = fora([lutador('Ana', { paciencia: 0 }), lutador('Bia', { paciencia: null }), lutador('Caio', { paciencia: 30 })], 'paciencia');
  assert.match(f.motivo, /pulad/);
});

test('rodada sai quando ninguém pontua ou todos empatam', () => {
  const zerados = [lutador('Ana', { coruja: 0 }), lutador('Bia', { coruja: 0 }), lutador('Caio', { coruja: 0.04 })];
  assert.ok(fora(zerados, 'coruja'), 'Coruja com todos em 0% (0,04 vira 0,0) fica de fora');
  const semRepetir = [lutador('Ana', { repeteco: 1 }), lutador('Bia', { repeteco: 1 }), lutador('Caio', { repeteco: 0 })];
  assert.ok(fora(semRepetir, 'repeteco'), 'Repeteco com todos ≤ 1 fica de fora');
  const iguais = [lutador('Ana'), lutador('Bia'), lutador('Caio')];
  assert.match(fora(iguais, 'horas').motivo, /empat/);
});

test('co-campeões quando ouro, prata e bronze empatam', () => {
  assert.deepEqual(campeoes([{ ouro: 2, prata: 1, bronze: 0 }, { ouro: 2, prata: 1, bronze: 0 }, { ouro: 2, prata: 0, bronze: 3 }]), [0, 1]);
  assert.deepEqual(campeoes([{ ouro: 1, prata: 0, bronze: 0 }, { ouro: 0, prata: 5, bronze: 5 }, { ouro: 0, prata: 0, bronze: 0 }]), [0]);
});

test('dupla mais afinada: maior cosseno, depois mais artistas em comum, depois os nomes', () => {
  const m = (obj) => new Map(Object.entries(obj));
  // Ana e Bia ouvem igual; Caio nada em comum.
  let r = maisAfinada([m({ x: 2, y: 1 }), m({ x: 2, y: 1 }), m({ z: 5 })], ['Ana', 'Bia', 'Caio']);
  assert.deepEqual(r.par, [0, 1]);
  assert.equal(r.valor, 100);
  // Dois pares com 100%: vence o que tem mais artistas em comum.
  r = maisAfinada([m({ x: 1 }), m({ x: 1 }), m({ y: 1, w: 1 }), m({ y: 1, w: 1 })], ['Ana', 'Bia', 'Caio', 'Duda']);
  assert.deepEqual(r.par, [2, 3]);
  assert.equal(r.comuns, 2);
  // Empate nos dois: vence o par cujos nomes vêm primeiro.
  r = maisAfinada([m({ x: 1 }), m({ x: 1 }), m({ y: 1 }), m({ y: 1 })], ['Zeca', 'Yuri', 'Ana', 'Bia']);
  assert.deepEqual(r.par, [2, 3]);
});

test('nomes: de 3 a 6, sem repetir, vazio vira Pessoa N', () => {
  assert.throws(() => validarNomes(['Ana', 'Bia']), /3 a 6/);
  assert.throws(() => validarNomes(['A', 'B', 'C', 'D', 'E', 'F', 'G']), /3 a 6/);
  assert.throws(() => validarNomes(['Ana', 'Bia', 'Ana ']), /nomes diferentes/);
  assert.deepEqual(validarNomes([' Ana ', '', 'Caio']), ['Ana', 'Pessoa 2', 'Caio']);
});

test('janela comum: maior início e menor fim; sem interseção é erro', () => {
  assert.deepEqual(janelaComum([[10, 50], [20, 60], [5, 40]]), [20, 40]);
  assert.throws(() => janelaComum([[10, 20], [30, 40], [0, 50]]), /período comum/);
});

test('recortar mantém só os eventos da janela, em todas as colunas', () => {
  const c = colunas([[1, 40_000, 'm1', 'a'], [5, 40_000, 'm2', 'b'], [9, 40_000, 'm3', 'c']]);
  const r = recortar(c, 2, 9);
  assert.deepEqual(r.utc, [5, 9]);
  assert.deepEqual(r.musica, ['m2', 'm3']);
  assert.equal(r.pulada.length, 2);
});

test('lutador sem plays de 30 s na janela é erro com o nome', () => {
  const c = colunas([[HORA, 10_000, 'm', 'a']]);
  assert.throws(() => numerosDoLutador(c, 'Bia', 'America/Sao_Paulo'), /Não há plays ≥30s para Bia/);
});

test('numerosDoLutador tira os números do Wrapped e conta os artistas', () => {
  const dia = 24 * HORA;
  const c = colunas([[10 * dia, 60_000, 'm1', 'a'], [10 * dia + HORA, 60_000, 'm1', 'a'], [11 * dia, 60_000, 'm2', 'b'], [11 * dia + HORA, 5_000, 'm3', 'c']]);
  const { numeros, contagens } = numerosDoLutador(c, 'Ana', 'America/Sao_Paulo');
  assert.equal(numeros.plays, 3);
  assert.equal(numeros.artistas, 2);
  assert.equal(numeros.sequencia, 2);
  assert.equal(numeros.paciencia, null); // sem skipped nem reason_end
  assert.deepEqual([...contagens], [['a', 2], ['b', 1]]);
});

test('sem nenhuma rodada sobrando, a batalha é erro', () => {
  const iguais = [lutador('Ana'), lutador('Bia'), lutador('Caio')];
  assert.throws(() => montarBatalha(iguais.map((l) => ({ ...l, contagens: new Map([['x', 1]]) }))), /números suficientes/);
});

test('batalha completa: rodadas, medalhas, campeão e dupla afinada', () => {
  const m = (obj) => new Map(Object.entries(obj));
  const b = montarBatalha([
    { ...lutador('Ana', { horas: 50, plays: 900 }), contagens: m({ x: 5, y: 1 }) },
    { ...lutador('Bia', { horas: 20 }), contagens: m({ x: 5, y: 1 }) },
    { ...lutador('Caio', { horas: 30, plays: 50 }), contagens: m({ z: 3 }) },
  ]);
  assert.deepEqual(b.rodadas.map((r) => r.chave), ['horas', 'plays']);
  assert.deepEqual(b.campeoes, [0]);
  assert.deepEqual(b.afinada.par, [0, 1]);
  assert.deepEqual(b.lutadores.map((l) => l.cor), CORES.slice(0, 3));
  assert.ok(b.fora.length >= 8);
});

// Contraste WCAG das 6 cores: barra sobre o fundo (3:1), texto colorido (4,5:1) e texto preto sobre a cor (4,5:1).
const luminancia = (hex) => {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((v) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};
const contraste = (a, b) => { const [x, y] = [luminancia(a), luminancia(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };

test('as 6 cores dos lutadores têm contraste no fundo escuro e com texto preto', () => {
  assert.equal(CORES.length, 6);
  for (const cor of CORES) {
    assert.ok(contraste(cor, '#121212') >= 4.5, `${cor} sobre #121212: ${contraste(cor, '#121212').toFixed(2)}`);
    assert.ok(contraste('#000000', cor) >= 4.5, `#000 sobre ${cor}: ${contraste('#000000', cor).toFixed(2)}`);
  }
});
