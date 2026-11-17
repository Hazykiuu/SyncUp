// Match no app web: o mesmo cálculo de perfil_gosto.py e conciliacao.py, em JS puro.
// Perfil = rankings (top 50 artistas e músicas em três janelas); compatibilidade = cosseno dos artistas ponderados.
import { compararTexto, TEMPO_MINIMO_PLAY_MS } from './calculo.js';
import { contribuicoes, cosseno, jaccard } from './dupla.js';
import { normalizarNome } from './historico.js';

export const PERIODOS = ['short_term', 'medium_term', 'long_term'];
const JANELAS_DIAS = { short_term: 28, medium_term: 182, long_term: 365 };
const PESO_PERIODO = { short_term: 0.6, medium_term: 0.8, long_term: 1.0 };
const PESO_MUSICAS = 0.5;
export const TAMANHO_RANKING = 50;
const DIA_MS = 86_400_000;

// Faixas calibradas no Python com 4 históricos reais (conciliacao.NIVEIS).
const NIVEIS = [
  [25, 'Sintonia rara', 'Rankings muito parecidos: compartilhar playlists é garantia.'],
  [10, 'Alta compatibilidade', 'Vários favoritos em comum, com espaço para descobertas.'],
  [5, 'Boa compatibilidade', 'Uma base em comum para começar a trocar músicas.'],
  [1, 'Compatibilidade baixa', 'Poucos pontos em comum, mas ótimo para sair da bolha.'],
  [0, 'Mundos diferentes', 'Quase nada em comum nos rankings enviados.'],
];

// Contagem decrescente, depois as chaves em ordem de ponto de código (perfil_gosto._ranking).
function ranking(contagem) {
  const cmp = (x, y) => { for (let k = 0; k < x.length; k++) { const c = compararTexto(x[k], y[k]); if (c) return c; } return 0; };
  return [...contagem.values()].sort((a, b) => b.n - a.n || cmp(a.chaves, b.chaves)).slice(0, TAMANHO_RANKING).map((x) => x.chaves);
}

// Os mesmos rankings que a API devolveria; as janelas terminam no último play, não hoje.
export function perfilDeHistorico(c, nome) {
  if (!c.utc.length) throw new Error(`O histórico de ${nome} não tem músicas válidas.`);
  const plays = [];
  for (let i = 0; i < c.ms.length; i++) if (c.ms[i] >= TEMPO_MINIMO_PLAY_MS) plays.push(i);
  if (!plays.length) throw new Error(`O histórico de ${nome} não tem plays de pelo menos 30 segundos.`);
  let fim = -Infinity; // laço, não Math.max(...): centenas de milhares de argumentos estouram a pilha
  for (const i of plays) if (c.utc[i] > fim) fim = c.utc[i];
  const top_artistas = {}, top_musicas = {};
  for (const p of PERIODOS) {
    const artistas = new Map(), musicas = new Map();
    for (const i of plays) {
      if (!(c.utc[i] > fim - JANELAS_DIAS[p] * DIA_MS)) continue;
      const a = c.artista[i], m = c.musica[i], km = `${m}\u0000${a}`;
      (artistas.get(a) || artistas.set(a, { n: 0, chaves: [a] }).get(a)).n++;
      (musicas.get(km) || musicas.set(km, { n: 0, chaves: [m, a] }).get(km)).n++;
    }
    top_artistas[p] = ranking(artistas).map(([a]) => a);
    top_musicas[p] = ranking(musicas).map(([musica, artista]) => ({ musica, artista }));
  }
  return { nome: (nome || '').trim() || 'Sem nome', fonte: 'historico_zip', top_artistas, top_musicas };
}

// round(x, 1) do Python: meio para o par sobre o valor binário exato. toFixed sobe o meio (6,25 → 6,3) e o Intl
// arredonda o decimal mais curto (6,35 → 6,4); toFixed(60) dá a expansão exata de um valor entre 0 e 100.
export function arredondar1(v) {
  const [int, frac] = v.toFixed(60).split('.');
  const base = Number(`${int}.${frac[0]}`), resto = frac.slice(1);
  const sobe = resto[0] > '5' || (resto[0] === '5' && (/[1-9]/.test(resto.slice(1)) || frac[0] % 2 === 1));
  return sobe ? Number((base + 0.1).toFixed(1)) : base;
}

const pesoPosicao = (i) => Math.max(0, (TAMANHO_RANKING - i + 1) / TAMANHO_RANKING);

export function vetorArtistas(perfil) {
  const pesos = new Map();
  const somar = (k, v) => pesos.set(k, (pesos.get(k) || 0) + v);
  for (const p of PERIODOS) {
    (perfil.top_artistas[p] || []).slice(0, TAMANHO_RANKING).forEach((a, i) => {
      const k = normalizarNome(a);
      if (k) somar(k, PESO_PERIODO[p] * pesoPosicao(i + 1));
    });
    const vistos = new Set();
    (perfil.top_musicas[p] || []).slice(0, TAMANHO_RANKING).forEach((f, i) => {
      const k = normalizarNome(String(f.artista ?? ''));
      if (k && !vistos.has(k)) { vistos.add(k); somar(k, PESO_MUSICAS * PESO_PERIODO[p] * pesoPosicao(i + 1)); }
    });
  }
  return pesos;
}

function nomesExibicao(perfil) {
  const nomes = new Map();
  const guardar = (a) => { const k = normalizarNome(a); if (!nomes.has(k)) nomes.set(k, a); };
  for (const p of PERIODOS) {
    for (const a of perfil.top_artistas[p] || []) guardar(a);
    for (const f of perfil.top_musicas[p] || []) guardar(String(f.artista ?? ''));
  }
  return nomes;
}

function musicasFavoritas(perfil) {
  const s = new Set();
  for (const p of PERIODOS) for (const f of perfil.top_musicas[p] || []) s.add(`${normalizarNome(String(f.musica ?? ''))}\u0000${normalizarNome(String(f.artista ?? ''))}`);
  return s;
}

export function nivel(pontuacao) {
  const n = NIVEIS.find(([limite]) => pontuacao >= limite) || NIVEIS.at(-1);
  return [n[1], n[2]];
}

// Artistas fortes na origem que não aparecem em nenhum ranking do destino.
function recomendar(origem, destino, nomes, n) {
  return [...origem].filter(([k]) => !destino.has(k)).sort(([ka, a], [kb, b]) => b - a || compararTexto(ka, kb))
    .slice(0, n).map(([k]) => nomes.get(k) ?? k);
}

// Sem gêneros no navegador (dependem do MusicBrainz): o eixo de estilo fica de fora.
export function compararPerfis(a, b, nExemplos = 8) {
  const va = vetorArtistas(a), vb = vetorArtistas(b);
  const valor = va.size && vb.size ? cosseno(va, vb) : null;
  const pontuacao = arredondar1((valor || 0) * 100);
  const na = nomesExibicao(a), nb = nomesExibicao(b);
  const nomes = new Map([...nb, ...na]);
  const contrib = va.size && vb.size ? contribuicoes(va, vb) : [];
  const comuns = contrib.filter(([, v]) => v > 0).sort(([ka, x], [kb, y]) => y - x || compararTexto(ka, kb)).map(([k]) => nomes.get(k) ?? k);
  const [rotulo, frase] = nivel(pontuacao);
  const fb = musicasFavoritas(b);
  return {
    a: a.nome, b: b.nome, pontuacao, nivel: rotulo, descricao: frase,
    artistas_comuns: comuns,
    musicas_comuns: [...musicasFavoritas(a)].filter((m) => fb.has(m)).length,
    jaccard_artistas: jaccard(va.keys(), vb.keys()) || 0,
    recomendacoes_para_a: recomendar(vb, va, nb, nExemplos),
    recomendacoes_para_b: recomendar(va, vb, na, nExemplos),
  };
}

export const MAXIMO_PESSOAS = 16;
// Chave de um par em `detalhes` (a ordem dos dois nomes não importa).
export const chave = (x, y) => [x, y].sort(compararTexto).join('\u0000');

// (total, -índices em ordem) como chave de desempate, igual ao max() do Python (o primeiro máximo fica).
function maior(x, y) {
  if (x[0] !== y[0]) return x[0] > y[0];
  const a = x[1].flat().map((k) => -k), b = y[1].flat().map((k) => -k);
  for (let i = 0; i < a.length && i < b.length; i++) if (a[i] !== b[i]) return a[i] > b[i];
  return a.length > b.length;
}
const melhorDe = (opcoes) => opcoes.reduce((m, o) => (maior(o, m) ? o : m));

// Grupos que maximizam a soma das compatibilidades (conciliacao.emparelhamento_otimo): exato, até 16 pessoas.
// Com número ímpar, um trio vale a média dos seus três pares.
export function emparelhamentoOtimo(nomes, valores) {
  const n = nomes.length;
  if (n < 2) return n ? [nomes.slice()] : [];
  const memo = new Map();
  const melhor = (restantes) => {
    if (restantes === 0) return [0, []];
    if (memo.has(restantes)) return memo.get(restantes);
    const i = 31 - Math.clz32(restantes & -restantes); // primeiro índice livre
    const semI = restantes & ~(1 << i);
    const opcoes = [];
    for (let bits = semI; bits; bits &= bits - 1) {
      const j = 31 - Math.clz32(bits & -bits);
      const [total, pares] = melhor(semI & ~(1 << j));
      opcoes.push([total + valores[i][j], [[i, j], ...pares]]);
    }
    const r = melhorDe(opcoes);
    memo.set(restantes, r);
    return r;
  };
  const todos = (1 << n) - 1;
  let grupos;
  if (n % 2 === 0) grupos = melhor(todos)[1];
  else {
    const opcoes = [];
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) for (let k = j + 1; k < n; k++) {
      const [total, pares] = melhor(todos & ~((1 << i) | (1 << j) | (1 << k)));
      opcoes.push([total + (valores[i][j] + valores[i][k] + valores[j][k]) / 3, [...pares, [i, j, k]]]);
    }
    grupos = melhorDe(opcoes)[1];
  }
  return [...grupos].sort((a, b) => Math.min(...a) - Math.min(...b)).map((g) => g.map((k) => nomes[k]));
}

// Todos contra todos, pares ótimos e o ranking de cada pessoa (conciliacao.conciliar).
export function conciliar(perfis) {
  if (perfis.length < 2) throw new Error('Adicione pelo menos duas pessoas para conciliar.');
  if (perfis.length > MAXIMO_PESSOAS) throw new Error(`Use no máximo ${MAXIMO_PESSOAS} pessoas por conciliação.`);
  const nomes = perfis.map((p) => p.nome);
  if (new Set(nomes).size !== nomes.length) throw new Error('Cada pessoa precisa de um nome diferente.');
  const matriz = nomes.map(() => nomes.map(() => 100));
  const detalhes = {}; // sem funções no resultado: ele atravessa o postMessage do Worker
  for (let i = 0; i < perfis.length; i++) for (let j = i + 1; j < perfis.length; j++) {
    const c = compararPerfis(perfis[i], perfis[j]);
    detalhes[chave(nomes[i], nomes[j])] = c;
    matriz[i][j] = matriz[j][i] = c.pontuacao;
  }
  const pares = emparelhamentoOtimo(nomes, matriz);
  const pontuacoes = pares.flatMap((g) => g.flatMap((x, a) => g.slice(a + 1).map((y) => detalhes[chave(x, y)].pontuacao)));
  const melhores = Object.fromEntries(nomes.map((nome, i) => [nome,
    nomes.map((outro, j) => [outro, matriz[i][j]]).filter((_, j) => j !== i).sort(([na, a], [nb, b]) => b - a || compararTexto(na, nb))]));
  return {
    nomes, matriz, pares, detalhes, melhores,
    pontuacao_media_pares: pontuacoes.length ? pontuacoes.reduce((s, v) => s + v, 0) / pontuacoes.length : 0,
  };
}

// O par formado de maior nota (em trio, o melhor dos três pares): o "casal do grupo" do pôster.
// Empate: o que vem primeiro na lista de pares.
export function melhorPar(r) {
  let melhor = null;
  for (const g of r.pares) for (let a = 0; a < g.length; a++) for (let b = a + 1; b < g.length; b++) {
    const c = r.detalhes[chave(g[a], g[b])];
    if (!melhor || c.pontuacao > melhor[2].pontuacao) melhor = [g[a], g[b], c];
  }
  return melhor;
}

// Trilha dos stories (o formato de som.js): cada par toca o artista que mais os une; o pôster, o do casal do grupo.
// Só nomes de artistas em comum vão ao iTunes.
export function trilhaMatch(r) {
  const comum = (x, y) => r.detalhes[chave(x, y)].artistas_comuns.slice(0, 1).map((artista) => ({ artista }));
  const [x, y] = melhorPar(r);
  const slides = {
    abertura: comum(x, y),
    ...Object.fromEntries(r.pares.map((g, n) => [`par-${n}`, comum(g[0], g[1])])),
    poster: comum(x, y),
  };
  const fila = [...new Set(r.pares.flatMap((g) => r.detalhes[chave(g[0], g[1])].artistas_comuns.slice(0, 3)))].map((artista) => ({ artista }));
  return { slides: Object.fromEntries(Object.entries(slides).filter(([, c]) => c.length)), fila };
}
