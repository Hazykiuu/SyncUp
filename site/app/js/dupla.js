// Comparação da Dupla em JavaScript, sem Python: as mesmas regras de analise.comparar e metricas.py.
// Entrada: as colunas de historico.lerHistorico para cada pessoa. A paridade com o Python é conferida em
// tests/test_paridade_dupla.py (mesmos arquivos nos dois lados, números com tolerância de 1e-9).
import { compararTexto, iso } from './calculo.js';

export const TEMPO_MINIMO_PLAY_MS = 30_000; // rankings usam plays de pelo menos 30 s; horas usam todas as execuções
const TOP = 20; // top artistas, top músicas e o Jaccard do top 20
const SEP = '\u0000'; // separa música e artista nas chaves compostas

const somar = (mapa, chave, valor = 1) => mapa.set(chave, (mapa.get(chave) || 0) + valor);
// Contagem decrescente; empate pelo nome em ordem de código (como o sort_values do pandas em texto).
const porContagem = ([a, x], [b, y]) => y - x || compararTexto(a, b);
// Mapa em ordem alfabética das chaves: é a ordem do groupby(sort=True) do pandas, e a das somas no Python.
const ordenado = (mapa) => new Map([...mapa].sort(([a], [b]) => compararTexto(a, b)));

// quote(texto, safe='') do Python: só letras, dígitos e _.-~ ficam como estão.
const quote = (texto) => encodeURIComponent(texto).replace(/[!'()*]/g, (c) => `%${c.charCodeAt(0).toString(16).toUpperCase()}`);
export const linkSpotify = (artista, musica = '') => `https://open.spotify.com/search/${quote(`${artista} ${musica}`.trim())}`;

/* ---------- Métricas (metricas.py) ---------- */
export const PONDERACOES = ['bruta', 'raiz', 'log1p'];

export function ponderar(contagens, modo = 'bruta') {
  if (!PONDERACOES.includes(modo)) throw new Error('Ponderação inválida. Use bruta, raiz ou log1p.');
  const f = modo === 'raiz' ? Math.sqrt : modo === 'log1p' ? Math.log1p : (x) => x;
  return new Map([...contagens].map(([k, v]) => [k, f(v)]));
}

// Divide pelo maior peso (ou pelo `maior` dado) para as somas e quadrados não estourarem.
function escalar(valores, maior) {
  const escala = maior ?? Math.max(0, ...valores.values());
  return new Map([...valores].map(([k, v]) => [k, escala ? v / escala : 0]));
}

function prepararCosseno(a, b) {
  const va = escalar(a), vb = escalar(b);
  let na = 0, nb = 0;
  for (const v of va.values()) na += v * v;
  for (const v of vb.values()) nb += v * v;
  return [va, vb, Math.sqrt(na) * Math.sqrt(nb)];
}

export function cosseno(a, b) {
  const [va, vb, denominador] = prepararCosseno(a, b);
  if (!denominador) return null;
  let produto = 0;
  for (const [k, v] of va) if (vb.has(k)) produto += v * vb.get(k);
  return Math.max(0, Math.min(1, produto / denominador));
}

export function jaccard(a, b) {
  const sa = new Set(a), sb = new Set(b);
  const uniao = new Set([...sa, ...sb]);
  let comum = 0;
  for (const x of sa) if (sb.has(x)) comum++;
  return uniao.size ? comum / uniao.size : null;
}

// Ruzicka: soma dos mínimos / soma dos máximos, com o mesmo divisor nos dois perfis.
export function ruzicka(a, b) {
  const escala = Math.max(0, ...a.values(), ...b.values());
  const va = escalar(a, escala), vb = escalar(b, escala);
  let minimo = 0, maximo = 0;
  for (const k of new Set([...va.keys(), ...vb.keys()])) {
    const x = va.get(k) || 0, y = vb.get(k) || 0;
    minimo += Math.min(x, y); maximo += Math.max(x, y);
  }
  return maximo ? minimo / maximo : null;
}

// aᵢ·bᵢ/(|a|·|b|) por artista, em ordem alfabética; a soma é o cosseno.
export function contribuicoes(a, b) {
  const [va, vb, denominador] = prepararCosseno(a, b);
  const nomes = [...new Set([...va.keys(), ...vb.keys()])].sort(compararTexto);
  return nomes.map((k) => [k, denominador ? ((va.get(k) || 0) * (vb.get(k) || 0)) / denominador : 0]);
}

/* ---------- Comparação (analise.comparar) ---------- */
// Índices dos eventos de uma pessoa dentro do período [inicio, fim] (UTC, inclusivo).
const noPeriodo = (c, inicio, fim) => c.utc.reduce((lista, t, i) => (t >= inicio && t <= fim && lista.push(i), lista), []);

function perfil(c, todos, nome) {
  const plays = todos.filter((i) => c.ms[i] >= TEMPO_MINIMO_PLAY_MS);
  const artistas = new Map(), musicas = new Map();
  for (const i of plays) {
    somar(artistas, c.artista[i]);
    somar(musicas, `${c.musica[i]}${SEP}${c.artista[i]}`);
  }
  let ms = 0;
  for (const i of todos) ms += c.ms[i];
  const topMusicas = [...musicas]
    .map(([k, n]) => [...k.split(SEP), n])
    .sort(([m1, a1, x], [m2, a2, y]) => y - x || compararTexto(m1, m2) || compararTexto(a1, a2))
    .slice(0, TOP);
  return {
    nome,
    plays,
    horas: ms / 60000 / 60,
    contagens: ordenado(artistas),
    faixas: musicas,
    topArtistas: [...artistas].sort(porContagem).slice(0, TOP),
    topMusicas,
  };
}

/**
 * Compara duas pessoas. `ca`/`cb`: colunas de lerHistorico. `opcoes`: { comum, ponderacao }.
 * Lança Error com as mesmas mensagens do Python (paridade de erros).
 */
export function compararDupla(ca, cb, nomeA, nomeB, opcoes = {}) {
  const modo = opcoes.ponderacao || 'bruta';
  ponderar(new Map(), modo); // valida antes de calcular
  nomeA = (nomeA || '').trim() || 'Pessoa A';
  nomeB = (nomeB || '').trim() || 'Pessoa B';
  if (!ca.utc.length || !cb.utc.length) throw new Error('Um dos históricos não contém registros de músicas válidos.');
  const comum = opcoes.comum ?? true;
  let ia = ca.utc.map((_, i) => i), ib = cb.utc.map((_, i) => i);
  let periodo = { comum, inicio: null, fim: null };
  if (comum) {
    const min = (c) => c.utc.reduce((m, t) => Math.min(m, t), Infinity);
    const max = (c) => c.utc.reduce((m, t) => Math.max(m, t), -Infinity);
    const inicioUtc = Math.max(min(ca), min(cb)), fimUtc = Math.min(max(ca), max(cb));
    if (inicioUtc > fimUtc) throw new Error('Os históricos não possuem período de cobertura em comum. Desmarque a opção para comparar períodos diferentes.');
    // Hora local do primeiro evento com esse instante (de A, senão de B), como o Python.
    const local = (t) => { const j = ca.utc.indexOf(t); return j >= 0 ? ca.local[j] : cb.local[cb.utc.indexOf(t)]; };
    periodo = { comum, inicio: iso(local(inicioUtc)), fim: iso(local(fimUtc)), inicioUtc, fimUtc };
    ia = noPeriodo(ca, inicioUtc, fimUtc); ib = noPeriodo(cb, inicioUtc, fimUtc);
  }
  const pa = perfil(ca, ia, nomeA), pb = perfil(cb, ib, nomeB);
  if (!pa.plays.length || !pb.plays.length) throw new Error('Não há reproduções de pelo menos 30 segundos para os dois perfis nesse período.');
  const ra = pa.contagens, rb = pb.contagens;
  const pesosA = ponderar(ra, modo), pesosB = ponderar(rb, modo);
  const positivos = (m) => [...m].filter(([, v]) => v > 0).map(([k]) => k);
  const metricas = {
    cosseno: cosseno(pesosA, pesosB),
    jaccard: jaccard(positivos(pesosA), positivos(pesosB)),
    jaccard_top20: jaccard(pa.topArtistas.map(([k]) => k), pb.topArtistas.map(([k]) => k)),
    ruzicka: ruzicka(pesosA, pesosB),
  };
  if (Object.values(metricas).some((v) => v === null)) throw new Error('Não há dados suficientes para calcular as similaridades.');
  // Participação de cada artista nos plays de cada um: ordena os artistas em comum.
  const totalA = pa.plays.length, totalB = pb.plays.length;
  const participacao = (k) => (ra.get(k) || 0) / totalA + (rb.get(k) || 0) / totalB;
  const comuns = [...ra.keys()].filter((k) => rb.has(k)).sort(compararTexto)
    .map((k) => [k, participacao(k)]).sort(([, x], [, y]) => y - x).map(([k]) => k);
  const exclusivos = (r, outro) => [...r].sort(porContagem).filter(([k]) => !outro.has(k)).map(([k]) => k);
  // Playlist comum: faixas (música + artista) dos dois, pelo total de plays; empate por artista e música.
  const playlist = [...pa.faixas].filter(([k]) => pb.faixas.has(k))
    .map(([k, x]) => { const [musica, artista] = k.split(SEP); return [artista, musica, x, pb.faixas.get(k)]; })
    .sort(([a1, m1, x1, y1], [a2, m2, x2, y2]) => x2 + y2 - (x1 + y1) || compararTexto(a1, a2) || compararTexto(m1, m2))
    .map(([artista, musica, x, y]) => [artista, musica, x, y, linkSpotify(artista, musica)]);
  return {
    metricas,
    periodo,
    perfis: [pa, pb].map((p) => ({
      nome: p.nome, plays: p.plays.length, horas: p.horas, artistas: p.contagens.size,
      top_artistas: p.topArtistas, top_musicas: p.topMusicas,
    })),
    comuns,
    so_a: exclusivos(ra, rb),
    so_b: exclusivos(rb, ra),
    // Empate pelo valor com 15 casas (como analise._ordenar_contribuicoes): iguais na matemática, às vezes diferentes no último bit.
    contribuicoes: contribuicoes(pesosA, pesosB).sort(([a, x], [b, y]) => Number(y.toFixed(15)) - Number(x.toFixed(15)) || compararTexto(a, b)),
    playlist,
    ponderacao: modo,
  };
}
