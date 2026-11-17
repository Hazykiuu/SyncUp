// Lógica da Batalha (modo Grupo do app web). Rodar: node --test tests/js/*.test.mjs
import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  alertaPaciencia, arredondar, campeoes, CORES, decididoNoDetalhe, destaqueRodada, janelaComum, maisAfinada, medalhas, montarBatalha,
  numerosDoLutador, posicoes, tituloCampeao,
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

/* ---------- Adendo: disputa e narrativa ---------- */
const r = (valores, menor = false, chave = 'horas') => ({ chave, valores, posicoes: posicoes(valores, menor), menor });

test('destaqueRodada: por um triz com 5% exatos, nada com 6%', () => {
  assert.equal(destaqueRodada(r([100, 95, 10])), 'por-um-triz');
  assert.equal(destaqueRodada(r([100, 94, 10])), null);
});

test('destaqueRodada: por um triz invertido na Paciência', () => {
  assert.equal(destaqueRodada(r([19.0, 20.0, 40], true, 'paciencia')), 'por-um-triz');
});

test('destaqueRodada: massacre com 2x exatos; nada com 2º zerado ou empate no topo', () => {
  assert.equal(destaqueRodada(r([200, 100, 50])), 'massacre');
  assert.equal(destaqueRodada(r([10, 4.9, 1], true, 'paciencia')), 'massacre');
  assert.equal(destaqueRodada(r([100, 0, 0])), null);
  assert.equal(destaqueRodada(r([100, 100, 50])), null);
});

test('alertaPaciencia: último único acima de 60%', () => {
  const nomes = ['Ana', 'Bia', 'Caio'];
  assert.deepEqual(alertaPaciencia(r([10, 20, 60.1], true, 'paciencia'), nomes), { nome: 'Caio', valor: 60.1 });
  assert.equal(alertaPaciencia(r([10, 20, 60.0], true, 'paciencia'), nomes), null);
  assert.equal(alertaPaciencia(r([10, 70, 70], true, 'paciencia'), nomes), null);
  assert.equal(alertaPaciencia(r([10, 20, 70], false, 'horas'), nomes), null);
});

// Batalha mínima: o lutador 0 vence as rodadas pedidas; o 1 vence o resto (para ter um único campeão use `extra`).
function batalhaCom(ganhas, extra = {}) {
  const todas = ['horas', 'plays', 'artistas', 'musicas', 'sequencia', 'dia', 'coruja', 'repeteco', 'fa', 'paciencia'];
  const rodadasB = todas.map((chave) => ({ chave, posicoes: ganhas.includes(chave) ? [1, 2, 3] : [3, 2, 1] }));
  return { rodadas: rodadasB, campeoes: [0], ...extra };
}

test('tituloCampeao: as combinações, a ordem e o Dono(a) do Aux', () => {
  assert.equal(tituloCampeao(batalhaCom(['coruja', 'dia'])), 'Insone Oficial');
  assert.equal(tituloCampeao(batalhaCom(['repeteco', 'fa'])), 'Modo Obsessão');
  assert.equal(tituloCampeao(batalhaCom(['artistas', 'musicas'])), 'Enciclopédia Musical');
  assert.equal(tituloCampeao(batalhaCom(['horas', 'plays'])), 'Trator de Plays');
  assert.equal(tituloCampeao(batalhaCom(['coruja', 'dia', 'repeteco', 'fa', 'artistas', 'musicas', 'horas', 'plays'])), 'Insone Oficial');
  assert.equal(tituloCampeao(batalhaCom(['horas', 'coruja'])), 'Dono(a) do Aux');
  assert.equal(tituloCampeao(batalhaCom(['horas'], { campeoes: [0, 1] })), null);
});

test('maisAfinada: artista-cola pelo menor dos dois e a dupla menos afinada', () => {
  const m = (obj) => new Map(Object.entries(obj));
  const r1 = maisAfinada([m({ estrela: 500, cola: 80 }), m({ estrela: 1, cola: 80 }), m({ z: 3 })], ['Ana', 'Bia', 'Caio']);
  assert.equal(r1.artistaComum, 'cola');
  assert.ok(r1.menosAfinada.par.includes(2));
  const r2 = maisAfinada([m({ a: 1 }), m({ b: 1 }), m({ c: 1 })], ['Ana', 'Bia', 'Caio']);
  assert.equal(r2.artistaComum, null);
  // Todos com 0%: menos afinada = menos artistas em comum (0), depois os nomes do fim da ordem.
  assert.deepEqual(r2.menosAfinada.par, [1, 2]);
});

test('decididoNoDetalhe: 1 ouro de diferença, ou ouro empatado e prata decide', () => {
  const b = (m, campeoes = [0]) => ({ campeoes, lutadores: m.map((medalhas) => ({ medalhas })) });
  assert.equal(decididoNoDetalhe(b([{ ouro: 3, prata: 0, bronze: 0 }, { ouro: 2, prata: 5, bronze: 0 }, { ouro: 0, prata: 0, bronze: 0 }])), true);
  assert.equal(decididoNoDetalhe(b([{ ouro: 2, prata: 2, bronze: 0 }, { ouro: 2, prata: 1, bronze: 9 }, { ouro: 0, prata: 0, bronze: 0 }])), true);
  assert.equal(decididoNoDetalhe(b([{ ouro: 4, prata: 0, bronze: 0 }, { ouro: 2, prata: 0, bronze: 0 }, { ouro: 0, prata: 0, bronze: 0 }])), false);
  assert.equal(decididoNoDetalhe(b([{ ouro: 2, prata: 1, bronze: 2 }, { ouro: 2, prata: 1, bronze: 1 }, { ouro: 0, prata: 0, bronze: 0 }])), false);
  assert.equal(decididoNoDetalhe(b([{ ouro: 2, prata: 0, bronze: 0 }, { ouro: 2, prata: 0, bronze: 0 }], [0, 1])), false);
});

test('montarBatalha traz selos, título, detalhe e resenha', () => {
  const m = (obj) => new Map(Object.entries(obj));
  const b = montarBatalha([
    { ...lutador('Ana', { horas: 50, plays: 900 }), contagens: m({ x: 5, y: 1 }) },
    { ...lutador('Bia', { horas: 20 }), contagens: m({ x: 5, y: 1 }) },
    { ...lutador('Caio', { horas: 30, plays: 50 }), contagens: m({ z: 3 }) },
  ]);
  assert.equal(b.rodadas.find((x) => x.chave === 'horas').destaque, null); // 50 h x 30 h: nem triz nem 2x
  assert.equal(b.rodadas.find((x) => x.chave === 'plays').destaque, 'massacre'); // 900 x 100
  assert.equal(b.titulo, 'Trator de Plays');
  assert.equal(b.afinada.artistaComum, 'x');
  assert.match(b.resenha, /Ana/);
  assert.match(b.resenha, /Trator de Plays/);
});

test('selos e título de classe (#e6e6e6) legíveis sobre o cartão de vidro mais claro', () => {
  assert.ok(contraste('#e6e6e6', '#2a2a2a') >= 4.5, contraste('#e6e6e6', '#2a2a2a').toFixed(2));
});

test('trilha da Batalha: favorito de quem venceu cada rodada, artista que une a dupla e o do campeão no pódio', async () => {
  const { favorito, trilhaBatalha } = await import('../../site/app/js/batalha.js');
  assert.equal(favorito(new Map([['B', 3], ['A', 3], ['C', 1]])), 'A'); // empate: ordem de ponto de código
  assert.equal(favorito(new Map()), null);
  const b = { campeoes: [1], afinada: { artistaComum: 'Zé' }, rodadas: [{ chave: 'horas', posicoes: [2, 1, 3] }, { chave: 'plays', posicoes: [1, 2, 3] }] };
  const t = trilhaBatalha(b, ['Ana fav', 'Bia fav', null]);
  assert.deepEqual(t.slides['rodada-horas'], [{ artista: 'Bia fav' }]);
  assert.deepEqual(t.slides['rodada-plays'], [{ artista: 'Ana fav' }]);
  assert.deepEqual(t.slides.afinada, [{ artista: 'Zé' }]);
  assert.deepEqual(t.slides.podio, [{ artista: 'Bia fav' }]);
  assert.deepEqual(t.fila, [{ artista: 'Ana fav' }, { artista: 'Bia fav' }]);
  const semComum = trilhaBatalha({ ...b, afinada: { artistaComum: null } }, ['A', 'B', 'C']);
  assert.equal(semComum.slides.afinada, undefined);
  assert.deepEqual(semComum.slides.abertura, [{ artista: 'B' }]);
});

test('textos legíveis sobre a superfície sólida da 1.19 (#181818)', () => {
  assert.ok(contraste('#e6e6e6', '#181818') >= 4.5, contraste('#e6e6e6', '#181818').toFixed(2));
  assert.ok(contraste('#b3b3b3', '#181818') >= 4.5, contraste('#b3b3b3', '#181818').toFixed(2)); // --sub
});
