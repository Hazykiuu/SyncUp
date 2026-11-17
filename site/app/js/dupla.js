// Comparação da Dupla em JavaScript, sem Python: as mesmas regras de analise.comparar e metricas.py.
// Entrada: as colunas de historico.lerHistorico para cada pessoa. A paridade com o Python é conferida em
// tests/test_paridade_dupla.py (mesmos arquivos nos dois lados, números com tolerância de 1e-9).
import { compararTexto, DIAS_SEMANA, iso, TEMPO_MINIMO_PLAY_MS } from './calculo.js';
import { normalizarNome } from './historico.js';

const TOP = 20; // top artistas e top músicas exibidos
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

// Rank-biased overlap extrapolado (Webber et al., 2010) nos tops de k, como metricas.rbo: o topo pesa mais.
// As duas listas são cortadas na mesma profundidade (a menor, até k); lista vazia devolve null.
export function rbo(a, b, p = 0.9, k = 50) {
  k = Math.min(k, a.length, b.length);
  if (!k) return null;
  const va = new Set(), vb = new Set();
  let soma = 0, acordo = 0;
  for (let d = 1; d <= k; d++) {
    const x = a[d - 1], y = b[d - 1];
    if (x === y) acordo += 1;
    else acordo += (vb.has(x) ? 1 : 0) + (va.has(y) ? 1 : 0);
    va.add(x); vb.add(y);
    soma += (acordo / d) * p ** d;
  }
  return (acordo / k) * p ** k + ((1 - p) / p) * soma;
}
const PROFUNDIDADE_RBO = 50; // "Favoritos em comum" (analise.PROFUNDIDADE_RBO)
const rankingArtistas = (contagens) => [...contagens].sort(porContagem).slice(0, PROFUNDIDADE_RBO).map(([k]) => k);

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

/* ---------- Diversidade (metricas.entropia_normalizada e gini) ---------- */
export function entropia(contagens) {
  let valores = [...contagens.values()].filter((x) => x > 0);
  if (!valores.length) return null;
  if (valores.length === 1) return 0;
  const escala = Math.max(...valores);
  valores = valores.map((x) => x / escala);
  const total = valores.reduce((s, x) => s + x, 0);
  let soma = 0;
  for (const x of valores) if (x > 0) soma += (x / total) * Math.log(x / total);
  return Math.min(1, Math.max(0, -soma / Math.log(valores.length)));
}

export function gini(contagens) {
  let valores = [...contagens.values()].filter((x) => x > 0).sort((a, b) => a - b);
  if (!valores.length) return null;
  const escala = Math.max(...valores);
  valores = valores.map((x) => x / escala);
  const k = valores.length;
  let num = 0, total = 0;
  valores.forEach((x, i) => { num += (2 * (i + 1) - k - 1) * x; total += x; });
  return Math.max(0, Math.min(1, num / (k * total)));
}

/* ---------- Estatísticas (describe() do pandas, minutos por execução) ---------- */
// count, mean, std (n − 1), min, 25%, 50%, 75%, max; quantis com interpolação linear, como o pandas.
export function descrever(valores) {
  const n = valores.length, v = [...valores].sort((a, b) => a - b);
  const media = valores.reduce((s, x) => s + x, 0) / n;
  const desvio = n > 1 ? Math.sqrt(valores.reduce((s, x) => s + (x - media) ** 2, 0) / (n - 1)) : NaN;
  const quantil = (q) => { const pos = (n - 1) * q, i = Math.floor(pos); return i + 1 < n ? v[i] + (v[i + 1] - v[i]) * (pos - i) : v[i]; };
  return [n, media, desvio, v[0], quantil(0.25), quantil(0.5), quantil(0.75), v[n - 1]];
}

/* ---------- Quase juntos (recursos.momentos_sincronizados) ---------- */
const JANELA_MS = 3_600_000; // 1 h
const MAXIMO_EXEMPLOS = 200;
const utcIso = (ms) => `${new Date(ms).toISOString().slice(0, 19)}+00:00`; // Timestamp UTC do pandas
const localTexto = (ms) => new Date(ms).toISOString().slice(0, 19).replace('T', ' '); // str() de Timestamp sem fuso

// Pares um a um de eventos com o mesmo artista (ou a mesma música do mesmo artista) a até 1 h de distância.
// Por chave, em ordem alfabética (artista, depois música), dois ponteiros pelos instantes: o máximo de pares.
export function momentosSincronizados(ca, ia, cb, ib, tipo) {
  const chave = (c, i) => (tipo === 'artista' ? c.artista[i] : `${c.artista[i]}${SEP}${c.musica[i]}`);
  const grupos = (c, idx) => {
    const m = new Map();
    for (const i of idx) { const k = chave(c, i); (m.get(k) || m.set(k, []).get(k)).push(i); }
    for (const lista of m.values()) lista.sort((x, y) => c.utc[x] - c.utc[y]); // estável: empate na ordem do arquivo
    return m;
  };
  const ga = grupos(ca, ia), gb = grupos(cb, ib);
  const porNome = (x, y) => { const [a1, m1 = ''] = x.split(SEP), [a2, m2 = ''] = y.split(SEP); return compararTexto(a1, a2) || compararTexto(m1, m2); };
  const chaves = [...ga.keys()].filter((k) => gb.has(k)).sort(porNome);
  let total = 0;
  const exemplos = [];
  for (const k of chaves) {
    const la = ga.get(k), lb = gb.get(k);
    let i = 0, j = 0;
    while (i < la.length && j < lb.length) {
      const x = la[i], y = lb[j], d = ca.utc[x] - cb.utc[y];
      if (d < -JANELA_MS) i++;
      else if (d > JANELA_MS) j++;
      else {
        total++;
        if (exemplos.length < MAXIMO_EXEMPLOS) {
          exemplos.push([ca.artista[x], ca.musica[x], cb.musica[y], utcIso(ca.utc[x]), utcIso(cb.utc[y]),
            localTexto(ca.local[x]), localTexto(cb.local[y]), Math.abs(d) / 60000]);
        }
        i++; j++;
      }
    }
  }
  return { total_pares: total, exemplos };
}

/* ---------- Sintonia (recursos.escutas e sintonia_entre) ---------- */
const MINIMO_JUNTOS_MS = 30_000;
// normalizar_nome; se sobrar vazio (só pontuação), o nome em casefold.
const normal = (n) => normalizarNome(n) || n.toUpperCase().toLowerCase();

// Cada play vira [fim − duração, fim]; plays sobrepostos da mesma faixa (nomes normalizados) se unem.
// Nomes e fuso de cada intervalo vêm do 1º play dele.
function escutas(c, idx) {
  const porFaixa = new Map();
  for (const i of idx) {
    if (!(c.ms[i] > 0)) continue;
    const faixa = `${normal(c.artista[i])}${SEP}${normal(c.musica[i])}`;
    (porFaixa.get(faixa) || porFaixa.set(faixa, []).get(faixa)).push({ inicio: c.utc[i] - c.ms[i], fim: c.utc[i], i });
  }
  const saida = new Map();
  for (const [faixa, lista] of porFaixa) {
    lista.sort((x, y) => x.inicio - y.inicio);
    const unidos = [];
    let maiorFim = -Infinity;
    for (const p of lista) {
      if (!unidos.length || p.inicio > maiorFim) unidos.push({ inicio: p.inicio, fim: p.fim, i: p.i });
      else unidos.at(-1).fim = Math.max(unidos.at(-1).fim, p.fim);
      maiorFim = Math.max(maiorFim, p.fim);
    }
    saida.set(faixa, unidos);
  }
  return saida;
}

// Momentos em que os dois tocavam a mesma faixa ao mesmo tempo (≥ 30 s juntos). Os intervalos de cada
// pessoa numa faixa não se sobrepõem: cada um cruza no máximo o último do outro que começou antes dele
// (B com o último A que começou até ele; A com o último B que começou antes dele).
function sintoniaEntre(ca, ia, cb, ib) {
  const ea = escutas(ca, ia), eb = escutas(cb, ib);
  const pares = [], segundos = [];
  const ultimoAte = (lista, t, estrito) => { let r = null; for (const x of lista) { if (estrito ? x.inicio < t : x.inicio <= t) r = x; else break; } return r; };
  for (const [faixa, la] of ea) {
    const lb = eb.get(faixa);
    if (!lb) continue;
    for (const b of lb) { const a = ultimoAte(la, b.inicio, false); if (a) pares.push([a, b]); }
    for (const a of la) { const b = ultimoAte(lb, a.inicio, true); if (b) segundos.push([a, b]); }
  }
  // Ordem do Python: primeiro as buscas pelo início de B, depois as pelo início de A; no fim, pelo início juntos.
  pares.sort(([, x], [, y]) => x.inicio - y.inicio);
  segundos.sort(([x], [y]) => x.inicio - y.inicio);
  let quase = 0;
  const momentos = [];
  for (const [a, b] of [...pares, ...segundos]) {
    const inicio = Math.max(a.inicio, b.inicio), duracao = Math.min(a.fim, b.fim) - inicio;
    if (duracao >= MINIMO_JUNTOS_MS) {
      momentos.push({ artista: ca.artista[a.i], musica: ca.musica[a.i], inicio, local: inicio + (ca.local[a.i] - ca.utc[a.i]), minutos: duracao / 60000 });
    } else if (-duracao <= JANELA_MS) quase++;
  }
  momentos.sort((x, y) => x.inicio - y.inicio);
  return { momentos, quase };
}

const doisDigitos = (n) => String(n).padStart(2, '0');

// O mesmo JSON de ponte._sintonia_json. `quaseMusicas`: total de "quase juntos" da mesma música.
function sintoniaJson({ momentos }, quaseMusicas) {
  const momento = (m) => m && { musica: m.musica, artista: m.artista, data: iso(Math.floor(m.local / 1000) * 1000), minutos: m.minutos };
  if (!momentos.length) {
    return { minutos: 0, momentos: 0, quase: quaseMusicas, primeira: null, mais_longo: null, musica: null, hora_favorita: null, dia_favorito: null, por_mes: [] };
  }
  let minutos = 0;
  const porMes = new Map(), porHora = new Map(), porDia = new Map(), porMusica = new Map();
  for (const m of momentos) {
    minutos += m.minutos;
    const d = new Date(m.local);
    somar(porMes, d.toISOString().slice(0, 7), m.minutos);
    somar(porHora, d.getUTCHours(), m.minutos);
    somar(porDia, (d.getUTCDay() + 6) % 7, m.minutos); // segunda = 0, como o dayofweek do pandas
    const k = `${m.musica}${SEP}${m.artista}`;
    const g = porMusica.get(k) || porMusica.set(k, { vezes: 0, minutos: 0 }).get(k);
    g.vezes++; g.minutos += m.minutos;
  }
  const maior = (mapa) => [...mapa].sort(([a], [b]) => a - b).reduce((x, y) => (y[1] > x[1] ? y : x))[0]; // idxmax: o 1º maior
  const [topo] = [...porMusica].map(([k, g]) => [...k.split(SEP), g])
    .sort(([m1, a1, g1], [m2, a2, g2]) => g2.minutos - g1.minutos || compararTexto(m1, m2) || compararTexto(a1, a2));
  const longo = momentos.reduce((x, y) => (y.minutos > x.minutos ? y : x)); // empate: o mais antigo
  // Meses sem sintonia entram com zero, do primeiro ao último.
  const meses = [...porMes.keys()].sort();
  const serie = [];
  let [ano, mes] = meses[0].split('-').map(Number);
  for (let chave = meses[0]; chave <= meses.at(-1); chave = `${ano}-${doisDigitos(mes)}`) {
    serie.push([chave, porMes.get(chave) || 0]);
    if (++mes > 12) { mes = 1; ano++; }
  }
  return {
    minutos, momentos: momentos.length, quase: quaseMusicas,
    primeira: momento(momentos[0]), mais_longo: momento(longo),
    musica: { nome: topo[0], artista: topo[1], vezes: topo[2].vezes, minutos: topo[2].minutos },
    hora_favorita: maior(porHora), dia_favorito: DIAS_SEMANA[maior(porDia)], por_mes: serie,
  };
}

/* ---------- Ponte musical (recursos.ponte_musical) ---------- */
const MAXIMO_PONTE = 10;
function ponte(ra, rb, nomeA, nomeB) {
  const linhas = [];
  for (const [origem, destino, de, para] of [[ra, rb, nomeA, nomeB], [rb, ra, nomeB, nomeA]]) {
    let total = 0;
    for (const v of origem.values()) total += v;
    // Ordem alfabética do mapa + ordenação estável: empate pelo nome, como o pandas.
    const exclusivos = [...origem].filter(([k]) => !destino.has(k)).sort(([, x], [, y]) => y - x).slice(0, MAXIMO_PONTE);
    for (const [artista, plays] of exclusivos) linhas.push([de, para, artista, plays, (plays / total) * 100, linkSpotify(artista)]);
  }
  return linhas;
}

/* ---------- Diagnóstico dos arquivos (analise._diagnostico) ---------- */
const hex = (buffer) => [...new Uint8Array(buffer)].map((b) => b.toString(16).padStart(2, '0')).join('');
const sha256 = async (bytes) => hex(await crypto.subtle.digest('SHA-256', bytes));

// SHA-256 e nome do que uma pessoa enviou, como dados.carregar_historicos: com várias partes, o resumo
// combina os SHA das partes na ordem (não os nomes). `arquivos`: [{ nome, bytes }].
export async function identificar(arquivos) {
  const shas = await Promise.all(arquivos.map((a) => sha256(a.bytes)));
  return {
    sha256: shas.length === 1 ? shas[0] : await sha256(new TextEncoder().encode(`SyncUp-partes-v1:${shas.join(':')}`)),
    arquivo: arquivos.map((a) => a.nome).join(' + '),
  };
}

function diagnostico(c, id, nome, fuso) {
  const n = c.contadores;
  let min = 0, max = 0;
  c.utc.forEach((t, i) => { if (t < c.utc[min]) min = i; if (t > c.utc[max]) max = i; });
  return {
    Perfil: nome,
    Arquivo: id.arquivo,
    'SHA-256 do arquivo': id.sha256,
    'Registros recebidos': n.recebidos,
    'Podcasts descartados': n.podcasts,
    'Duração inválida': n.ms_invalidos,
    'Data inválida': n.datas_invalidas,
    'Identificação inválida': n.metadados_invalidos,
    'Various Artists encontrados': n.various_artists_encontrados,
    'Various Artists descartados': n.various_artists_descartados,
    'Ignorados pelos filtros': n.ignorados,
    'Duplicados removidos': n.duplicados,
    'Registros de músicas antes do recorte': n.validos,
    'Início do histórico': localTexto(c.local[min]),
    'Fim do histórico': localTexto(c.local[max]),
    'Fuso horário': fuso,
    'Origem dos dados': 'Lido no navegador',
  };
}

// Mesmos eventos (instante, duração, música, artista) e na mesma ordem.
function iguais(ca, ia, cb, ib) {
  return ia.length === ib.length && ia.every((i, k) => {
    const j = ib[k];
    return ca.utc[i] === cb.utc[j] && ca.ms[i] === cb.ms[j] && ca.musica[i] === cb.musica[j] && ca.artista[i] === cb.artista[j];
  });
}

const AVISOS = {
  bytes_identicos: 'Os arquivos recebidos possuem bytes idênticos (SHA-256 igual). Confira os arquivos selecionados na aba Diagnóstico.',
  historicos_identicos: 'Os ZIPs são diferentes, mas os registros de músicas após a limpeza são idênticos. Isso não identifica o dono dos arquivos.',
  recorte_identico: 'Os históricos completos são diferentes; apenas os registros no período selecionado coincidem.',
  diferentes: 'Os históricos recebidos possuem registros diferentes.',
};

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
    todos,
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
export function compararDupla(ca, cb, nomeA, nomeB, opcoes = {}, ids = [{ sha256: '', arquivo: '' }, { sha256: '', arquivo: '' }]) {
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
  const todosA = ca.utc.map((_, i) => i), todosB = cb.utc.map((_, i) => i);
  const status = ids[0].sha256 && ids[0].sha256 === ids[1].sha256 ? 'bytes_identicos'
    : iguais(ca, todosA, cb, todosB) ? 'historicos_identicos'
      : iguais(ca, ia, cb, ib) ? 'recorte_identico' : 'diferentes';
  const fuso = opcoes.fuso || 'America/Sao_Paulo';
  const pa = perfil(ca, ia, nomeA), pb = perfil(cb, ib, nomeB);
  if (!pa.plays.length || !pb.plays.length) throw new Error('Não há reproduções de pelo menos 30 segundos para os dois perfis nesse período.');
  const ra = pa.contagens, rb = pb.contagens;
  const pesosA = ponderar(ra, modo), pesosB = ponderar(rb, modo);
  const positivos = (m) => [...m].filter(([, v]) => v > 0).map(([k]) => k);
  const metricas = {
    cosseno: cosseno(pesosA, pesosB),
    jaccard: jaccard(positivos(pesosA), positivos(pesosB)),
    rbo_top50: rbo(rankingArtistas(ra), rankingArtistas(rb)),
    ruzicka: ruzicka(pesosA, pesosB),
  };
  if (Object.values(metricas).some((v) => v === null)) throw new Error('Não há dados suficientes para calcular as similaridades.');
  // Participação de cada artista nos plays de cada um: ordena os artistas em comum.
  const quaseMusicas = momentosSincronizados(ca, pa.plays, cb, pb.plays, 'musica');
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
    quase_artistas: momentosSincronizados(ca, pa.plays, cb, pb.plays, 'artista'),
    quase_musicas: quaseMusicas,
    sintonia: sintoniaJson(sintoniaEntre(ca, pa.plays, cb, pb.plays), quaseMusicas.total_pares),
    ponte: ponte(ra, rb, nomeA, nomeB),
    diversidade: [pa, pb].map((p) => ({ entropia: entropia(p.contagens), gini: gini(p.contagens) })),
    // Minutos por execução: todas as execuções do período (não só as de 30 s).
    estatisticas: [ca, cb].map((c, k) => descrever([pa, pb][k].todos.map((i) => c.ms[i] / 60000))),
    status,
    aviso: AVISOS[status],
    diagnostico: [diagnostico(ca, ids[0], nomeA, fuso), diagnostico(cb, ids[1], nomeB, fuso)],
    fuso,
    // Para a resposta do app (respostaDupla): plays por hora e por mês e artista. Fora da paridade da etapa 2.
    _bruto: [[ca, pa], [cb, pb]].map(([c, p]) => {
      const porHora = Array(24).fill(0), porMes = new Map(), diaHora = Array.from({ length: 7 }, () => Array(24).fill(0));
      for (const i of p.plays) {
        const d = new Date(c.local[i]);
        porHora[d.getUTCHours()]++;
        diaHora[(d.getUTCDay() + 6) % 7][d.getUTCHours()]++; // segunda = 0, como o dayofweek do pandas
        const mes = d.getUTCFullYear() * 100 + d.getUTCMonth() + 1;
        const m = porMes.get(mes) || porMes.set(mes, new Map()).get(mes);
        somar(m, c.artista[i]);
      }
      // Horas por mês: todas as execuções do período (não só as de 30 s), como perfil.mensal.
      const horasMes = new Map();
      for (const i of p.todos) {
        const d = new Date(c.local[i]);
        somar(horasMes, d.getUTCFullYear() * 100 + d.getUTCMonth() + 1, c.ms[i] / 60000);
      }
      return { porHora, porMes, diaHora, horasMes, contagens: p.contagens, faixas: p.faixas };
    }),
    // Os 12 artistas do gráfico: maior participação somada nos dois; empate pelo nome.
    ordem: [...new Set([...ra.keys(), ...rb.keys()])].sort(compararTexto)
      .map((k) => [k, participacao(k)]).sort(([, x], [, y]) => y - x).slice(0, 12).map(([k]) => k),
  };
}

/* ---------- Resposta do app (web/ponte.comparar_dupla, sem os gráficos) ---------- */
export const VERDE = '#1ed760', ROXO = '#c4b7ff';
const ARTISTAS_CORRIDA = 8, LINHAS_TABELA = 20, TOP_LISTA = 10;

// fmt_num do Python: milhares com ponto, decimais com vírgula. Diferente do fmtNum de stories/logica.js
// (halfEven, o do Wrapped) de propósito: cada um tem a paridade com o seu lado do Python.
export function fmtNum(valor, casas = 0) {
  const [inteiro, decimais] = Math.abs(valor).toFixed(casas).split('.');
  const sinal = valor < 0 && Number(Math.abs(valor).toFixed(casas)) !== 0 ? '-' : '';
  return sinal + inteiro.replace(/\B(?=(\d{3})+(?!\d))/g, '.') + (decimais ? `,${decimais}` : '');
}
// html.escape(texto, quote=True) do Python.
const escapar = (texto) => String(texto).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');

// zlib.crc32 (o tom da capa tipográfica de cada nome, igual ao do app para PC).
const TABELA_CRC = Array.from({ length: 256 }, (_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; return c >>> 0; });
function crc32(texto) {
  let c = 0xffffffff;
  for (const b of new TextEncoder().encode(texto)) c = TABELA_CRC[(c ^ b) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}
// Até duas iniciais (primeira e última palavra que começam com letra ou número).
function inicial(nome) {
  const palavras = (nome || '').split(/\s+/).filter((p) => /^[\p{L}\p{N}]/u.test(p));
  if (!palavras.length) return '?';
  return escapar((palavras[0][0] + (palavras.length > 1 ? palavras.at(-1)[0] : '')).toUpperCase());
}

// componentes.lista_top: a lista estilo playlist dos rankings, com o mesmo HTML do Python.
function listaTop(entradas, cor, titulo) {
  if (!entradas.length) return `<div class="su-tracklist-card"><h3>${escapar(titulo)}</h3><p class="su-note">Sem dados neste recorte.</p></div>`;
  const linhas = entradas.slice(0, TOP_LISTA);
  const maximo = Math.max(...linhas.map((l) => l.plays), 1);
  const itens = linhas.map(({ principal, secundario, link, plays }, i) => `<li style="--i:${i}"><a href="${escapar(link)}" target="_blank" rel="noopener noreferrer">`
    + `<span class="su-num">${i + 1}</span><span class="su-playicon" aria-hidden="true"></span>`
    + `<span class="su-cover" style="--hue:${crc32(principal) % 360}">${inicial(principal)}</span>`
    + `<span class="su-meta"><b>${escapar(principal)}</b>${secundario ? `<small>${escapar(secundario)}</small>` : ''}</span>`
    + `<span class="su-mini"><i style="--value:${((plays / maximo) * 100).toFixed(1)}%"></i></span>`
    + `<span class="su-count">${fmtNum(plays)}</span></a></li>`);
  return `<div class="su-tracklist-card" style="--accent:${cor}"><h3>${escapar(titulo)}</h3><ol class="su-tracklist">${itens.join('')}</ol></div>`;
}

// componentes.corrida_html: plays acumulados mês a mês dos artistas que chegam ao top 8 em algum mês.
function corridaHtml(perfis, brutos) {
  const meses = [...new Set(brutos.flatMap((b) => [...b.porMes.keys()]))].sort((a, b) => a - b);
  if (!meses.length) return '<p class="su-note">Sem meses suficientes para a corrida de artistas.</p>';
  const serie = (nome, { porMes }) => {
    const acumulado = new Map(), linhas = [], selecionados = new Set();
    for (const mes of meses) {
      for (const [artista, n] of porMes.get(mes) || []) somar(acumulado, artista, n);
      linhas.push(new Map(acumulado));
      [...acumulado].filter(([, v]) => v > 0).sort(porContagem).slice(0, ARTISTAS_CORRIDA).forEach(([k]) => selecionados.add(k));
    }
    const colunas = [...selecionados].sort((x, y) => (acumulado.get(y) - acumulado.get(x)) || compararTexto(x, y));
    return { nome, artistas: colunas, valores: colunas.map((k) => linhas.map((l) => l.get(k) || 0)) };
  };
  const dados = {
    meses: meses.map((m) => `${Math.floor(m / 100)}-${String(m % 100).padStart(2, '0')}`),
    topo: ARTISTAS_CORRIDA,
    perfis: [{ ...serie(perfis[0].nome, brutos[0]), cor: VERDE, rotulo: 'A' }, { ...serie(perfis[1].nome, brutos[1]), cor: ROXO, rotulo: 'B' }],
  };
  return `<div class="su-race" data-race="${escapar(JSON.stringify(dados))}"><p class="su-note">Corrida dos artistas: plays ≥30s acumulados mês a mês no recorte. Ative o JavaScript para ver a animação.</p></div>`;
}

// ponte._tabela + apresentacao.tabela_display: números em pt-BR (inteiros sem casas, decimais com 2).
const celula = (v, inteiro = false) => (typeof v !== 'number' ? (v ?? '') : Number.isNaN(v) ? '—' : fmtNum(v, inteiro || Number.isInteger(v) ? 0 : 2));
const tabela = (colunas, linhas, inteiro = () => false) => ({ colunas, linhas: linhas.map((l, r) => l.map((v) => String(celula(v, inteiro(r))))) });
const COLUNAS_MOMENTOS = ['Artista', 'Música A', 'Música B', 'Instante A (UTC)', 'Instante B (UTC)', 'Horário A', 'Horário B', 'Distância (min)'];
const MEDIDAS = ['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max'];

// ponte._trilha_dupla: a música de cada story vem da playlist comum (a mais ouvida pelos dois primeiro).
function trilhaDupla(r, apresentar) {
  const comuns = r.playlist.slice(0, 10).map(([artista, musica]) => ({ faixa: musica, artista }));
  const emComum = r.comuns.slice(0, 3);
  const doArtista = comuns.filter((m) => emComum.includes(m.artista));
  const favoritos = r.perfis.filter((p) => p.top_artistas.length).map((p) => ({ artista: p.top_artistas[0][0] }));
  const juntos = r.sintonia.musica ? [{ faixa: r.sintonia.musica.nome, artista: r.sintonia.musica.artista }] : [];
  const slides = {
    abertura: comuns.slice(0, 1),
    em_comum: [...doArtista.slice(0, 1), ...emComum.map((a) => ({ artista: a }))],
    frente: favoritos,
    apresentar: apresentar.map((p) => ({ artista: p.artista })),
    relogios: comuns.slice(1, 2),
    sintonia: juntos,
    sintonia_musica: juntos,
    poster: comuns.slice(0, 1),
  };
  return {
    slides: Object.fromEntries(Object.entries(slides).filter(([, c]) => c.length)),
    fila: [...comuns, ...emComum.map((a) => ({ artista: a }))],
  };
}

// ponte._dupla_json: o contrato dos stories da Dupla.
function duplaJson(r) {
  const [ra, rb] = r._bruto.map((b) => b.contagens);
  const posicoes = [ra, rb].map((m) => new Map([...m].sort(porContagem).map(([k], i) => [k, i + 1])));
  const pessoa = (p, b) => ({ nome: p.nome, plays: p.plays, horas: p.horas, artistas: p.artistas, plays_por_hora: b.porHora, pico_hora: b.porHora.indexOf(Math.max(...b.porHora)) });
  const favorito = (i) => {
    const topo = r.perfis[i].top_artistas[0];
    return topo ? { nome: topo[0], plays: topo[1], posicao_no_outro: posicoes[1 - i].get(topo[0]) ?? null } : null;
  };
  const apresentar = [r.perfis[0].nome, r.perfis[1].nome].flatMap((de) => r.ponte.filter((l) => l[0] === de).slice(0, 2)
    .map(([d, para, artista, plays, , link]) => ({ de: d, para, artista, plays, link })));
  return {
    a: pessoa(r.perfis[0], r._bruto[0]),
    b: pessoa(r.perfis[1], r._bruto[1]),
    inicio: r.periodo.inicio,
    fim: r.periodo.fim,
    periodo_comum: r.periodo.comum,
    match: r.metricas.cosseno,
    total_comuns: r.comuns.length,
    em_comum: r.comuns.slice(0, 3).map((nome) => ({ nome, plays_a: ra.get(nome) || 0, plays_b: rb.get(nome) || 0 })),
    favoritos: [favorito(0), favorito(1)],
    apresentar,
    sintonia: r.sintonia,
    trilha: trilhaDupla(r, apresentar),
  };
}

const dataBr = (iso) => iso.slice(0, 10).split('-').reverse().join('/');

/** A mesma resposta de web/ponte.comparar_dupla (sem `graficos`), a partir de compararDupla. */
export function respostaDupla(r) {
  const [a, b] = r.perfis;
  const listaArtistas = (p) => p.top_artistas.map(([nome, plays]) => ({ principal: nome, secundario: '', link: linkSpotify(nome), plays }));
  const listaMusicas = (p) => p.top_musicas.map(([musica, artista, plays]) => ({ principal: musica, secundario: artista, link: linkSpotify(artista, musica), plays }));
  // Distância e estatísticas são decimais no Python (2 casas mesmo quando redondas, como 30,00); o JS não distingue 30 de 30.0.
  const decimal = (v) => (Number.isNaN(v) ? '—' : fmtNum(v, 2));
  const momentos = (q) => tabela(COLUNAS_MOMENTOS, q.exemplos.map((l) => [...l.slice(0, 7), decimal(l[7])]));
  const div = (p, d) => [p.nome, fmtNum(p.artistas), d.entropia === null ? '—' : fmtNum(d.entropia, 4), d.gini === null ? '—' : fmtNum(d.gini, 4)];
  const colunasDiagnostico = Object.keys(r.diagnostico[0]);
  return {
    nomes: [a.nome, b.nome],
    periodo: r.periodo.comum
      ? `${dataBr(r.periodo.inicio)} a ${dataBr(r.periodo.fim)} (fuso ${r.fuso})`
      : `Históricos completos, com coberturas potencialmente diferentes. Fuso: ${r.fuso}.`,
    aviso: r.aviso,
    dupla: duplaJson(r),
    metricas: r.metricas,
    html: {
      corrida: corridaHtml(r.perfis, r._bruto),
      listas: [
        listaTop(listaArtistas(a), VERDE, `Top artistas · ${a.nome}`),
        listaTop(listaArtistas(b), ROXO, `Top artistas · ${b.nome}`),
        listaTop(listaMusicas(a), VERDE, `Top músicas · ${a.nome}`),
        listaTop(listaMusicas(b), ROXO, `Top músicas · ${b.nome}`),
      ],
    },
    quase: { artistas: r.quase_artistas.total_pares, musicas: r.quase_musicas.total_pares },
    conexoes: { comuns: r.comuns.slice(0, 20), so_a: r.so_a.slice(0, 20), so_b: r.so_b.slice(0, 20) },
    ponte: r.ponte.map(([de, para, artista, plays, , link]) => ({ de, para, artista, plays, link })),
    tabelas: {
      playlist: tabela(['Artista', 'Música', 'Reproduções A', 'Reproduções B', 'Spotify'], r.playlist.slice(0, LINHAS_TABELA)),
      contribuicoes: tabela(['Artista', 'Contribuição ao cosseno'], r.contribuicoes.slice(0, LINHAS_TABELA).map(([k, v]) => [k, `${fmtNum(v * 100, 4)} p.p.`])),
      diversidade: tabela(['Perfil', 'Artistas observados', 'Entropia normalizada', 'Gini observado'], [div(a, r.diversidade[0]), div(b, r.diversidade[1])]),
      estatisticas: tabela(['Medida', 'Minutos por execução · A', 'Minutos por execução · B'], MEDIDAS.map((m, k) => [m, ...[0, 1].map((p) => (k === 0 ? fmtNum(r.estatisticas[p][k]) : decimal(r.estatisticas[p][k])))])),
      diagnostico: tabela(colunasDiagnostico, r.diagnostico.map((d) => colunasDiagnostico.map((k) => d[k]))),
      quase_artistas: momentos(r.quase_artistas),
      quase_musicas: momentos(r.quase_musicas),
    },
  };
}

/* ---------- Playlist comum em CSV (exportacoes.exportar_playlist) ---------- */
// UTF-8 com BOM, separado por ponto e vírgula, como o csv.writer do Python. Nomes que uma planilha leria
// como fórmula (=, +, -, @, tab, CR no começo) ganham um apóstrofo na frente.
const seguro = (v) => { const t = String(v); return /^\s*[=+\-@\t\r]/.test(t) ? `'${t}` : t; };
const campo = (t) => (/[;"\r\n]/.test(t) ? `"${t.replace(/"/g, '""')}"` : t);
export function csvPlaylist(r) {
  const linhas = [['Artista', 'Música', 'Reproduções A', 'Reproduções B', 'Spotify'], ...r.playlist.map((l) => l.map(seguro))];
  return `﻿${linhas.map((l) => l.map(campo).join(';')).join('\r\n')}\r\n`;
}
