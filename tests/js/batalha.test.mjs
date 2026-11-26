// Lógica da Batalha (modo Grupo do app web). Rodar: node --test tests/js/*.test.mjs
import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  alertaPaciencia, arredondar, campeoes, CORES, decididoNoDetalhe, destaqueRodada, janelaComum, maisAfinada, medalhas, montarBatalha,
  numerosDoLutador, posicoes, resenha, tituloCampeao,
  recortar, rodadas, validarNomes,
} from '../../site/app/js/batalha.js';
import { FAMILIAS, TEMA, TITULOS } from '../../site/app/js/batalha-temas.js';

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
  // Ruling (Batalha v2, passo 2): "Só eu conheço" sai das contagens; Caio é o único com um artista só dele.
  assert.deepEqual(b.rodadas.map((r) => r.chave), ['horas', 'plays', 'soeu']);
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

// Ruling (passo 5): o título vem da família em que o campeão fez 2 ouros ou mais (antes, de pares fixos de rodadas).
// Muda: coruja + dia (famílias relógio e volume) não dá mais "Insone Oficial", e com 8 ouros vale a primeira família
// do registro (volume), não mais a primeira combinação da lista antiga.
test('tituloCampeao: as famílias de antes, a ordem e o Dono(a) do Aux', () => {
  assert.equal(tituloCampeao(batalhaCom(['coruja', 'dia'])), 'Dono(a) do Aux');
  assert.equal(tituloCampeao(batalhaCom(['repeteco', 'fa'])), 'Modo Obsessão');
  assert.equal(tituloCampeao(batalhaCom(['artistas', 'musicas'])), 'Enciclopédia Musical');
  assert.equal(tituloCampeao(batalhaCom(['horas', 'plays'])), 'Trator de Plays');
  assert.equal(tituloCampeao(batalhaCom(['coruja', 'dia', 'repeteco', 'fa', 'artistas', 'musicas', 'horas', 'plays'])), 'Trator de Plays');
  assert.equal(tituloCampeao(batalhaCom(['horas', 'coruja'])), 'Dono(a) do Aux');
  assert.equal(tituloCampeao(batalhaCom(['horas'], { campeoes: [0, 1] })), null);
});

// Rodadas quaisquer: o campeão (índice 0) vence as de `ganhas` e fica em 3º nas outras.
const comOuros = (ganhas, perdidas = []) => ({
  campeoes: [0],
  rodadas: [...ganhas.map((chave) => ({ chave, posicoes: [1, 2, 3] })), ...perdidas.map((chave) => ({ chave, posicoes: [3, 2, 1] }))],
});

test('tituloCampeao: um título por família, verdadeiro para qualquer tema dela', () => {
  const dois = {
    volume: ['metralhadora', 'cruzeiro'], variedade: ['buffet', 'elenco'], repeticao: ['disco', 'obra'], relogio: ['coruja', 'madrugador'],
    calendario: ['sextou', 'virada'], constancia: ['sumico', 'sessao'], pulos: ['paciencia', 'destino'], aparelhos: ['bolso', 'aparelhos'],
    descoberta: ['faro', 'raizes'], grupo: ['soeu', 'turma'],
  };
  for (const f of FAMILIAS) {
    assert.equal(tituloCampeao(comOuros(dois[f])), TITULOS[f], f);
    assert.equal(tituloCampeao(comOuros(dois[f].slice(0, 1), dois[f].slice(1))), 'Dono(a) do Aux', `${f} com 1 ouro`);
  }
  const nomes = Object.values(TITULOS);
  assert.equal(new Set(nomes).size, FAMILIAS.length);
  for (const t of [...nomes, 'Dono(a) do Aux']) {
    assert.ok([...t].length <= 20, t); // cabe no pódio do story (1/3 da largura) e no pôster, como o mais longo de antes
    assert.doesNotMatch(t, /\p{Extended_Pictographic}/u, t);
  }
});

test('tituloCampeao: mais ouros na família vencem a ordem; empate fica com a primeira família do registro', () => {
  assert.equal(tituloCampeao(comOuros(['horas', 'plays', 'artistas', 'musicas', 'buffet'])), 'Enciclopédia Musical');
  assert.equal(tituloCampeao(comOuros(['soeu', 'dj', 'coruja', 'noite'])), TITULOS.relogio);
  assert.equal(tituloCampeao(comOuros(['coruja', 'virada', 'soeu', 'bolso'])), 'Dono(a) do Aux'); // 4 ouros, 1 por família
});

test('resenha: o título vem com as rodadas que o deram', () => {
  const b = {
    ...comOuros(['sextou', 'virada'], ['horas']), menosAfinada: { par: [1, 2], valor: 12.5 },
  };
  b.rodadas = b.rodadas.map((r) => ({ ...r, titulo: TEMA[r.chave].titulo, destaque: null }));
  b.titulo = tituloCampeao(b);
  assert.match(resenha(b, ['Ana', 'Bia', 'Caio']), /^Ana levou a batalha como Agenda Cheia, com ouro em Sextou e Virada\. /);
  const aux = { ...b, rodadas: b.rodadas.slice(1), titulo: 'Dono(a) do Aux' };
  assert.match(resenha(aux, ['Ana', 'Bia', 'Caio']), /^Ana levou a batalha como Dono\(a\) do Aux\. /);
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

/* ---------- Batalha v2: registro dos 56 temas ---------- */
// Entrada fixa: 240 eventos de 20/12/2023 em diante, com pulos, aleatório, offline e aparelho preenchidos.
function historicoFixo() {
  const c = { utc: [], local: [], ms: [], musica: [], artista: [], uri: [], pulada: [], aleatorio: [], offline: [], plataforma: [], motivo: [] };
  for (let i = 0; i < 240; i++) {
    const utc = Date.UTC(2023, 11, 20) + Math.round(i * 4.7 * HORA) + (i % 4) * 600_000;
    c.utc.push(utc); c.local.push(utc - 3 * HORA); c.ms.push(20_000 + ((i * 7919) % 240_000));
    c.musica.push(`m${(i * i) % 17}`); c.artista.push(`a${i % 7 === 0 ? 0 : i % 5}`); c.uri.push(null);
    c.pulada.push(i % 5 === 0); c.aleatorio.push(i % 3 === 0); c.offline.push(i % 11 === 0);
    c.plataforma.push(['Android', 'Windows', 'iOS'][i % 3]); c.motivo.push(i % 5 === 0 ? 'fwdbtn' : 'trackdone');
  }
  return c;
}

test('regressão: os 10 temas de antes dão exatamente os mesmos números', () => {
  const { numeros } = numerosDoLutador(historicoFixo(), 'Ana', 'America/Sao_Paulo');
  const dez = ['horas', 'plays', 'artistas', 'musicas', 'sequencia', 'dia', 'coruja', 'repeteco', 'fa', 'paciencia'];
  assert.deepEqual(Object.fromEntries(dez.map((k) => [k, numeros[k]])), {
    horas: 9.221366666666665, plays: 229, artistas: 5, musicas: 45, sequencia: 48, dia: 0.3577408333333334,
    coruja: 25.76419213973799, repeteco: 2, fa: 31.877729257641924, paciencia: 20,
  });
});

test('registro: 56 temas em 10 famílias, 6 modelos de desenho e pares opostos', async () => {
  const { TEMAS, TEMA, FAMILIAS, MODELOS, OPOSTOS } = await import('../../site/app/js/batalha-temas.js');
  assert.equal(TEMAS.length, 56);
  assert.equal(new Set(TEMAS.map((t) => t.chave)).size, 56);
  assert.deepEqual(FAMILIAS.map((f) => TEMAS.filter((t) => t.familia === f).length), [5, 6, 7, 6, 6, 7, 6, 3, 6, 4]);
  assert.deepEqual(MODELOS, ['corrida', 'porcentagem', 'relogio', 'calendario', 'sequencia', 'contagem']);
  for (const t of TEMAS) {
    assert.ok(MODELOS.includes(t.modelo), t.chave);
    assert.match(t.frase, /^[A-ZÁÉÍÓÚ].*\.$/u, t.chave);
    assert.ok(t.titulo && t.unidade && Number.isInteger(t.casas), t.chave);
    assert.ok(t.menor || t.vazio, `${t.chave}: sem motivo para quando ninguém pontua`);
    assert.ok(Array.isArray(t.campos) && typeof t.aprox === 'boolean' && typeof t.pct === 'boolean', t.chave);
    if (t.pct) assert.equal(t.escala, 100, t.chave);
    assert.doesNotMatch(`${t.titulo}${t.unidade}${t.frase}`, /\p{Extended_Pictographic}/u, t.chave);
  }
  for (const [a, b] of OPOSTOS) {
    assert.equal(TEMA[a].familia, TEMA[b].familia);
    assert.notEqual(!!TEMA[a].menor, !!TEMA[b].menor, `${a} x ${b}`);
  }
  assert.deepEqual(OPOSTOS, [['nuncasome', 'sumico'], ['paciencia', 'dedo'], ['destino', 'adedo']]);
});

test('registro: os 10 de antes mantêm chave, título, unidade, frase e escala', async () => {
  const { TEMA } = await import('../../site/app/js/batalha-temas.js');
  const antes = [
    ['horas', 'Maratonista', 'h', 0, 'Horas de música no período.'],
    ['plays', 'Play infinito', 'plays', 0, 'Plays de pelo menos 30 segundos.'],
    ['artistas', 'Explorador(a)', 'artistas', 0, 'Artistas diferentes que cada um ouviu.'],
    ['musicas', 'Colecionador(a)', 'músicas', 0, 'Músicas diferentes na estante de cada um.'],
    ['sequencia', 'Sem parar', 'dias seguidos', 0, 'Dias seguidos ouvindo, sem falhar um.'],
    ['dia', 'Dia mais insano', 'h num dia', 1, 'O dia em que mais ouviu, nas 24 horas.'],
    ['coruja', 'Coruja', '% na madrugada', 1, 'Fatia dos plays entre meia-noite e 6 h.'],
    ['repeteco', 'Repeteco', 'vezes a mesma música num dia', 0, 'A mesma música, repetida num dia só.'],
    ['fa', 'Fã nº 1', '% no artista favorito', 1, 'Fatia dos plays no artista favorito.'],
    ['paciencia', 'Paciência', '% de músicas puladas', 1, 'Fatia de músicas puladas. Aqui, menos é melhor.'],
  ];
  for (const [chave, titulo, unidade, casas, frase] of antes) assert.deepEqual([TEMA[chave].titulo, TEMA[chave].unidade, TEMA[chave].casas, TEMA[chave].frase], [titulo, unidade, casas, frase]);
  assert.equal(TEMA.paciencia.menor, true);
  assert.equal(TEMA.repeteco.minimo, 1);
  assert.deepEqual(['coruja', 'fa', 'paciencia', 'dia', 'horas'].map((k) => TEMA[k].escala), [100, 100, 100, 24, null]);
  assert.deepEqual(['horas', 'dia', 'plays', 'coruja'].map((k) => TEMA[k].aprox), [true, true, false, false]); // nota "≈" do Last.fm
});

test('rodadas: tema sem cálculo não aparece; dado ausente sai com o motivo do campo', () => {
  const lista = [lutador('Ana'), lutador('Bia', { paciencia: null, horas: 12 }), lutador('Caio', { horas: 30 })];
  const { dentro, fora: f } = rodadas(lista);
  assert.ok(dentro.every((r) => r.chave in lista[0].numeros));
  assert.ok(f.every((r) => r.chave in lista[0].numeros));
  assert.deepEqual(f.find((r) => r.chave === 'paciencia'), { chave: 'paciencia', titulo: 'Paciência', tipo: 'dado', motivo: 'nem todo histórico informa as músicas puladas' });
});

test('porcentagens pedem 100 plays de 30 s de cada pessoa', () => {
  const f = fora([lutador('Ana', { coruja: 9 }), lutador('Bia', { coruja: 4, plays: 99 }), lutador('Caio')], 'coruja');
  assert.equal(f.tipo, 'dado');
  assert.match(f.motivo, /100 plays/);
  assert.ok(rodada([lutador('Ana', { horas: 9 }), lutador('Bia', { plays: 99 }), lutador('Caio')], 'horas')); // horas não é porcentagem
});

/* ---------- Batalha v2: cálculo dos temas novos (contas feitas à mão) ---------- */
// [hora local 'AAAA-MM-DD HH:MM', ms, música, artista, campos opcionais]. Fuso -3: utc = local + 3 h, e utc é o FIM do play.
function hist(eventos) {
  const c = { utc: [], local: [], ms: [], musica: [], artista: [], uri: [], pulada: [], aleatorio: [], offline: [], plataforma: [], motivo: [] };
  for (const [quando, ms, musica, artista, x = {}] of eventos) {
    const local = Date.parse(`${quando.replace(' ', 'T')}:00Z`);
    c.utc.push(local + 3 * HORA); c.local.push(local); c.ms.push(ms); c.musica.push(musica); c.artista.push(artista); c.uri.push(null);
    for (const k of ['pulada', 'aleatorio', 'offline', 'plataforma', 'motivo']) c[k].push(x[k] ?? null);
  }
  return c;
}
const num = (eventos) => numerosDoLutador(hist(eventos), 'Ana', 'America/Sao_Paulo').numeros;
const perto = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `${a} ≠ ${b}`);
const MIN = 60_000;

test('volume, variedade e repetição', () => {
  const n = num([
    ['2024-03-04 10:00', MIN, 'm1', 'a1'], ['2024-03-04 10:05', MIN, 'm1', 'a1'], ['2024-03-04 12:00', MIN, 'm4', 'a3'],
    ['2024-03-04 23:59', 20_000, 'm2', 'a2'], // < 30 s: conta nas horas, não nos plays
    ['2024-03-05 00:00', 2 * MIN, 'm3', 'a2'], // meia-noite já é o dia 5
  ]);
  assert.equal(n.metralhadora, 3);
  perto(n.cruzeiro, (1 + 1 + 1 + 1 / 3 + 2) / 2);
  assert.equal(n.buffet, 2);
  perto(n.umavez, 200 / 3); // (m4, a3) e (m3, a2) de 3 músicas
  perto(n.visita, 200 / 3); // a3 e a2 de 3 artistas
  assert.equal(n.elenco, 75); // 3 artistas em 4 plays
  assert.equal(n.disco, 2);
  assert.equal(n.hino, 2);
  assert.equal(n.panelinha, 100);
  assert.equal(n.playlist, 100);
  assert.equal(n.obra, 1);
});

test('top 10 corta no 10º, obra conta músicas de um artista e presença conta dias do período', () => {
  // a1: 3 músicas no dia 1; a2 a a11: uma música cada no dia 4. 13 plays, 11 artistas, 13 músicas.
  const n = num([
    ...[1, 2, 3].map((k) => [`2024-03-01 10:0${k}`, MIN, `m${k}`, 'a1']),
    ...Array.from({ length: 10 }, (_, k) => [`2024-03-04 10:${String(k + 10)}`, MIN, `s${k}`, `a${k + 2}`]),
  ]);
  perto(n.panelinha, 1200 / 13); // a1 (3) + 9 artistas com 1
  perto(n.playlist, 1000 / 13); // 10 músicas de 1 play
  assert.equal(n.obra, 3);
  assert.equal(n.presenca, 50); // dias 1 e 4 de 1 a 4
});

test('em sequência: a ordem é a do início (fim − duração), não a do fim gravado', () => {
  // m1 termina 10:10 depois de 9 min (começou 10:01); m2 termina 10:05 e começou 10:04; m1 de novo às 10:19.
  const n = num([['2024-03-04 10:05', MIN, 'm2', 'a'], ['2024-03-04 10:10', 9 * MIN, 'm1', 'a'], ['2024-03-04 10:20', MIN, 'm1', 'a']]);
  assert.equal(n.disco, 1); // pela ordem do fim seriam 2 seguidas
  assert.equal(num([['2024-03-04 10:00', MIN, 'm1', 'a'], ['2024-03-04 10:01', 10_000, 'm9', 'a'], ['2024-03-04 10:02', MIN, 'm1', 'a']]).disco, 2); // pulo curto no meio não quebra
});

test('sessões e pausas: intervalo de 30 min, com a sobreposição de plays', () => {
  const n = num([
    ['2024-03-04 10:00', 10 * MIN, 'm1', 'a'], ['2024-03-04 10:20', 10 * MIN, 'm2', 'a'], // 9:50–10:20, uma sessão
    ['2024-03-04 12:00', 30 * MIN, 'm3', 'a'], // começa 11:30: 70 min depois, outra sessão
    ['2024-03-06 12:00', 60 * MIN, 'm4', 'a'], // começa 11:00 do dia 6: 47 h de pausa
  ]);
  assert.equal(n.sessao, 1);
  assert.equal(n.sessoes, 1.5); // 3 sessões em 2 dias com música
  perto(n.sumico, 47 / 24);
  perto(n.nuncasome, 47 / 24);
  // Um play longo (10:00–11:00) cobre um curto no meio (10:05–10:10): a pausa conta do fim do longo.
  const s = num([['2024-03-04 11:00', 60 * MIN, 'm1', 'a'], ['2024-03-04 10:10', 5 * MIN, 'm2', 'a'], ['2024-03-04 11:25', 5 * MIN, 'm3', 'a']]);
  perto(s.sessao, 85 / 60);
  assert.equal(s.sessoes, 1);
  perto(s.sumico, 20 / (24 * 60));
  const um = num([['2024-03-04 10:00', MIN, 'm1', 'a']]);
  assert.equal(um.sumico, null);
  assert.equal(um.nuncasome, null);
});

test('dias de maratona e mês lendário usam todas as reproduções', () => {
  const n = num([
    ['2024-01-31 23:00', 3 * 60 * MIN, 'm1', 'a'], ['2024-02-01 10:00', 179 * MIN, 'm2', 'a'],
    ['2024-02-02 10:00', 20_000, 'm3', 'a'], ['2024-02-03 10:00', MIN, 'm3', 'a'],
  ]);
  assert.equal(n.maratona, 1); // 31/1 com 3 h; 1º/2 com 2 h 59
  perto(n.mes, (180 * MIN + 20_000) / HORA); // fevereiro passa janeiro (3 h) só por causa do play de 20 s
});

test('relógio e calendário pela hora local', () => {
  const n = num([
    ['2024-03-01 18:00', MIN, 'm', 'a'], // sexta, 18 h: sextou, fim de tarde e noite
    ['2024-03-01 17:59', MIN, 'm', 'a'], // sexta, 17 h: só fim de tarde
    ['2024-03-02 12:30', MIN, 'm', 'a'], // sábado: almoço e fim de semana
    ['2024-03-04 00:00', MIN, 'm', 'a'], // segunda, meia-noite: madrugada
    ['2024-03-04 06:00', MIN, 'm', 'a'], // segunda, 6 h: manhã
  ]);
  assert.deepEqual([n.madrugador, n.almoco, n.tarde, n.noite, n.fimdesemana, n.sextou, n.segunda], [20, 20, 40, 20, 20, 20, 40]);
  perto(n.espalhado, (Math.log(5) / Math.log(24)) * 100); // 5 horas com um play cada
  perto(num(Array.from({ length: 24 }, (_, h) => [`2024-03-04 ${String(h).padStart(2, '0')}:10`, MIN, 'm', 'a'])).espalhado, 100);
});

test('Natal e virada: pela data local, e só quando o período passa por elas', () => {
  const n = num([
    ['2023-12-20 10:00', MIN, 'm', 'a'], ['2023-12-24 00:00', MIN, 'm', 'a'], ['2023-12-26 23:59', MIN, 'm', 'a'], ['2023-12-27 00:00', MIN, 'm', 'a'],
    ['2023-12-31 23:00', MIN, 'm', 'a'], ['2024-01-01 22:00', MIN, 'm', 'a'], // já é 2 de janeiro em UTC
    ['2024-01-03 10:00', MIN, 'm', 'a'],
  ]);
  assert.equal(n.natal, 2);
  assert.equal(n.virada, 2);
  const curto = num([['2023-12-20 10:00', MIN, 'm', 'a'], ['2023-12-25 10:00', MIN, 'm', 'a']]);
  assert.equal(curto.natal, null); // não chega ao dia 26
  assert.equal(curto.virada, null);
  assert.equal(num([['2024-03-04 10:00', MIN, 'm', 'a'], ['2024-12-24 10:00', MIN, 'm2', 'a'], ['2024-12-29 10:00', MIN, 'm', 'a']]).natal, 1);
  assert.equal(num([['2024-12-20 10:00', MIN, 'm', 'a'], ['2025-01-02 10:00', MIN, 'm', 'a']]).virada, 0); // passou pela virada sem ouvir: 0, não null
});

test('pulos, modo e aparelho: null quando o histórico não traz o campo', () => {
  const sem = num([['2024-03-04 10:00', MIN, 'm', 'a'], ['2024-03-04 11:00', MIN, 'm', 'a']]);
  for (const k of ['paciencia', 'dedo', 'ultimanota', 'destino', 'adedo', 'offline', 'bolso', 'mesa', 'aparelhos']) assert.equal(sem[k], null, k);
  const x = [
    { pulada: true, aleatorio: true, offline: true, plataforma: 'Android', motivo: 'fwdbtn' },
    { pulada: false, aleatorio: true, offline: false, plataforma: 'iOS', motivo: 'trackdone' },
    { pulada: false, aleatorio: false, offline: false, plataforma: 'Windows', motivo: 'trackdone' },
    { pulada: false, aleatorio: false, offline: false, plataforma: null, motivo: 'endplay' },
  ];
  const n = num(x.map((campos, i) => [`2024-03-04 1${i}:00`, MIN, `m${i}`, 'a', campos]));
  assert.deepEqual([n.paciencia, n.dedo, n.ultimanota, n.destino, n.adedo, n.offline], [25, 25, 50, 50, 50, 25]);
  perto(n.bolso, 200 / 3);
  perto(n.mesa, 100 / 3);
  assert.equal(n.aparelhos, 3);
  // Um play perdido numa TV (menos de 1% do que tem aparelho) não conta como aparelho.
  const tv = Array.from({ length: 101 }, (_, i) => [`2024-03-04 10:${String(i % 60).padStart(2, '0')}`, MIN, 'm', 'a', { plataforma: i ? 'Android' : 'TV, console ou caixa de som' }]);
  assert.equal(num(tv).aparelhos, 1);
});

test('descoberta e fidelidade', () => {
  const n = num([
    ['2023-01-10 10:00', MIN, 'm', 'a1'], ['2023-01-20 10:00', MIN, 'm', 'a2'], ['2023-02-05 10:00', MIN, 'm', 'a3'],
    ['2023-03-01 10:00', MIN, 'm', 'a1'], ['2023-08-15 10:00', MIN, 'm', 'a1'], // 167 dias depois: não é reencontro
    ['2024-01-10 10:00', MIN, 'm', 'a2'], // 355 dias depois: reencontro
    ['2024-01-15 10:00', MIN, 'm', 'a4'],
  ]);
  perto(n.novidades, 2 / 12); // a3 e a4 nos 12 meses depois de janeiro de 2023
  assert.equal(n.antigo, 355);
  assert.equal(n.fidelidade, 3); // a1 em jan, mar e ago
  assert.equal(n.reencontro, 1);
  perto(n.faro, 100 / 7); // a4, descoberto nos últimos 6 meses
  perto(n.raizes, 600 / 7); // a1, a2 e a3, nos primeiros 6 meses
  const curto = num([['2023-12-10 10:00', MIN, 'm', 'a1'], ['2023-12-20 10:00', MIN, 'm', 'a2']]);
  assert.deepEqual([curto.novidades, curto.faro, curto.raizes], [null, null, null]);
  perto(num([['2023-12-10 10:00', MIN, 'm', 'a1'], ['2024-01-02 10:00', MIN, 'm', 'a2']]).novidades, 1); // dezembro → janeiro é 1 mês
});

test('temas do grupo a partir das contagens e do primeiro play de cada artista', async () => {
  const { numerosDoGrupo } = await import('../../site/app/js/batalha-medidas.js');
  const m = (obj) => new Map(Object.entries(obj));
  const lista = [
    { contagens: m({ x: 5, y: 3, s: 2 }), primeiros: m({ x: 100, y: 500, s: 10 }) },
    { contagens: m({ x: 1, y: 4 }), primeiros: m({ x: 50, y: 500 }) },
    { contagens: m({ x: 2, z: 8 }), primeiros: m({ x: 300, z: 1 }) },
  ];
  assert.deepEqual(numerosDoGrupo(lista), [
    { soeu: 1, turma: 50, primeiro: 0, dj: 80 },
    { soeu: 0, turma: 20, primeiro: 1, dj: 100 }, // y empatado no mesmo instante: ninguém chega antes
    { soeu: 1, turma: 20, primeiro: 0, dj: 20 },
  ]);
  assert.deepEqual(numerosDoGrupo(lista.map(({ contagens }) => ({ contagens }))).map((g) => g.primeiro), [null, null, null]);
});

test('numerosDoLutador traz todos os temas que não dependem do grupo, e o primeiro play por artista', async () => {
  const { TEMAS } = await import('../../site/app/js/batalha-temas.js');
  const { numeros, primeiros } = numerosDoLutador(historicoFixo(), 'Ana', 'America/Sao_Paulo');
  for (const t of TEMAS) assert.equal(t.chave in numeros, t.familia !== 'grupo', t.chave);
  for (const t of TEMAS) if (t.familia !== 'grupo') assert.ok(numeros[t.chave] === null || Number.isFinite(numeros[t.chave]), t.chave);
  assert.deepEqual([...primeiros.keys()].sort(), ['a0', 'a1', 'a2', 'a3', 'a4']);
});

/* ---------- Batalha v2: sorteio com semente ---------- */
// Três pessoas com 300, 200 e 100 em cada tema pedido (os outros não existem para elas): todos elegíveis,
// porcentagens inclusive. Cada uma tem um artista só dela, então os temas do grupo empatam ou zeram e ficam fora.
const elenco = (chaves) => ['Ana', 'Bia', 'Caio'].map((nome, k) => ({ nome, numeros: Object.fromEntries(chaves.map((c) => [c, 300 - 100 * k])), contagens: new Map([[`x${k}`, 1]]) }));
const temas = async () => (await import('../../site/app/js/batalha-temas.js'));

test('sorteio: 10 temas, no máximo 2 por família, nunca um par oposto, na ordem do registro', async () => {
  const { TEMAS, TEMA, OPOSTOS } = await temas();
  const todos = elenco(TEMAS.filter((t) => t.familia !== 'grupo').map((t) => t.chave));
  const vistos = new Set();
  for (let semente = 1; semente <= 50; semente++) {
    const b = montarBatalha(todos, { semente });
    assert.equal(b.semente, semente);
    assert.equal(b.rodadas.length, 10);
    assert.deepEqual(b.temas, b.rodadas.map((r) => r.chave));
    const ordem = b.temas.map((k) => TEMAS.indexOf(TEMA[k]));
    assert.deepEqual(ordem, [...ordem].sort((x, y) => x - y));
    const porFamilia = Map.groupBy(b.temas, (k) => TEMA[k].familia);
    assert.ok([...porFamilia.values()].every((l) => l.length <= 2), b.temas.join());
    for (const [x, y] of OPOSTOS) assert.ok(!(b.temas.includes(x) && b.temas.includes(y)), `${x} e ${y}`);
    vistos.add(b.temas.join());
  }
  assert.ok(vistos.size > 40, `só ${vistos.size} sorteios diferentes em 50`);
});

test('sorteio: mesma entrada e semente dão o mesmo resultado; batalha anterior não se repete', async () => {
  const { TEMAS } = await temas();
  const todos = elenco(TEMAS.filter((t) => t.familia !== 'grupo').map((t) => t.chave));
  const a = montarBatalha(todos, { semente: 7 });
  assert.deepEqual(montarBatalha(todos, { semente: 7 }), a);
  assert.deepEqual(montarBatalha(todos), montarBatalha(todos)); // sem semente: a padrão, fixa
  const b = montarBatalha(todos, { semente: 7, evitar: a.temas });
  assert.equal(b.rodadas.length, 10);
  assert.deepEqual(b.temas.filter((k) => a.temas.includes(k)), []);
});

test('sorteio: quando as regras não cabem, volta a batalha anterior antes de passar do teto por família', async () => {
  // 4 famílias com 2 temas cada e 4 temas de variedade: 12 elegíveis. Sem os 2 de volume (batalha anterior), sobram 8 no teto.
  const chaves = ['horas', 'plays', 'repeteco', 'fa', 'coruja', 'madrugador', 'natal', 'virada', 'artistas', 'musicas', 'buffet', 'umavez'];
  const b = montarBatalha(elenco(chaves), { semente: 3, evitar: ['horas', 'plays'] });
  assert.equal(b.rodadas.length, 10);
  assert.ok(b.temas.includes('horas') && b.temas.includes('plays'));
  assert.equal(b.temas.filter((k) => ['artistas', 'musicas', 'buffet', 'umavez'].includes(k)).length, 2);
  // Só 3 famílias: o teto cai e as 10 rodadas saem assim mesmo.
  const tres = montarBatalha(elenco(['horas', 'plays', 'dia', 'metralhadora', 'artistas', 'musicas', 'buffet', 'umavez', 'repeteco', 'fa', 'disco', 'hino']), { semente: 3 });
  assert.equal(tres.rodadas.length, 10);
});

test('sorteio: com menos de 10 elegíveis usa todos, menos um de cada par oposto', () => {
  const b = montarBatalha(elenco(['horas', 'plays', 'artistas', 'paciencia', 'dedo', 'destino', 'adedo']), { semente: 5 });
  assert.equal(b.rodadas.length, 5);
  assert.equal(b.temas.filter((k) => k === 'paciencia' || k === 'dedo').length, 1);
  assert.equal(b.temas.filter((k) => k === 'destino' || k === 'adedo').length, 1);
  assert.ok(['horas', 'plays', 'artistas'].every((k) => b.temas.includes(k)));
});

test('Dedinho nervoso vale também no Dedo nervoso, onde quem pula mais vence', () => {
  assert.deepEqual(alertaPaciencia(r([10, 20, 70], false, 'dedo'), ['Ana', 'Bia', 'Caio']), { nome: 'Caio', valor: 70 });
});

test('textos legíveis sobre a superfície sólida da 1.19 (#181818)', () => {
  assert.ok(contraste('#e6e6e6', '#181818') >= 4.5, contraste('#e6e6e6', '#181818').toFixed(2));
  assert.ok(contraste('#b3b3b3', '#181818') >= 4.5, contraste('#b3b3b3', '#181818').toFixed(2)); // --sub
});

test('registro: cada tema tem um desenho do seu modelo; os 10 de antes mantêm o desenho aprovado', async () => {
  const { TEMAS, TEMA, DESENHOS, MODELOS } = await import('../../site/app/js/batalha-temas.js');
  assert.deepEqual(Object.keys(DESENHOS), MODELOS);
  for (const t of TEMAS) assert.ok(DESENHOS[t.modelo].includes(t.desenho), `${t.chave}: ${t.desenho} não é de ${t.modelo}`);
  const antes = { horas: 'pista', plays: 'vinil', dia: 'horas24', artistas: 'pontos', musicas: 'estante', sequencia: 'corrente', repeteco: 'tally', fa: 'anel', coruja: 'lua', paciencia: 'casas' };
  for (const [chave, desenho] of Object.entries(antes)) assert.equal(TEMA[chave].desenho, desenho, chave);
  // Fora os 10, cada tema usa o desenho padrão do modelo (6 modelos, como no plano).
  for (const t of TEMAS) if (!antes[t.chave]) assert.equal(t.desenho, DESENHOS[t.modelo][0], t.chave);
  for (const t of TEMAS.filter((x) => x.desenho === 'janela')) {
    const [ini, fim] = t.janela;
    assert.ok(Number.isInteger(ini) && Number.isInteger(fim) && ini >= 0 && fim <= 24 && ini < fim, t.chave);
  }
});
