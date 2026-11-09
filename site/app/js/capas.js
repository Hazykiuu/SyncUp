// Capas e fotos do Wrapped, só depois do opt-in ("Começar com capas e som").
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
  };
}

export function cacheMemoria() {
  const m = new Map();
  return { ler: async (k) => m.get(k), gravar: async (k, v) => { m.set(k, v); } };
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
  const spotify = limitador(PARALELO, 0, esperar);
  const musicbrainz = limitador(1, INTERVALO_MB, esperar);

  // 429/503: espera dobrando (2 s, 4 s, 8 s); depois de 3 recusas, segue sem imagem.
  async function json(url, vez) {
    for (let tentativa = 0; tentativa < 4; tentativa++) {
      const r = await vez(() => fetch(url));
      if (r.ok) return r.json();
      if (r.status !== 429 && r.status !== 503) return null;
      if (tentativa < 3) await esperar(2000 * 2 ** tentativa);
    }
    return null;
  }
  const oembed = async (tipo, id) => {
    const d = await json(OEMBED + encodeURIComponent(`https://open.spotify.com/${tipo}/${id}`), spotify);
    return d?.thumbnail_url ? { url: d.thumbnail_url, titulo: d.title || '' } : null;
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
