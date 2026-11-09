// Busca de capas e fotos com fetch falso (sem rede). Rodar: node --test tests/js
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { cacheMemoria, criarBuscador, HOSTS_AUDIO, HOSTS_IMAGEM, idFaixa, urlSegura } from '../../site/app/js/capas.js';

const ID = '4cOdK2wGLETKBW3PvgPWqT';
const ARTISTA = '6tw6EpC9RgmSRZiZg0n22t';
const resposta = (status, corpo) => ({ ok: status === 200, status, json: async () => corpo });

// Servidor falso: responde por trecho da URL e registra os pedidos.
function falso(rotas) {
  const pedidos = [];
  const fetch = async (url) => {
    pedidos.push(url);
    const rota = rotas.find(([trecho]) => url.includes(trecho));
    const r = rota ? rota[1] : resposta(404, {});
    return typeof r === 'function' ? r() : r;
  };
  return { fetch, pedidos };
}
const esperas = [];
const esperar = async (ms) => { esperas.push(ms); };

const mbBusca = (nome) => ['musicbrainz.org/ws/2/artist/?query', resposta(200, { artists: [{ id: 'mb1', name: nome }] })];
const mbLinks = ['musicbrainz.org/ws/2/artist/mb1', resposta(200, { relations: [{ url: { resource: `https://open.spotify.com/artist/${ARTISTA}` } }] })];
const oembedArtista = (titulo) => [`artist%2F${ARTISTA}`, resposta(200, { title: titulo, thumbnail_url: 'https://i.scdn.co/image/foto' })];

test('só IDs reais vão à rede (dados fictícios ficam de fora)', async () => {
  assert.equal(idFaixa(`spotify:track:${ID}`), ID);
  assert.equal(idFaixa('spotify:track:ficticio_1559_08'), null);
  assert.equal(idFaixa(null), null);
  const { fetch, pedidos } = falso([]);
  const b = criarBuscador({ fetch, esperar, cache: cacheMemoria() });
  assert.equal(await b.faixa('spotify:track:ficticio_1559_08'), null);
  assert.equal(pedidos.length, 0);
});

test('capa da faixa pelo oEmbed, com cache na segunda vez', async () => {
  const { fetch, pedidos } = falso([[`track%2F${ID}`, resposta(200, { title: 'X', thumbnail_url: 'https://i.scdn.co/image/capa' })]]);
  const cache = cacheMemoria();
  const b = criarBuscador({ fetch, esperar, cache });
  assert.deepEqual(await b.faixa(`spotify:track:${ID}`), { url: 'https://i.scdn.co/image/capa', link: `https://open.spotify.com/track/${ID}` });
  await criarBuscador({ fetch, esperar, cache }).faixa(`spotify:track:${ID}`);
  assert.equal(pedidos.length, 1);
});

test('foto do artista: MusicBrainz → Spotify, conferindo o nome nas duas pontas', async () => {
  const { fetch } = falso([mbBusca('Legião Urbana'), mbLinks, oembedArtista('Legião Urbana')]);
  const b = criarBuscador({ fetch, esperar, cache: cacheMemoria() });
  assert.deepEqual(await b.artista('LEGIAO URBANA'), { url: 'https://i.scdn.co/image/foto', link: `https://open.spotify.com/artist/${ARTISTA}` });
  // O MusicBrainz espera ~1,1 s entre as duas consultas.
  assert.ok(esperas.some((ms) => ms >= 1000));
});

test('nome diferente em qualquer ponta → sem foto (nunca a foto errada)', async () => {
  const outroNoMb = falso([mbBusca('Legião Urbana Cover'), mbLinks, oembedArtista('Legião Urbana')]);
  assert.equal(await criarBuscador({ fetch: outroNoMb.fetch, esperar, cache: cacheMemoria() }).artista('Legião Urbana'), null);
  const outroNoSpotify = falso([mbBusca('Legião Urbana'), mbLinks, oembedArtista('Renato Russo')]);
  assert.equal(await criarBuscador({ fetch: outroNoSpotify.fetch, esperar, cache: cacheMemoria() }).artista('Legião Urbana'), null);
});

test('429 espera dobrando e tenta de novo; sem rede não grava no cache', async () => {
  let vez = 0;
  const { fetch } = falso([[`track%2F${ID}`, () => (++vez < 3 ? resposta(429, {}) : resposta(200, { thumbnail_url: 'https://i.scdn.co/image/u' }))]]);
  esperas.length = 0;
  assert.equal((await criarBuscador({ fetch, esperar, cache: cacheMemoria() }).faixa(`spotify:track:${ID}`)).url, 'https://i.scdn.co/image/u');
  assert.deepEqual(esperas, [2000, 4000]);

  const cache = cacheMemoria();
  const semRede = criarBuscador({ fetch: async () => { throw new TypeError('offline'); }, esperar, cache });
  assert.equal(await semRede.faixa(`spotify:track:${ID}`), null);
  assert.equal(await cache.ler(`t:${ID}`), undefined);

  // Recusou as 4 vezes: sem imagem agora, e nada gravado (não vira "não achou" por 30 dias).
  const ocupado = criarBuscador({ fetch: falso([[`track%2F${ID}`, resposta(503, {})]]).fetch, esperar, cache });
  assert.equal(await ocupado.faixa(`spotify:track:${ID}`), null);
  assert.equal(await cache.ler(`t:${ID}`), undefined);
});

test('só imagens e trechos dos domínios esperados, em https', async () => {
  assert.equal(urlSegura('https://i.scdn.co/image/x', HOSTS_IMAGEM), 'https://i.scdn.co/image/x');
  assert.equal(urlSegura('https://image-cdn-ak.spotifycdn.com/image/x', HOSTS_IMAGEM), 'https://image-cdn-ak.spotifycdn.com/image/x');
  assert.equal(urlSegura('http://i.scdn.co/image/x', HOSTS_IMAGEM), null);
  assert.equal(urlSegura('https://i.scdn.co.ruim.com/x', HOSTS_IMAGEM), null);
  assert.equal(urlSegura('javascript:alert(1)', HOSTS_IMAGEM), null);
  assert.equal(urlSegura(undefined, HOSTS_IMAGEM), null);
  assert.ok(urlSegura('https://audio-ssl.itunes.apple.com/a.m4a', HOSTS_AUDIO));
  // oEmbed adulterado apontando para outro servidor → sem capa.
  const { fetch } = falso([[`track%2F${ID}`, resposta(200, { thumbnail_url: 'https://rastreio.exemplo/pixel.gif' })]]);
  assert.equal(await criarBuscador({ fetch, esperar, cache: cacheMemoria() }).faixa(`spotify:track:${ID}`), null);
});

test('cache vencido é apagado ao criar o buscador; "apagar tudo" esvazia', async () => {
  const cache = cacheMemoria();
  await cache.gravar('t:velha', { valor: null, quando: 0 });
  await cache.gravar('t:nova', { valor: null, quando: Date.now() });
  const b = criarBuscador({ fetch: falso([]).fetch, esperar, cache });
  await new Promise((r) => setTimeout(r, 0));
  assert.equal(await cache.ler('t:velha'), undefined);
  assert.ok(await cache.ler('t:nova'));
  await b.apagarTudo();
  assert.equal(await cache.ler('t:nova'), undefined);
});
