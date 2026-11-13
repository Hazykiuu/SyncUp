// Leitura do Histórico Estendido do Spotify no navegador, com as regras de dados.py.
// Sem DOM: roda no Worker do Wrapped e no Node (testes de paridade com o Python).

export const LIMITE_BYTES = 1024 ** 3; // o mesmo teto do Python: barra zip bomb antes de descompactar
// Cada JSON do ZIP vira um bloco único de memória; acima disso o celular (iOS) fecha a aba.
// shortcut: 64 MB = 4× o maior arquivo real do Spotify (~15 MB); subir se o Spotify mudar o tamanho.
export const LIMITE_ENTRADA = 64 * 1048576;
const CAMPOS = ['ts', 'ms_played', 'master_metadata_track_name', 'master_metadata_album_artist_name'];

const MSG = {
  zip: 'O arquivo ZIP está inválido ou incompleto. Baixe o histórico novamente.',
  json: 'O histórico contém um JSON inválido. Confira se o download foi concluído.',
  texto: 'Não foi possível ler o texto do histórico. Use arquivos JSON em UTF-8.',
  tipo: 'Selecione um arquivo ZIP ou JSON do histórico estendido.',
  estendido: 'Use o histórico estendido de áudio do Spotify (ZIP ou JSON).',
  tamanho: 'O histórico passa de 1 GB descompactado. Use o histórico estendido de áudio do Spotify (ZIP ou JSON).',
  entrada: 'Um arquivo dentro do ZIP passa de 64 MB descompactado, grande demais para o navegador. Use o histórico estendido de áudio do Spotify.',
  nenhum: 'Selecione pelo menos um ZIP ou JSON por perfil.',
  repetido: 'O mesmo conteúdo foi selecionado mais de uma vez neste perfil. Remova o arquivo duplicado.',
  fuso: 'Fuso inválido. Use um nome IANA, como America/Sao_Paulo ou Europe/Lisbon.',
  navegador: 'Este navegador não consegue abrir o ZIP. Atualize o navegador (no iPhone, iOS 16.4 ou mais novo) e tente de novo.',
};
const falha = (chave) => new Error(MSG[chave]);

/* ---------- ZIP (diretório central + DecompressionStream) ---------- */
// O ZIP vem do usuário: toda posição e todo tamanho são conferidos contra o arquivo.
function entradasZip(bytes) {
  const v = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  let fim = -1;
  for (let i = bytes.length - 22; i >= Math.max(0, bytes.length - 22 - 65535); i--) {
    if (v.getUint32(i, true) === 0x06054b50) { fim = i; break; }
  }
  if (fim < 0) throw falha('zip');
  const total = v.getUint16(fim + 10, true), tamanhoDir = v.getUint32(fim + 12, true), inicioDir = v.getUint32(fim + 16, true);
  if (total === 0xffff || inicioDir === 0xffffffff || inicioDir + tamanhoDir > fim) throw falha('zip'); // ZIP64 ou cortado
  const nomes = new TextDecoder();
  const entradas = [];
  for (let p = inicioDir, i = 0; i < total; i++) {
    if (p + 46 > fim || v.getUint32(p, true) !== 0x02014b50) throw falha('zip');
    const bandeiras = v.getUint16(p + 8, true), metodo = v.getUint16(p + 10, true);
    const comprimido = v.getUint32(p + 20, true), tamanho = v.getUint32(p + 24, true);
    const n = v.getUint16(p + 28, true), extra = v.getUint16(p + 30, true), comentario = v.getUint16(p + 32, true);
    const local = v.getUint32(p + 42, true);
    if (p + 46 + n > fim) throw falha('zip');
    entradas.push({ nome: nomes.decode(bytes.subarray(p + 46, p + 46 + n)), bandeiras, metodo, comprimido, tamanho, local });
    p += 46 + n + extra + comentario;
  }
  return entradas;
}

async function lerEntrada(bytes, e) {
  const v = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  if (e.bandeiras & 1 || (e.metodo !== 0 && e.metodo !== 8)) throw falha('zip'); // senha ou compressão rara
  if (e.local + 30 > bytes.length || v.getUint32(e.local, true) !== 0x04034b50) throw falha('zip');
  const inicio = e.local + 30 + v.getUint16(e.local + 26, true) + v.getUint16(e.local + 28, true);
  if (inicio + e.comprimido > bytes.length) throw falha('zip');
  const dados = bytes.subarray(inicio, inicio + e.comprimido);
  if (e.metodo === 0) {
    if (e.comprimido !== e.tamanho) throw falha('zip');
    return dados;
  }
  // Para no tamanho declarado: um cabeçalho mentiroso não estoura a memória.
  const saida = new Uint8Array(e.tamanho);
  let pos = 0;
  try {
    const leitor = new Blob([dados]).stream().pipeThrough(new DecompressionStream('deflate-raw')).getReader();
    for (;;) {
      const { done, value } = await leitor.read();
      if (done) break;
      if (pos + value.length > e.tamanho) { await leitor.cancel(); throw falha('zip'); }
      saida.set(value, pos);
      pos += value.length;
    }
  } catch { throw falha('zip'); }
  if (pos !== e.tamanho) throw falha('zip');
  return saida;
}

// Pastas e metadados do macOS (__MACOSX/, ._arquivo.json) e o que não for JSON ficam de fora.
export function entradaIgnorada(nome) {
  const base = nome.slice(nome.lastIndexOf('/') + 1);
  return nome.endsWith('/') || nome.startsWith('__MACOSX/') || nome.includes('/__MACOSX/') || base.startsWith('._') || !base.toLowerCase().endsWith('.json');
}

// Um JSON por vez (o texto sai da memória antes do próximo), como o Python.
async function* jsonsDoArquivo({ nome, bytes }) {
  const lerJson = (dados) => {
    let texto;
    try { texto = new TextDecoder('utf-8', { fatal: true }).decode(dados); } catch { throw falha('texto'); } // tira o BOM
    try { return JSON.parse(texto); } catch { throw falha('json'); }
  };
  if (/\.zip$/i.test(nome)) {
    if (typeof DecompressionStream === 'undefined') throw falha('navegador');
    const entradas = entradasZip(bytes).filter((e) => !entradaIgnorada(e.nome));
    if (entradas.reduce((t, e) => t + e.tamanho, 0) > LIMITE_BYTES) throw falha('tamanho');
    if (entradas.some((e) => e.tamanho > LIMITE_ENTRADA)) throw falha('entrada');
    for (const e of entradas) yield lerJson(await lerEntrada(bytes, e));
  } else if (/\.json$/i.test(nome)) {
    if (bytes.length > LIMITE_BYTES) throw falha('tamanho');
    yield lerJson(bytes);
  } else throw falha('tipo');
}

/* ---------- Limpeza (mesma ordem de descartes de dados._limpar) ---------- */
// casefold do Python ≈ maiúsculas e depois minúsculas ("ß" → "ss"); \W do Python tira marcas também.
export const normalizarNome = (nome) => nome.normalize('NFKC').toUpperCase().toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '');
const VARIOS = normalizarNome('Various Artists');

// Família do aparelho (Android, Windows…), nunca o modelo ou a versão: igual a dados.familia_plataforma.
const FAMILIAS = [
  [['web_player', 'web player', 'webplayer'], 'Navegador'], [['android'], 'Android'], [['ios', 'iphone', 'ipad'], 'iOS'],
  [['windows'], 'Windows'], [['os x', 'osx', 'macos', 'mac os'], 'macOS'], [['linux'], 'Linux'], [['web'], 'Navegador'],
  [['partner', 'cast', 'tv', 'playstation', 'xbox', 'sonos', 'alexa', 'echo', 'car'], 'TV, console ou caixa de som'],
];
export function familiaPlataforma(texto) {
  if (typeof texto !== 'string' || !texto.trim() || texto === 'not_applicable') return null;
  const t = texto.toUpperCase().toLowerCase();
  return FAMILIAS.find(([chaves]) => chaves.some((c) => t.includes(c)))?.[1] ?? 'Outro';
}

// Um play não passa de 24 h; acima disso é arquivo corrompido (igual a dados.py, TETO_MS).
export const TETO_MS = 86_400_000;

// Instante em ISO 8601 → milissegundos UTC. Sem fuso no texto, vale UTC (como o pandas com utc=True).
// Hora opcional (só a data = meia-noite UTC) e segundos opcionais, como o pandas aceita no Python.
const ISO = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.(\d+))?)?)?(Z|[+-]\d{2}:?\d{2})?$/;
export function instanteUtc(ts) {
  if (typeof ts !== 'string') return NaN;
  // Formato do Spotify ("2023-12-30T03:00:00Z"): caminho rápido pelo Date.parse nativo. Ele aceita
  // 30/02 e 24h (rola para o dia seguinte); a conferência do dia e da hora recusa essas datas.
  if (ts.length === 20 && ts[10] === 'T' && ts[19] === 'Z') {
    const ms = Date.parse(ts), dia = ts.slice(8, 10);
    return ms === ms && ts.slice(11, 13) < '24' && (dia <= '28' || new Date(ms).getUTCDate() === Number(dia)) ? ms : NaN;
  }
  const m = ISO.exec(ts.trim());
  if (!m) return NaN;
  const [ano, mes, dia, hora, min, seg] = m.slice(1, 7).map((x) => Number(x ?? 0)); // grupo ausente = 0
  if (mes < 1 || mes > 12 || dia < 1 || hora > 23 || min > 59 || seg > 59) return NaN;
  const ms = Date.UTC(ano, mes - 1, dia, hora, min, seg) + Number(`0.${m[7] || 0}`) * 1000;
  if (new Date(ms).getUTCDate() !== dia) return NaN; // 30 de fevereiro e afins
  if (!m[8] || m[8] === 'Z') return Math.floor(ms);
  const sinal = m[8][0] === '-' ? -1 : 1, [h, mm] = [m[8].slice(1, 3), m[8].slice(-2)].map(Number);
  return Math.floor(ms - sinal * (h * 60 + mm) * 60000);
}

// UTC → hora local do fuso. O Intl é a parte cara: o deslocamento é guardado por dia UTC, e só
// nos dias de troca de horário (início e fim do dia diferentes) ele é calculado por hora.
// shortcut: supõe a troca em hora cheia (vale para os fusos do app); fusos de meia hora com
// horário de verão (Austrália) erram por até 30 min na hora da troca. Calcular por 15 min resolve.
const HORA = 3600000, DIA = 24 * HORA;
export function relogio(fuso) {
  let formato;
  try { formato = new Intl.DateTimeFormat('en-US', { timeZone: fuso, hourCycle: 'h23', year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: 'numeric', second: 'numeric' }); } catch { throw falha('fuso'); }
  const desvioEm = (ms) => {
    const p = {};
    for (const { type, value } of formato.formatToParts(ms)) p[type] = Number(value);
    return Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, p.second) - ms;
  };
  const dias = new Map(), horas = new Map();
  return (utc) => {
    const d = Math.floor(utc / DIA);
    let desvio = dias.get(d);
    if (desvio === undefined) {
      const inicio = desvioEm(d * DIA);
      desvio = inicio === desvioEm(d * DIA + DIA - HORA) ? inicio : null; // null: dia de troca
      dias.set(d, desvio);
    }
    if (desvio === null) {
      const h = Math.floor(utc / HORA);
      desvio = horas.get(h) ?? (horas.set(h, desvioEm(h * HORA)), horas.get(h));
    }
    return utc + desvio;
  };
}

const linhas = (texto) => (texto || '').split(/\r?\n/).map((x) => x.trim()).filter(Boolean);
// Laço simples: 8× mais rápido que every() (50 MB iguais: 620 → 72 ms) e para na primeira diferença.
function iguais(a, b) {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return false;
  return true;
}

/**
 * Lê as partes do histórico de uma pessoa e devolve os eventos válidos em colunas.
 * `arquivos`: [{ nome, bytes: Uint8Array }]. `opcoes`: as do app (fuso, musicas, artistas, varios, deduplicar).
 * Colunas: utc e local (ms), ms, musica, artista, uri, pulada, aleatorio, offline, plataforma, motivo.
 */
export async function lerHistorico(arquivos, opcoes = {}) {
  if (!arquivos.length) throw falha('nenhum');
  for (let i = 0; i < arquivos.length; i++) {
    for (let j = i + 1; j < arquivos.length; j++) if (iguais(arquivos[i].bytes, arquivos[j].bytes)) throw falha('repetido');
  }
  const local = relogio(opcoes.fuso || 'America/Sao_Paulo');
  const ignorarVarios = opcoes.varios === 'ignorar';
  const musicasIgnoradas = new Set(linhas(opcoes.musicas).map(normalizarNome));
  const artistasIgnorados = new Set(linhas(opcoes.artistas).map(normalizarNome));
  const vistos = opcoes.deduplicar ? new Set() : null;
  const normal = new Map(); // nome → normalizado, uma vez por nome
  const norm = (n) => normal.get(n) ?? (normal.set(n, normalizarNome(n)), normal.get(n));
  // O JSON cria um texto novo a cada ocorrência: guardar cada nome uma vez baixa o pico de memória.
  const unicos = new Map();
  const unico = (v) => (typeof v === 'string' ? unicos.get(v) ?? (unicos.set(v, v), v) : null);
  const familias = new Map();
  const c = { utc: [], local: [], ms: [], musica: [], artista: [], uri: [], pulada: [], aleatorio: [], offline: [], plataforma: [], motivo: [] };
  const bool = (v) => (typeof v === 'boolean' ? v : null);

  for (const arquivo of arquivos) {
    const encontrados = new Set();
    for await (const conteudo of jsonsDoArquivo(arquivo)) {
      // Só listas de histórico: listas auxiliares sem campos reconhecidos ficam de fora.
      const objeto = (x) => x !== null && typeof x === 'object' && !Array.isArray(x);
      if (!Array.isArray(conteudo) || !conteudo.some((x) => objeto(x) && CAMPOS.some((k) => k in x))) continue;
      for (const bruto of conteudo) {
        const e = objeto(bruto) ? bruto : {};
        if (encontrados.size < CAMPOS.length) for (const k of CAMPOS) if (k in e) encontrados.add(k);
        if (e.episode_name || e.episode_show_name || e.spotify_episode_uri) continue; // podcast
        const msBruto = e.ms_played;
        const ms = typeof msBruto === 'number' ? msBruto : typeof msBruto === 'string' && msBruto.trim() ? Number(msBruto) : NaN;
        if (!(ms >= 0 && ms <= TETO_MS)) continue; // mais de 24 h num play só: arquivo corrompido ou adulterado
        const utc = instanteUtc(e.ts);
        if (!(utc >= 0)) continue; // NaN ou antes de 1970 (relógio zerado): o cálculo por dia supõe dia ≥ 0
        const musica = typeof e.master_metadata_track_name === 'string' ? unico(e.master_metadata_track_name.trim()) : '';
        const artista = typeof e.master_metadata_album_artist_name === 'string' ? unico(e.master_metadata_album_artist_name.trim()) : '';
        if (!musica || !artista) continue;
        if (ignorarVarios && norm(artista) === VARIOS) continue;
        if ((musicasIgnoradas.size && musicasIgnoradas.has(norm(musica))) || (artistasIgnorados.size && artistasIgnorados.has(norm(artista)))) continue;
        if (vistos) {
          const chave = `${utc}|${ms}|${musica}|${artista}`;
          if (vistos.has(chave)) continue;
          vistos.add(chave);
        }
        const plataforma = typeof e.platform === 'string' ? (familias.get(e.platform) ?? (familias.set(e.platform, familiaPlataforma(e.platform)), familias.get(e.platform))) : null;
        c.utc.push(utc); c.local.push(local(utc)); c.ms.push(ms); c.musica.push(musica); c.artista.push(artista);
        c.uri.push(unico(e.spotify_track_uri)); c.pulada.push(bool(e.skipped)); c.aleatorio.push(bool(e.shuffle));
        c.offline.push(bool(e.offline)); c.plataforma.push(plataforma); c.motivo.push(unico(e.reason_end));
      }
    }
    if (encontrados.size < CAMPOS.length) throw falha('estendido');
  }
  return c;
}
