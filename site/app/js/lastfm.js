// Histórico do Last.fm pelo nome de usuário, direto do navegador (sem servidor nosso): só o nome vai ao Last.fm.
// Os scrobbles viram um JSON no formato do Histórico Estendido do Spotify e seguem o caminho de sempre
// (historico.js, workers). O Last.fm não diz quanto a música tocou nem se foi pulada: a duração vem do
// getTopTracks (top 3.000) e, no resto, da mediana; pulos ficam de fora sozinhos (sem skipped/reason_end).
import { cacheIndexedDB } from './capas.js';

// Chave pública de leitura (não é segredo; o Last.fm a usa para limitar pedidos por app).
export const CHAVE_API = '487c26d26abbfd02d12fe83ee0cb0fc1';
const API = 'https://ws.audioscrobbler.com/2.0/';
export const USUARIO_VALIDO = /^[A-Za-z][A-Za-z0-9_-]{1,14}$/; // regra de cadastro do Last.fm
const DURACAO_PADRAO = 210000; // 3,5 min, quando o Last.fm não sabe nenhuma duração
const PAGINAS_TOP = 3;
const INTERVALO_MS = 250; // até 4 pedidos por segundo (o Last.fm pede no máximo 5)
const EM_PARALELO = 3; // medido (1.23): 3 em voo, 152 mil escutas em ~5 min; com 6, o Last.fm passou a travar
const ESPERAS_LIMITE = [1000, 2000, 4000, 8000];
// Falhas passageiras: 8 (backend), 11 (fora do ar), 16 (indisponível), 29 (limite) e HTTP 429/5xx. Medido em 1.23:
// o erro 8 com HTTP 500 aparece de vez em quando no meio de históricos grandes.
const PASSAGEIRO = new Set([8, 11, 16, 29, 429, 500, 502, 503, 504]);
const TEMPO_LIMITE_MS = 20000; // um pedido pendurado travaria o download inteiro
const ANO_S = 365 * 86400;

const MENSAGENS = {
  6: 'Não achamos esse usuário no Last.fm. Confira o nome (é o que aparece no endereço do seu perfil).',
  17: 'Esse perfil esconde as escutas. No Last.fm, desligue "Ocultar escutas recentes" em Configurações → Privacidade e tente de novo.',
  29: 'O Last.fm pediu uma pausa. Espere um minuto e tente de novo.',
};

export class ErroLastfm extends Error {
  constructor(mensagem, codigo) { super(mensagem); this.codigo = codigo; }
}

const dormir = (ms, sinal) => new Promise((ok, erro) => {
  const t = setTimeout(ok, ms);
  sinal?.addEventListener('abort', () => { clearTimeout(t); erro(sinal.reason); }, { once: true });
});

// O único ponto que fala com a API. O Last.fm responde erros de negócio com HTTP 200 e { error }.
export async function pedir(metodo, params, { buscar = fetch, esperar = dormir, sinal } = {}) {
  const url = `${API}?${new URLSearchParams({ ...params, method: metodo, api_key: CHAVE_API, format: 'json' })}`;
  for (let tentativa = 0; ; tentativa++) {
    let resp, dados = null;
    const limite = AbortSignal.timeout(TEMPO_LIMITE_MS);
    try {
      resp = await buscar(url, { signal: sinal ? AbortSignal.any([sinal, limite]) : limite });
      try { dados = await resp.json(); } catch (e) { if (e?.name === 'TimeoutError' || e?.name === 'AbortError') throw e; } // corpo que não é JSON: tratado abaixo
    } catch (e) {
      if (sinal?.aborted || e?.name === 'AbortError') throw sinal?.reason ?? e;
      const demorou = e?.name === 'TimeoutError';
      if (demorou && tentativa < ESPERAS_LIMITE.length) { await esperar(ESPERAS_LIMITE[tentativa], sinal); continue; }
      throw new ErroLastfm(demorou ? 'O Last.fm está demorando para responder. Tente de novo daqui a pouco.' : 'Sem conexão com o Last.fm. Confira a internet e tente de novo.', 'rede');
    }
    const codigo = dados?.error ?? (resp.ok && dados && typeof dados === 'object' ? null : resp.status);
    if (codigo == null) return dados;
    if (PASSAGEIRO.has(codigo) && tentativa < ESPERAS_LIMITE.length) { await esperar(ESPERAS_LIMITE[tentativa], sinal); continue; }
    throw new ErroLastfm(MENSAGENS[codigo === 429 ? 29 : codigo] ?? `O Last.fm recusou o pedido (código ${codigo}). Tente de novo daqui a pouco.`, codigo);
  }
}

// Capa do álbum que o Last.fm manda junto com cada escuta (os scrobbles não têm o código do Spotify para o oEmbed).
// Só https do CDN do Last.fm; a estrela cinza é a imagem de "sem capa".
const HOST_CAPA = /^lastfm(-img)?\.freetls\.fastly\.net$/;
const SEM_CAPA = '2a96cbd8b46e442fc41c2b86b821562f';
export function capaDoScrobble(t) {
  const imagens = Array.isArray(t?.image) ? t.image : [];
  const url = (imagens.find((i) => i?.size === 'extralarge') ?? imagens.at(-1))?.['#text'];
  try {
    const u = new URL(url);
    return u.protocol === 'https:' && HOST_CAPA.test(u.hostname) && !u.pathname.includes(SEM_CAPA) ? u.href : null;
  } catch { return null; }
}

const lista = (x) => (Array.isArray(x) ? x : x ? [x] : []); // uma faixa só vem como objeto
const texto = (x) => (typeof x === 'string' ? x.trim() : '');
function validar(usuario) {
  if (!USUARIO_VALIDO.test(usuario || '')) throw new ErroLastfm('Esse nome de usuário não parece do Last.fm (de 2 a 15 letras, números, - ou _).', 'usuario');
}

// Todas as escutas a partir de `desde` (uts, opcional), sem ordem garantida (historicoDoLastfm ordena).
// O Last.fm leva ~1,5 s por página: várias páginas ao mesmo tempo, mas cada pedido começa 250 ms depois do
// anterior (no máximo 4 por segundo). Pula a faixa tocando agora.
// `capas` (Map opcional): recebe a capa de cada música (chave artista|música), a primeira que aparecer.
export async function baixarScrobbles(usuario, { desde, buscar, esperar = dormir, agora = () => performance.now(), sinal, aoProgresso, capas } = {}) {
  validar(usuario);
  const saida = [];
  const inicio = agora();
  let proximo = -Infinity, feitas = 0, paginas = 1, total = 0;
  const baixar = async (pagina) => {
    sinal?.throwIfAborted();
    const espera = proximo - agora();
    proximo = Math.max(agora(), proximo) + INTERVALO_MS; // reserva o horário antes de esperar
    if (espera > 0) await esperar(espera, sinal);
    const dados = await pedir('user.getrecenttracks', { user: usuario, limit: '200', page: String(pagina), ...(desde ? { from: String(desde) } : {}) }, { buscar, esperar, sinal });
    const rt = dados?.recenttracks;
    paginas = Number(rt?.['@attr']?.totalPages) || 0;
    total = Number(rt?.['@attr']?.total) || 0;
    for (const t of lista(rt?.track)) {
      if (t?.['@attr']?.nowplaying === 'true' || !t?.date?.uts) continue;
      const uts = Number(t.date.uts), musica = texto(t.name), artista = texto(t.artist?.['#text'] ?? t.artist?.name);
      if (!(Number.isFinite(uts) && musica && artista)) continue;
      saida.push({ uts, musica, artista });
      const k = capas && chave(artista, musica);
      if (k && !capas.has(k)) { const url = capaDoScrobble(t); if (url) capas.set(k, url); }
    }
    feitas++;
    const ritmo = Math.max((agora() - inicio) / feitas, INTERVALO_MS);
    aoProgresso?.({ pagina: feitas, paginas, scrobbles: saida.length, total, restanteMs: Math.round(ritmo * Math.max(0, paginas - feitas)) });
  };
  await baixar(1); // a primeira diz quantas páginas há
  let seguinte = 2;
  const trabalhar = async () => { while (seguinte <= paginas) await baixar(seguinte++); };
  await Promise.all(Array.from({ length: EM_PARALELO }, trabalhar));
  return saida;
}

export const chave = (artista, musica) => `${String(artista).trim().toLowerCase()}|${String(musica).trim().toLowerCase()}`;

// Duração das músicas mais ouvidas (top 3.000). "0" quer dizer que o Last.fm não sabe: fica de fora.
export async function baixarDuracoes(usuario, { buscar, esperar = dormir, sinal } = {}) {
  validar(usuario);
  const mapa = new Map();
  for (let pagina = 1, paginas = 1; pagina <= Math.min(paginas, PAGINAS_TOP); pagina++) {
    const dados = await pedir('user.gettoptracks', { user: usuario, period: 'overall', limit: '1000', page: String(pagina) }, { buscar, esperar, sinal });
    paginas = Number(dados?.toptracks?.['@attr']?.totalPages) || 0;
    for (const t of lista(dados?.toptracks?.track)) {
      const s = Number(t?.duration);
      if (s > 0 && texto(t.name) && texto(t.artist?.name)) mapa.set(chave(t.artist.name, t.name), s * 1000);
    }
  }
  return mapa;
}

function mediana(valores) {
  if (!valores.length) return null;
  const v = [...valores].sort((a, b) => a - b), m = v.length >> 1;
  return Math.round((v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2) / 1000) * 1000;
}

// JSON enxuto (~150 bytes por escuta) com só as 4 chaves que historico.js lê. O scrobble marca o início;
// o `ts` do Spotify é o fim da música.
export function paraFormatoSpotify(scrobbles, duracoes) {
  const reserva = mediana([...duracoes.values()]) ?? DURACAO_PADRAO;
  let comDuracao = 0;
  const eventos = scrobbles.map((s) => {
    const real = duracoes.get(chave(s.artista, s.musica));
    if (real) comDuracao++;
    const ms = real ?? reserva;
    return { ts: `${new Date(s.uts * 1000 + ms).toISOString().slice(0, 19)}Z`, ms_played: ms, master_metadata_track_name: s.musica, master_metadata_album_artist_name: s.artista };
  });
  return { json: JSON.stringify(eventos), cobertura: scrobbles.length ? comDuracao / scrobbles.length : 0 };
}

let armazemPadrao = null;
export const armazemLastfm = () => (armazemPadrao ??= cacheIndexedDB('syncup-lastfm'));

// O histórico guardado vence 7 dias depois do último uso (a landing e o README prometem isso).
export const VALIDADE_LASTFM = 7 * 86_400_000;
export const limparLastfmVencido = () => armazemLastfm().limpar(Date.now() - VALIDADE_LASTFM);

// Junta escutas sem repetir: a página do Last.fm desliza quando chega escuta nova no meio do download.
function juntar(a, b) {
  const vistos = new Set(), saida = [];
  for (const s of [...b, ...a]) {
    const k = `${s.uts}|${s.artista}|${s.musica}`;
    if (!vistos.has(k)) { vistos.add(k); saida.push(s); }
  }
  return saida.sort((x, y) => y.uts - x.uts);
}

// Histórico pronto para o pipeline, com cache por usuário: na volta, só baixa o que é novo.
// periodo: 'tudo' | 'ano'. Devolve { json, cobertura, reproducoes, capas }.
export async function historicoDoLastfm(usuario, { periodo = 'tudo', armazem = armazemLastfm(), agora = Date.now, ...rede } = {}) {
  validar(usuario);
  const id = usuario.toLowerCase();
  const anoAtras = Math.floor(agora() / 1000) - ANO_S;
  let cache = null;
  try { cache = (await armazem.ler(id)) ?? null; } catch { /* sem cache: baixa tudo */ }
  if (cache && agora() - cache.quando > VALIDADE_LASTFM) cache = null;
  // O cache guarda desde quando cobre (null = histórico inteiro). "Todo o histórico" sobre um cache de um ano baixa de novo.
  const completo = cache && (periodo === 'ano' ? cache.desde == null || cache.desde <= anoAtras : cache.desde == null);
  const desde = completo ? cache.ultimo + 1 : periodo === 'ano' ? anoAtras : undefined;
  const capas = new Map(completo ? cache.capas ?? [] : []);
  const novos = await baixarScrobbles(usuario, { ...rede, desde, capas });
  const escutas = juntar(completo ? cache.escutas : [], novos);
  const duracoes = cache?.duracoes ? new Map(cache.duracoes) : await baixarDuracoes(usuario, rede);
  if (escutas.length) {
    const valor = { escutas, ultimo: escutas[0].uts, desde: completo ? cache.desde : (desde ?? null), duracoes: [...duracoes], capas: [...capas], quando: agora() };
    try { await armazem.gravar(id, valor); } catch { /* aba anônima: segue sem cache */ }
  }
  const usadas = periodo === 'ano' ? escutas.filter((s) => s.uts >= anoAtras) : escutas;
  if (!usadas.length) throw new ErroLastfm(periodo === 'ano' ? 'Nenhum scrobble no último ano nesse perfil.' : 'Nenhum scrobble nesse perfil do Last.fm.', 'vazio');
  return { ...paraFormatoSpotify(usadas, duracoes), reproducoes: usadas.length, capas };
}
