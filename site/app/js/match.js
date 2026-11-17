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
  const fim = Math.max(...plays.map((i) => c.utc[i]));
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
  const pontuacao = Number(((valor || 0) * 100).toFixed(1)); // toFixed arredonda o binário exato, como o round() do Python
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
