// Batalha (no app web, no lugar do Grupo do app para PC): de 3 a 6 históricos disputam rodadas de números do período.
// Funções puras: o Worker (batalha-worker.js) lê os arquivos e chama numerosDoLutador e montarBatalha.
import { medidasNovas, numerosDoGrupo } from './batalha-medidas.js';
import { ausente, OPOSTOS, TEMA, TEMAS } from './batalha-temas.js';
import { calcularWrapped, compararTexto, MINIMO_PLAYS_WRAPPED, TEMPO_MINIMO_PLAY_MS } from './calculo.js';
import { cosseno, ponderar } from './dupla.js';

// Verde e violeta são os da Dupla; texto sobre elas é sempre preto (teste de contraste em batalha.test.mjs).
export const CORES = ['#1ed760', '#c4b7ff', '#f573a0', '#ffa42b', '#5cb8ff', '#f5d547'];

// Todas as métricas são ≥ 0: Math.round basta (sem o caso do .5 negativo).
export const arredondar = (v, casas) => Math.round(v * 10 ** casas) / 10 ** casas;

export function validarNomes(nomes) {
  if (nomes.length < 3 || nomes.length > 6) throw new Error('A Batalha precisa de 3 a 6 pessoas.');
  const limpos = nomes.map((n, i) => (n || '').trim() || `Pessoa ${i + 1}`);
  if (new Set(limpos).size !== limpos.length) throw new Error('Use nomes diferentes para identificar cada pessoa da batalha.');
  return limpos;
}

// Recorte comum (analise.comparar_grupo): do maior início ao menor fim, em UTC.
export function janelaComum(faixas) {
  const inicio = Math.max(...faixas.map(([i]) => i)), fim = Math.min(...faixas.map(([, f]) => f));
  if (inicio > fim) throw new Error('Não há período comum a todo o grupo. Desmarque o recorte comum.');
  return [inicio, fim];
}

export function recortar(c, inicio, fim) {
  const dentro = [];
  for (let i = 0; i < c.utc.length; i++) if (c.utc[i] >= inicio && c.utc[i] <= fim) dentro.push(i);
  return Object.fromEntries(Object.entries(c).map(([k, v]) => [k, Array.isArray(v) ? dentro.map((i) => v[i]) : v]));
}

// Os números de todos os temas que não dependem do grupo, de um histórico já recortado, e o resumo para os
// temas do grupo: plays por artista (também para a dupla afinada) e o início do primeiro play de cada artista (UTC).
export function numerosDoLutador(c, nome, fuso) {
  const contagens = new Map(), primeiros = new Map();
  for (let i = 0; i < c.ms.length; i++) {
    if (c.ms[i] < TEMPO_MINIMO_PLAY_MS) continue;
    const art = c.artista[i], inicio = c.utc[i] - c.ms[i];
    contagens.set(art, (contagens.get(art) || 0) + 1);
    if (!(primeiros.get(art) <= inicio)) primeiros.set(art, inicio);
  }
  if (!contagens.size) throw new Error(`Não há plays ≥30s para ${nome} no período escolhido. Tente desmarcar o recorte comum.`);
  const d = calcularWrapped(c, nome, fuso);
  return {
    numeros: {
      horas: d.horas, plays: d.plays, artistas: d.quantidade_artistas, musicas: d.quantidade_musicas,
      sequencia: d.sequencia, dia: d.horas_dia_recorde, coruja: d.periodos.Madrugada * 100,
      repeteco: d.repeticao_dia.plays, fa: d.participacao_artista_vida * 100,
      paciencia: d.habitos.pulos === null ? null : d.habitos.pulos * 100,
      ...medidasNovas(c, d, contagens),
    },
    contagens: new Map([...contagens].sort(([a], [b]) => compararTexto(a, b))),
    primeiros,
  };
}

// Posição olímpica: 1 + quantos têm valor estritamente melhor (empate divide a posição).
export const posicoes = (valores, menor) => valores.map((v) => 1 + valores.filter((x) => (menor ? x < v : x > v)).length);

// Os temas do registro que dão para todos. `fora`: { chave, titulo, tipo: 'dado' | 'vazio' | 'empate', motivo }.
// undefined = tema que estes números não trazem (fica de fora calado); null = dado ausente (sai com o motivo).
export function rodadas(lutadores) {
  const dentro = [], fora = [];
  for (const t of TEMAS) {
    const brutos = lutadores.map((l) => l.numeros[t.chave]);
    if (brutos.every((v) => v === undefined)) continue;
    const sai = (tipo, motivo) => fora.push({ chave: t.chave, titulo: t.titulo, tipo, motivo });
    if (brutos.some((v) => v === null || v === undefined)) { sai('dado', ausente(t)); continue; }
    if (t.pct && lutadores.some((l) => l.numeros.plays < MINIMO_PLAYS_WRAPPED)) { sai('dado', `alguém tem menos de ${MINIMO_PLAYS_WRAPPED} plays de 30 s`); continue; }
    const valores = brutos.map((v) => arredondar(v, t.casas));
    if (!t.menor && valores.every((v) => v <= (t.minimo ?? 0))) { sai('vazio', t.vazio); continue; }
    if (valores.every((v) => v === valores[0])) { sai('empate', 'todos empataram'); continue; }
    dentro.push({ chave: t.chave, titulo: t.titulo, unidade: t.unidade, casas: t.casas, menor: !!t.menor, valores, posicoes: posicoes(valores, t.menor) });
  }
  return { dentro, fora };
}

// mulberry32: o mesmo sorteio para a mesma semente, sem Math.random.
function gerador(semente) {
  let a = semente >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), a | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export const RODADAS_POR_BATALHA = 10;
const POR_FAMILIA = 2;
const OPOSTO = new Map(OPOSTOS.flatMap(([a, b]) => [[a, b], [b, a]]));
// Embaralha os elegíveis e escolhe em três passadas, cada uma relaxando uma regra: 1) sem os temas de `evitar`
// (a batalha anterior) e no máximo 2 por família; 2) volta a batalha anterior; 3) passa do teto por família.
// Par oposto nunca. Devolve as rodadas na ordem do registro.
export function sortear(dentro, { semente, evitar = [] }) {
  const sorte = gerador(semente), lista = [...dentro];
  for (let i = lista.length - 1; i > 0; i--) {
    const j = Math.floor(sorte() * (i + 1));
    [lista[i], lista[j]] = [lista[j], lista[i]];
  }
  const anterior = new Set(evitar), escolhidos = new Set(), familias = new Map();
  for (const passada of [1, 2, 3]) {
    for (const { chave } of lista) {
      if (escolhidos.size === RODADAS_POR_BATALHA) break;
      const { familia } = TEMA[chave];
      if (escolhidos.has(chave) || escolhidos.has(OPOSTO.get(chave))) continue;
      if (passada === 1 && anterior.has(chave)) continue;
      if (passada < 3 && (familias.get(familia) || 0) >= POR_FAMILIA) continue;
      escolhidos.add(chave);
      familias.set(familia, (familias.get(familia) || 0) + 1);
    }
  }
  return dentro.filter((r) => escolhidos.has(r.chave));
}

export function medalhas(lista) {
  const m = lista[0].posicoes.map(() => ({ ouro: 0, prata: 0, bronze: 0 }));
  for (const { posicoes: p } of lista) p.forEach((pos, i) => { const tipo = ['ouro', 'prata', 'bronze'][pos - 1]; if (tipo) m[i][tipo]++; });
  return m;
}

const comparar = (a, b) => b.ouro - a.ouro || b.prata - a.prata || b.bronze - a.bronze;
export function campeoes(m) {
  const melhor = [...m].sort(comparar)[0];
  return m.map((x, i) => (comparar(x, melhor) === 0 ? i : -1)).filter((i) => i >= 0);
}

// Maior cosseno log1p (o mais estável no estudo com históricos reais), em % com 1 casa; empate: mais artistas em comum,
// depois os nomes em ordem. `menosAfinada` é a ponta oposta da mesma ordem (desempates invertidos).
// `artistaComum`: o artista que mais une o par, pelo menor dos dois plays (500 x 1 não une; 80 x 80 une).
export function maisAfinada(contagens, nomes) {
  const pares = [];
  for (let i = 0; i < contagens.length; i++) {
    for (let j = i + 1; j < contagens.length; j++) {
      const valor = arredondar((cosseno(ponderar(contagens[i], 'log1p'), ponderar(contagens[j], 'log1p')) ?? 0) * 100, 1);
      let comuns = 0;
      for (const k of contagens[i].keys()) if (contagens[j].has(k)) comuns++;
      pares.push({ par: [i, j], valor, comuns, nomes: [nomes[i], nomes[j]].sort(compararTexto) });
    }
  }
  pares.sort((a, b) => b.valor - a.valor || b.comuns - a.comuns || compararTexto(a.nomes[0], b.nomes[0]) || compararTexto(a.nomes[1], b.nomes[1]));
  const { par, valor, comuns } = pares[0];
  const [ca, cb] = par.map((i) => contagens[i]);
  let artistaComum = null, melhor = 0;
  for (const [k, n] of ca) {
    const juntos = Math.min(n, cb.get(k) ?? 0);
    if (juntos > melhor || (juntos === melhor && juntos > 0 && compararTexto(k, artistaComum) < 0)) { artistaComum = k; melhor = juntos; }
  }
  const ultimo = pares[pares.length - 1];
  return { par, valor, comuns, artistaComum, menosAfinada: { par: ultimo.par, valor: ultimo.valor, comuns: ultimo.comuns } };
}

/* ---------- Disputa e narrativa (adendo de 16/11) ---------- */
const FOLGA = 1e-9; // 5% "exatos" não podem falhar por ponto flutuante

// 'por-um-triz' (diferença ≤ 5%), 'massacre' (o dobro) ou null. Só com um único 1º e um 2º acima de zero.
export function destaqueRodada(r) {
  const unico = r.posicoes.filter((p) => p === 1).length === 1;
  const primeiro = r.valores[r.posicoes.indexOf(1)];
  const segundos = r.valores.filter((_, i) => r.posicoes[i] === 2);
  if (!unico || !segundos.length || !(segundos[0] > 0)) return null;
  const segundo = segundos[0];
  if (r.menor) {
    if ((segundo - primeiro) / segundo <= 0.05 + FOLGA) return 'por-um-triz';
    return primeiro > 0 && segundo >= primeiro * 2 - FOLGA ? 'massacre' : null;
  }
  if ((primeiro - segundo) / primeiro <= 0.05 + FOLGA) return 'por-um-triz';
  return primeiro >= segundo * 2 - FOLGA ? 'massacre' : null;
}

// Paciência ou Dedo nervoso: quem mais pula, se for um só e pular mais de 60% das músicas ("Dedinho nervoso").
export function alertaPaciencia(r, nomes) {
  if (r.chave !== 'paciencia' && r.chave !== 'dedo') return null;
  const pior = Math.max(...r.valores);
  const quem = r.valores.map((v, i) => (v === pior ? i : -1)).filter((i) => i >= 0);
  return quem.length === 1 && pior > 60 ? { nome: nomes[quem[0]], valor: pior } : null;
}

// Título de classe do campeão único, pela primeira combinação de ouros que bater.
const TITULOS = [
  [['coruja', 'dia'], 'Insone Oficial'],
  [['repeteco', 'fa'], 'Modo Obsessão'],
  [['artistas', 'musicas'], 'Enciclopédia Musical'],
  [['horas', 'plays'], 'Trator de Plays'],
];
export function tituloCampeao(b) {
  if (b.campeoes.length !== 1) return null;
  const c = b.campeoes[0];
  const ouros = new Set(b.rodadas.filter((r) => r.posicoes[c] === 1).map((r) => r.chave));
  return TITULOS.find(([chaves]) => chaves.every((k) => ouros.has(k)))?.[1] ?? 'Dono(a) do Aux';
}

// Campeão único que venceu por 1 ouro, ou empatado em ouros e decidido na prata.
export function decididoNoDetalhe(b) {
  if (b.campeoes.length !== 1) return false;
  const c = b.lutadores[b.campeoes[0]].medalhas;
  const vice = b.lutadores.filter((_, i) => i !== b.campeoes[0]).map((l) => l.medalhas)
    .sort((x, y) => y.ouro - x.ouro || y.prata - x.prata || y.bronze - x.bronze)[0];
  return c.ouro - vice.ouro === 1 || (c.ouro === vice.ouro && c.prata !== vice.prata);
}

const NOME_SELO = { 'por-um-triz': 'Por um triz', massacre: 'Massacre' };
// Até 3 fatos da partida: o campeão, um selo (massacre antes de por um triz) e a dupla menos afinada.
export function resenha(b, nomes) {
  const e = (lista) => lista.join(lista.length > 2 ? ', ' : ' e ').replace(/, ([^,]*)$/, ' e $1');
  const fatos = [b.campeoes.length === 1
    ? `${nomes[b.campeoes[0]]} levou a batalha como ${b.titulo}.`
    : `Empate no topo entre ${e(b.campeoes.map((i) => nomes[i]))}.`];
  const selo = b.rodadas.find((r) => r.destaque === 'massacre') || b.rodadas.find((r) => r.destaque === 'por-um-triz');
  if (selo) fatos.push(`${NOME_SELO[selo.destaque]} em ${selo.titulo}: ${nomes[selo.posicoes.indexOf(1)]} venceu ${selo.destaque === 'massacre' ? 'com folga' : 'por pouco'}.`);
  const [x, y] = b.menosAfinada.par;
  fatos.push(`${nomes[x]} e ${nomes[y]} têm o gosto mais distante (${String(b.menosAfinada.valor).replace('.', ',')}% de escuta em comum, pelo cosseno).`);
  return fatos.join(' ');
}

// Artista mais tocado de cada um (empate: ordem de ponto de código).
export function favorito(contagens) {
  let melhor = null, n = 0;
  for (const [k, v] of contagens) if (v > n || (v === n && compararTexto(k, melhor) < 0)) { melhor = k; n = v; }
  return melhor;
}

// Trilha dos stories (o mesmo formato da Dupla, lido por som.js): cada rodada toca o favorito de quem venceu,
// a dupla afinada o artista que une os dois e o pódio o favorito do campeão. Só nomes de artistas vão ao iTunes.
export function trilhaBatalha(b, favoritos) {
  const de = (i) => (favoritos[i] ? [{ artista: favoritos[i] }] : []);
  const slides = {
    abertura: b.afinada.artistaComum ? [{ artista: b.afinada.artistaComum }] : de(b.campeoes[0]),
    ...Object.fromEntries(b.rodadas.map((r) => [`rodada-${r.chave}`, de(r.posicoes.indexOf(1))])),
    afinada: b.afinada.artistaComum ? [{ artista: b.afinada.artistaComum }] : [],
    medalhas: favoritos.flatMap((_, i) => de(i)),
    podio: de(b.campeoes[0]),
  };
  return {
    slides: Object.fromEntries(Object.entries(slides).filter(([, c]) => c.length)),
    fila: [...new Set(favoritos.filter(Boolean))].map((artista) => ({ artista })),
  };
}

// `lutadores`: [{ nome, numeros, contagens, primeiros? }] na ordem do formulário. `semente` e `evitar` (os temas da
// batalha anterior) vêm da tela. Devolve o JSON da tela, com a semente e os temas sorteados.
export function montarBatalha(lutadores, { semente = 1, evitar = [] } = {}) {
  const grupo = numerosDoGrupo(lutadores);
  lutadores = lutadores.map((l, i) => ({ ...l, numeros: { ...l.numeros, ...grupo[i] } }));
  const { dentro: elegiveis, fora } = rodadas(lutadores);
  if (!elegiveis.length) throw new Error('Não há números suficientes para uma batalha neste período.');
  const dentro = sortear(elegiveis, { semente, evitar });
  const nomes = lutadores.map((l) => l.nome);
  const m = medalhas(dentro);
  const { menosAfinada, ...afinada } = maisAfinada(lutadores.map((l) => l.contagens), nomes);
  const b = {
    semente,
    temas: dentro.map((r) => r.chave),
    lutadores: lutadores.map((l, i) => ({ nome: l.nome, cor: CORES[i], medalhas: m[i] })),
    rodadas: dentro.map((r) => ({ ...r, destaque: destaqueRodada(r), alerta: alertaPaciencia(r, nomes) })),
    fora,
    campeoes: campeoes(m),
    afinada,
    menosAfinada,
  };
  b.titulo = tituloCampeao(b);
  b.detalhe = decididoNoDetalhe(b);
  b.resenha = resenha(b, nomes);
  b.trilha = trilhaBatalha(b, lutadores.map((l) => favorito(l.contagens)));
  return b;
}
