// Capas e fotos do Wrapped: o Wrapped começa sempre com capas e som (pedido do Carlos, 12/11).
// Capa da música: oEmbed público do Spotify pelo ID que veio no ZIP (exata, sem casar nomes).
// Foto do artista: MusicBrainz (nome → link do Spotify) → oEmbed do artista.
// Tudo com CORS * e sem chave. Guarda só a URL (IndexedDB, 30 dias), nunca a imagem.
import { normalizar } from './stories/logica.js';

const OEMBED = 'https://open.spotify.com/oembed?url=';
const MB = 'https://musicbrainz.org/ws/2/artist/';
const DIA = 86_400_000;
const VALIDADE = 30 * DIA;
const PARALELO = 4; // oEmbed em rajada
const INTERVALO_MB = 1100; // MusicBrainz: 1 consulta por segundo para o app todo

// Só IDs reais (22 caracteres base62): os dados fictícios ("spotify:track:ficticio_…") não vão à rede.
const ID_FAIXA = /^spotify:track:([A-Za-z0-9]{22})$/;
export const idFaixa = (uri) => (typeof uri === 'string' && uri.match(ID_FAIXA)?.[1]) || null;
const ID_ARTISTA = /open\.spotify\.com\/artist\/([A-Za-z0-9]{22})/;

// Só https dos domínios esperados: uma resposta adulterada não consegue apontar <img>/<audio>
// para outro servidor (rastreio de quem abriu o Wrapped).
export const HOSTS_IMAGEM = /^(i\.scdn\.co|[a-z0-9-]+\.spotifycdn\.com)$/;
export const HOSTS_AUDIO = /^(audio-ssl\.itunes\.apple\.com|[a-z0-9-]+\.mzstatic\.com)$/;
export function urlSegura(url, hosts) {
  try { const u = new URL(url); return u.protocol === 'https:' && hosts.test(u.hostname) ? u.href : null; } catch { return null; }
}

// Cache: IndexedDB quando existe (aba anônima ou erro → só memória).
export function cacheIndexedDB(nome = 'syncup-capas') {
  const memoria = new Map();
  const banco = new Promise((ok) => {
    try {
      const pedido = indexedDB.open(nome, 1);
      pedido.onupgradeneeded = () => pedido.result.createObjectStore('capas');
      pedido.onsuccess = () => ok(pedido.result);
      pedido.onerror = () => ok(null);
    } catch { ok(null); }
  });
  const loja = async (modo) => (await banco)?.transaction('capas', modo).objectStore('capas');
  const comoPromessa = (pedido) => new Promise((ok) => { pedido.onsuccess = () => ok(pedido.result); pedido.onerror = () => ok(undefined); });
  return {
    async ler(chave) {
      if (memoria.has(chave)) return memoria.get(chave);
      try { const l = await loja('readonly'); return l ? comoPromessa(l.get(chave)) : undefined; } catch { return undefined; }
    },
    async gravar(chave, valor) {
      memoria.set(chave, valor);
      try { (await loja('readwrite'))?.put(valor, chave); } catch { /* fica só na memória */ }
    },
    // Apaga o que venceu: as regras do Spotify pedem para não guardar capas para sempre.
    async limpar(antesDe) {
      for (const [k, v] of memoria) if (v.quando < antesDe) memoria.delete(k);
      try {
        const l = await loja('readwrite');
        if (!l) return;
        const cursor = l.openCursor();
        await new Promise((ok) => {
          cursor.onsuccess = () => { const c = cursor.result; if (!c) return ok(); if (c.value?.quando < antesDe) c.delete(); c.continue(); };
          cursor.onerror = () => ok();
        });
      } catch { /* sem IndexedDB: nada a apagar */ }
    },
    async apagarTudo() {
      memoria.clear();
      try { const l = await loja('readwrite'); if (l) await comoPromessa(l.clear()); } catch { /* idem */ }
    },
  };
}

export function cacheMemoria() {
  const m = new Map();
  return {
    ler: async (k) => m.get(k),
    gravar: async (k, v) => { m.set(k, v); },
    limpar: async (antesDe) => { for (const [k, v] of m) if (v.quando < antesDe) m.delete(k); },
    apagarTudo: async () => { m.clear(); },
  };
}

// Limite de concorrência: no máximo `n` tarefas ao mesmo tempo, com espaço mínimo entre os inícios.
function limitador(n, espaco, esperar) {
  let ativos = 0, ultimo = -Infinity;
  const fila = [];
  const proximo = () => {
    if (ativos >= n || !fila.length) return;
    ativos++;
    const { tarefa, ok, falha } = fila.shift();
    const atraso = Math.max(0, ultimo + espaco - Date.now());
    ultimo = Date.now() + atraso;
    (atraso ? esperar(atraso) : Promise.resolve())
      .then(tarefa).then(ok, falha)
      .finally(() => { ativos--; proximo(); });
  };
  return (tarefa) => new Promise((ok, falha) => { fila.push({ tarefa, ok, falha }); proximo(); });
}

export function criarBuscador({ fetch = globalThis.fetch.bind(globalThis), esperar = (ms) => new Promise((r) => setTimeout(r, ms)), cache = cacheIndexedDB(), agora = Date.now } = {}) {
  cache.limpar(agora() - VALIDADE);
  const spotify = limitador(PARALELO, 0, esperar);
  const musicbrainz = limitador(1, INTERVALO_MB, esperar);

  // 429/503: espera dobrando (2 s, 4 s, 8 s). Se continuar recusando, erro: segue sem imagem
  // agora, mas não grava "não achou" no cache (tenta de novo na próxima vez).
  async function json(url, vez) {
    for (let tentativa = 0; tentativa < 4; tentativa++) {
      const r = await vez(() => fetch(url));
      if (r.ok) return r.json();
      if (r.status !== 429 && r.status !== 503) return null;
      if (tentativa < 3) await esperar(2000 * 2 ** tentativa);
    }
    throw new Error('serviço ocupado');
  }
  const oembed = async (tipo, id) => {
    const d = await json(OEMBED + encodeURIComponent(`https://open.spotify.com/${tipo}/${id}`), spotify);
    const url = urlSegura(d?.thumbnail_url, HOSTS_IMAGEM);
    return url ? { url, titulo: d.title || '' } : null;
  };

  // Mesmo pedido duas vezes (ex.: artista em dois slides) → uma busca só.
  const emAndamento = new Map();
  const comCache = (chave, buscar) => {
    if (!emAndamento.has(chave)) {
      emAndamento.set(chave, (async () => {
        const salvo = await cache.ler(chave);
        if (salvo && agora() - salvo.quando < VALIDADE) return salvo.valor;
        let valor = null;
        try { valor = await buscar(); } catch { return null; } // sem rede: não grava, tenta de novo outro dia
        await cache.gravar(chave, { valor, quando: agora() });
        return valor;
      })());
    }
    return emAndamento.get(chave);
  };

  return {
    // "Apagar capas guardadas": cache e buscas em memória.
    async apagarTudo() { emAndamento.clear(); await cache.apagarTudo(); },
    // { url, link } da capa, ou null.
    faixa(uri) {
      const id = idFaixa(uri);
      if (!id) return Promise.resolve(null);
      return comCache(`t:${id}`, async () => {
        const o = await oembed('track', id);
        return o && { url: o.url, link: `https://open.spotify.com/track/${id}` };
      });
    },
    // { url, link } da foto, ou null. Na dúvida, sem foto: nunca a foto de outra pessoa.
    artista(nome) {
      const alvo = normalizar(nome || '');
      if (!alvo) return Promise.resolve(null);
      return comCache(`a:${alvo}`, async () => {
        const termo = `artist:"${nome.replace(/["\\]/g, '\\$&')}"`;
        const busca = await json(`${MB}?query=${encodeURIComponent(termo)}&fmt=json&limit=3`, musicbrainz);
        const achado = busca?.artists?.find((a) => normalizar(a.name) === alvo);
        if (!achado) return null;
        const rel = await json(`${MB}${achado.id}?inc=url-rels&fmt=json`, musicbrainz);
        const id = rel?.relations?.map((x) => x.url?.resource?.match(ID_ARTISTA)?.[1]).find(Boolean);
        if (!id) return null;
        const o = await oembed('artist', id);
        return o && normalizar(o.titulo) === alvo ? { url: o.url, link: `https://open.spotify.com/artist/${id}` } : null;
      });
    },
  };
}
