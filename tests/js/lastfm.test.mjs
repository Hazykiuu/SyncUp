// Importação do Last.fm com fetch e relógio falsos (sem rede). Rodar: node --test tests/js
import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  baixarDuracoes, baixarScrobbles, capaDoScrobble, chave, historicoDoLastfm, paraFormatoSpotify, pedir, USUARIO_VALIDO,
} from '../../site/app/js/lastfm.js';

const resposta = (corpo, status = 200) => ({ ok: status === 200, status, json: async () => corpo });

// Last.fm falso: responde por método e página, e guarda os pedidos.
function lastfm({ recentes = [], top = [], porPagina = 200, topPorPagina = 1000, totalTop } = {}) {
  const pedidos = [];
  const buscar = async (url) => {
    const p = new URL(url).searchParams;
    pedidos.push(Object.fromEntries(p));
    const pagina = Number(p.get('page') || 1);
    if (p.get('method') === 'user.getrecenttracks') {
      const desde = Number(p.get('from') || 0);
      const lista = recentes.filter((t) => !t.date || Number(t.date.uts) >= desde);
      const totalPages = Math.ceil(lista.length / porPagina);
      return resposta({ recenttracks: { track: lista.slice((pagina - 1) * porPagina, pagina * porPagina), '@attr': { page: String(pagina), totalPages: String(totalPages), total: String(lista.length) } } });
    }
    if (p.get('method') === 'user.gettoptracks') {
      return resposta({ toptracks: { track: top.slice((pagina - 1) * topPorPagina, pagina * topPorPagina), '@attr': { page: String(pagina), totalPages: String(totalTop ?? Math.ceil(top.length / topPorPagina)) } } });
    }
    return resposta({ error: 3, message: 'Invalid Method' });
  };
  return { buscar, pedidos };
}
const scrobble = (uts, musica = 'Faixa', artista = 'Banda') => ({ name: musica, artist: { '#text': artista }, date: { uts: String(uts) } });
const faixaTop = (musica, artista, duracao) => ({ name: musica, artist: { name: artista }, duration: String(duracao) });
const semEspera = { esperar: async () => {} };
function memoria() {
  const m = new Map();
  return { ler: async (k) => m.get(k), gravar: async (k, v) => { m.set(k, v); }, m };
}

// --- Erros: o Last.fm responde HTTP 200 com { error } ---------------------------------------------

test('erro 6 (usuário não existe) vira mensagem própria, mesmo com HTTP 200', async () => {
  const buscar = async () => resposta({ error: 6, message: 'User not found' });
  await assert.rejects(pedir('user.getrecenttracks', { user: 'ninguem' }, { buscar, ...semEspera }), (e) => e.codigo === 6 && /não achamos/i.test(e.message));
});

test('erro 17 (perfil privado) explica como liberar as escutas', async () => {
  const buscar = async () => resposta({ error: 17, message: 'Login required' });
  await assert.rejects(pedir('user.getrecenttracks', { user: 'fechado' }, { buscar, ...semEspera }), (e) => e.codigo === 17 && /ocultar escutas recentes/i.test(e.message));
});

test('código desconhecido vira mensagem genérica com o número', async () => {
  const buscar = async () => resposta({ error: 26, message: 'Suspended API key' });
  await assert.rejects(pedir('user.getrecenttracks', { user: 'alguem' }, { buscar, ...semEspera }), (e) => e.codigo === 26 && /código 26/.test(e.message));
});

test('erro 8 com HTTP 500 (falha passageira do Last.fm) tenta de novo', async () => {
  let chamadas = 0;
  const buscar = async () => (++chamadas < 3 ? resposta({ error: 8, message: 'Operation failed' }, 500) : resposta({ ok: 1 }));
  assert.deepEqual(await pedir('user.getrecenttracks', { user: 'alguem' }, { buscar, ...semEspera }), { ok: 1 });
  const sempre500 = async () => resposta('<html>', 503);
  await assert.rejects(pedir('m', {}, { buscar: sempre500, ...semEspera }), (e) => e.codigo === 503);
});

test('erro 29 (limite) tenta de novo com espera crescente e desiste depois de 4 vezes', async () => {
  const esperas = [];
  let chamadas = 0;
  const buscar = async () => { chamadas++; return resposta({ error: 29, message: 'Rate limit exceeded' }); };
  await assert.rejects(pedir('user.getrecenttracks', { user: 'alguem' }, { buscar, esperar: async (ms) => { esperas.push(ms); } }), (e) => e.codigo === 29);
  assert.deepEqual(esperas, [1000, 2000, 4000, 8000]);
  assert.equal(chamadas, 5);
});

test('erro 29 seguido de sucesso devolve os dados', async () => {
  let chamadas = 0;
  const buscar = async () => (++chamadas < 3 ? resposta({ error: 29 }) : resposta({ ok: 1 }));
  assert.deepEqual(await pedir('user.getrecenttracks', { user: 'alguem' }, { buscar, ...semEspera }), { ok: 1 });
});

test('sem rede: mensagem de conexão; cancelado: AbortError passa direto', async () => {
  const semRede = async () => { throw new TypeError('Failed to fetch'); };
  await assert.rejects(pedir('m', {}, { buscar: semRede, ...semEspera }), /conexão/i);
  const cancelado = async () => { throw new DOMException('parou', 'AbortError'); };
  await assert.rejects(pedir('m', {}, { buscar: cancelado, ...semEspera }), (e) => e.name === 'AbortError');
});

test('pedido que passa do tempo limite tenta de novo; sempre pendurado vira mensagem de demora', async () => {
  const demora = () => { throw new DOMException('timeout', 'TimeoutError'); };
  let chamadas = 0;
  const umaVez = async () => (++chamadas === 1 ? demora() : resposta({ ok: 1 }));
  assert.deepEqual(await pedir('m', {}, { buscar: umaVez, ...semEspera }), { ok: 1 });
  await assert.rejects(pedir('m', {}, { buscar: async () => demora(), ...semEspera }), /demorando/);
});

test('cada pedido leva um sinal com tempo limite, além do cancelamento', async () => {
  let recebido;
  const ctl = new AbortController();
  await pedir('m', {}, { buscar: async (_, op) => { recebido = op.signal; return resposta({}); }, sinal: ctl.signal, ...semEspera });
  assert.ok(recebido instanceof AbortSignal && recebido !== ctl.signal);
  ctl.abort();
  assert.ok(recebido.aborted);
});

test('só vai para ws.audioscrobbler.com em https, com format=json', async () => {
  let url;
  await pedir('user.getrecenttracks', { user: 'a1' }, { buscar: async (u) => { url = new URL(u); return resposta({}); }, ...semEspera });
  assert.equal(url.origin, 'https://ws.audioscrobbler.com');
  assert.equal(url.searchParams.get('format'), 'json');
});

test('nome de usuário: regras do Last.fm (2 a 15, começa com letra)', () => {
  for (const ok of ['rj', 'Carlos_99', 'a-b-c']) assert.ok(USUARIO_VALIDO.test(ok), ok);
  for (const ruim of ['', 'a', '9abc', 'nome com espaço', 'a'.repeat(16), 'x&api_key=1', '../a']) assert.ok(!USUARIO_VALIDO.test(ruim), ruim);
});

test('usuário inválido nem chega à rede', async () => {
  const { buscar, pedidos } = lastfm();
  await assert.rejects(baixarScrobbles('a b', { buscar, ...semEspera }), /usuário/i);
  assert.equal(pedidos.length, 0);
});

// --- "Tocando agora" e paginação --------------------------------------------------------------------

test('pula a faixa "tocando agora" e qualquer faixa sem date.uts', async () => {
  const recentes = [
    { name: 'Ao vivo', artist: { '#text': 'X' }, '@attr': { nowplaying: 'true' }, date: { uts: '100' } },
    { name: 'Sem data', artist: { '#text': 'X' } },
    { name: 'Data vazia', artist: { '#text': 'X' }, date: {} },
    scrobble(1700000000, 'Valeu', 'Y'),
  ];
  const { buscar } = lastfm({ recentes });
  const lista = await baixarScrobbles('carlos', { buscar, ...semEspera });
  assert.deepEqual(lista, [{ uts: 1700000000, musica: 'Valeu', artista: 'Y' }]);
});

test('respeita totalPages, baixa em paralelo a no máximo 4 pedidos por segundo, e o tempo restante diminui', async () => {
  const recentes = Array.from({ length: 450 }, (_, i) => scrobble(1700000000 - i));
  const { buscar, pedidos } = lastfm({ recentes });
  let t = 0;
  const esperas = [];
  const progresso = [];
  const inicios = [];
  const lista = await baixarScrobbles('carlos', {
    buscar: (u) => { inicios.push(t); return buscar(u); }, agora: () => t, esperar: async (ms) => { esperas.push(ms); t += ms; },
    aoProgresso: (p) => { progresso.push(p); t += 50; },
  });
  assert.equal(lista.length, 450);
  assert.equal(pedidos.length, 3);
  assert.ok(pedidos.every((p) => p.limit === '200'));
  assert.equal(new Set(pedidos.map((p) => p.page)).size, 3); // cada página uma vez, mesmo em paralelo
  assert.ok(esperas.length >= 2);
  // Cada pedido começa pelo menos 250 ms depois do anterior (relógio falso que só anda nas esperas).
  const reservas = inicios.slice(1).map((_, k) => esperas.slice(0, k + 1).reduce((a, b) => a + b, 0));
  assert.ok(reservas.every((r, k) => k === 0 || r - reservas[k - 1] >= 250), JSON.stringify({ inicios, esperas }));
  assert.deepEqual(progresso.map((p) => [p.pagina, p.paginas, p.total]), [[1, 3, 450], [2, 3, 450], [3, 3, 450]]);
  assert.ok(progresso[0].restanteMs > progresso[1].restanteMs && progresso[2].restanteMs === 0);
});

test('para quando o sinal cancela', async () => {
  const recentes = Array.from({ length: 1000 }, (_, i) => scrobble(1700000000 - i));
  const { buscar, pedidos } = lastfm({ recentes });
  const ctl = new AbortController();
  await assert.rejects(baixarScrobbles('carlos', { buscar, ...semEspera, sinal: ctl.signal, aoProgresso: () => ctl.abort() }), (e) => e.name === 'AbortError');
  assert.equal(pedidos.length, 1);
});

test('capa do álbum: só a do CDN do Last.fm, sem a estrela de "sem capa"', () => {
  const img = (url) => ({ image: [{ size: 'small', '#text': 'https://lastfm.freetls.fastly.net/i/u/34s/x.jpg' }, { size: 'extralarge', '#text': url }] });
  assert.equal(capaDoScrobble(img('https://lastfm.freetls.fastly.net/i/u/300x300/abc.jpg')), 'https://lastfm.freetls.fastly.net/i/u/300x300/abc.jpg');
  assert.equal(capaDoScrobble(img('https://lastfm-img.freetls.fastly.net/i/u/300x300/abc.png')), 'https://lastfm-img.freetls.fastly.net/i/u/300x300/abc.png');
  assert.equal(capaDoScrobble(img('https://lastfm.freetls.fastly.net/i/u/300x300/2a96cbd8b46e442fc41c2b86b821562f.png')), null);
  assert.equal(capaDoScrobble(img('http://lastfm.freetls.fastly.net/i/u/300x300/abc.jpg')), null);
  assert.equal(capaDoScrobble(img('https://outro.site/abc.jpg')), null);
  assert.equal(capaDoScrobble(img('')), null);
  assert.equal(capaDoScrobble({}), null);
});

test('as capas vêm no resultado e ficam no cache (a escuta mais nova manda)', async () => {
  const armazem = memoria();
  const comCapa = (uts, musica, id) => ({ ...scrobble(uts, musica), image: [{ size: 'extralarge', '#text': `https://lastfm.freetls.fastly.net/i/u/300x300/${id}.jpg` }] });
  const lf = lastfm({ recentes: [comCapa(1000, 'a', 'nova'), comCapa(900, 'a', 'velha'), scrobble(800, 'b')] });
  const r = await historicoDoLastfm('carlos', { buscar: lf.buscar, armazem, ...semEspera });
  assert.deepEqual([...r.capas], [[chave('Banda', 'a'), 'https://lastfm.freetls.fastly.net/i/u/300x300/nova.jpg']]);
  const de_novo = await historicoDoLastfm('carlos', { buscar: lf.buscar, armazem, ...semEspera });
  assert.equal(de_novo.capas.get(chave('Banda', 'a')), 'https://lastfm.freetls.fastly.net/i/u/300x300/nova.jpg');
});

// --- Durações --------------------------------------------------------------------------------------

test('durações: "0" fica fora, chaves normalizadas e só 3 páginas de getTopTracks', async () => {
  const top = [faixaTop('  Música Um ', 'BANDA ', 200), faixaTop('Sem Info', 'Banda', 0), faixaTop('Dois', 'Outra', '185')];
  const { buscar, pedidos } = lastfm({ top, totalTop: 40 });
  const mapa = await baixarDuracoes('carlos', { buscar, ...semEspera });
  assert.deepEqual([...mapa], [[chave('banda', 'música um'), 200000], [chave('Outra', 'Dois'), 185000]]);
  assert.equal(chave(' Banda', 'MÚSICA UM  '), 'banda|música um');
  const paginas = pedidos.filter((p) => p.method === 'user.gettoptracks').map((p) => p.page);
  assert.deepEqual(paginas, ['1', '2', '3']);
  assert.ok(pedidos.every((p) => p.period === 'overall' && p.limit === '1000'));
});

// --- Conversão para o formato do Spotify -------------------------------------------------------------

test('ts = início + duração; mediana para quem não tem duração; cobertura', () => {
  const duracoes = new Map([[chave('A', 'x'), 200000], [chave('B', 'y'), 100000], [chave('C', 'z'), 300000]]);
  const { json, cobertura } = paraFormatoSpotify([
    { uts: 1700000000, musica: 'X', artista: 'a' },
    { uts: 1700000500, musica: 'Nova', artista: 'Desconhecida' },
  ], duracoes);
  const eventos = JSON.parse(json);
  assert.deepEqual(eventos[0], { ts: '2023-11-14T22:16:40Z', ms_played: 200000, master_metadata_track_name: 'X', master_metadata_album_artist_name: 'a' });
  assert.equal(eventos[1].ms_played, 200000); // mediana de 100, 200 e 300 mil
  assert.equal(eventos[1].ts, new Date((1700000500 * 1000) + 200000).toISOString().replace('.000Z', 'Z'));
  assert.equal(cobertura, 0.5);
});

test('sem nenhuma duração conhecida: 3,5 min e cobertura 0', () => {
  const { json, cobertura } = paraFormatoSpotify([{ uts: 1700000000, musica: 'X', artista: 'a' }], new Map());
  assert.equal(JSON.parse(json)[0].ms_played, 210000);
  assert.equal(cobertura, 0);
});

test('JSON enxuto: só as 4 chaves, sem indentação, e 300 mil reproduções abaixo de 50 MB', () => {
  const scrobbles = Array.from({ length: 300000 }, (_, i) => ({ uts: 1500000000 + i * 180, musica: `Uma música de nome médio ${i % 997}`, artista: `Artista ${i % 251}` }));
  const { json } = paraFormatoSpotify(scrobbles, new Map([[chave('Artista 1', 'Uma música de nome médio 1'), 215000]]));
  assert.ok(!json.includes('\n') && !json.includes(': '));
  assert.deepEqual(Object.keys(JSON.parse(json.slice(0, json.indexOf('}') + 1) + ']')[0]), ['ts', 'ms_played', 'master_metadata_track_name', 'master_metadata_album_artist_name']);
  assert.ok(new TextEncoder().encode(json).length < 50 * 1048576, `${(json.length / 1048576).toFixed(1)} MB`);
});

// --- Cache (IndexedDB trocado por memória) ---------------------------------------------------------

test('segunda consulta pede só from = último uts + 1 e junta sem repetir', async () => {
  const armazem = memoria();
  const recentes = [scrobble(1000, 'a'), scrobble(900, 'b')];
  const lf = lastfm({ recentes, top: [faixaTop('a', 'Banda', 200)] });
  const primeira = await historicoDoLastfm('Carlos', { buscar: lf.buscar, armazem, ...semEspera });
  assert.equal(primeira.reproducoes, 2);
  assert.ok(armazem.m.has('carlos'));

  recentes.unshift(scrobble(1100, 'c'), scrobble(1000, 'a')); // a de novo: o Last.fm repete faixa quando a página desliza
  lf.pedidos.length = 0;
  const segunda = await historicoDoLastfm('CARLOS', { buscar: lf.buscar, armazem, ...semEspera });
  const recentesPedidos = lf.pedidos.filter((p) => p.method === 'user.getrecenttracks');
  assert.ok(recentesPedidos.every((p) => p.from === '1001'));
  assert.equal(lf.pedidos.filter((p) => p.method === 'user.gettoptracks').length, 0); // durações vêm do cache
  assert.equal(segunda.reproducoes, 3);
});

test('"Último ano" com cache completo filtra no aparelho, sem baixar o histórico de novo', async () => {
  const armazem = memoria();
  const agora = Date.UTC(2026, 10, 19) / 1000;
  const recentes = [scrobble(agora - 10 * 86400, 'recente'), scrobble(agora - 400 * 86400, 'antiga')];
  const lf = lastfm({ recentes });
  await historicoDoLastfm('carlos', { buscar: lf.buscar, armazem, agora: () => agora * 1000, ...semEspera });
  lf.pedidos.length = 0;
  const ano = await historicoDoLastfm('carlos', { periodo: 'ano', buscar: lf.buscar, armazem, agora: () => agora * 1000, ...semEspera });
  assert.equal(ano.reproducoes, 1);
  const recentesPedidos = lf.pedidos.filter((p) => p.method === 'user.getrecenttracks');
  assert.ok(recentesPedidos.every((p) => Number(p.from) > agora - 10 * 86400)); // só o que é novo
});

test('"Último ano" sem cache baixa só o último ano; depois "Todo o histórico" baixa o resto', async () => {
  const armazem = memoria();
  const agora = Date.UTC(2026, 10, 19) / 1000;
  const recentes = [scrobble(agora - 10 * 86400, 'recente'), scrobble(agora - 400 * 86400, 'antiga')];
  const lf = lastfm({ recentes });
  const ano = await historicoDoLastfm('carlos', { periodo: 'ano', buscar: lf.buscar, armazem, agora: () => agora * 1000, ...semEspera });
  assert.equal(ano.reproducoes, 1);
  assert.ok(lf.pedidos.some((p) => p.from === String(agora - 365 * 86400)));
  const tudo = await historicoDoLastfm('carlos', { buscar: lf.buscar, armazem, agora: () => agora * 1000, ...semEspera });
  assert.equal(tudo.reproducoes, 2);
});

test('cache que falha (aba anônima) não quebra: baixa tudo', async () => {
  const quebrado = { ler: async () => { throw new Error('IDB'); }, gravar: async () => { throw new Error('IDB'); } };
  const lf = lastfm({ recentes: [scrobble(1000)] });
  const r = await historicoDoLastfm('carlos', { buscar: lf.buscar, armazem: quebrado, ...semEspera });
  assert.equal(r.reproducoes, 1);
});

test('sem nenhum scrobble: erro claro', async () => {
  const lf = lastfm({ recentes: [] });
  await assert.rejects(historicoDoLastfm('carlos', { buscar: lf.buscar, armazem: memoria(), ...semEspera }), /nenhum scrobble/i);
});

// R3-11: o histórico guardado vence 7 dias depois do último uso.
test('cache vencido há mais de 7 dias é ignorado e o histórico é baixado de novo', async () => {
  const armazem = memoria();
  const recentes = [scrobble(1000, 'a')];
  const lf = lastfm({ recentes });
  const dia = 86_400_000;
  await historicoDoLastfm('carlos', { buscar: lf.buscar, armazem, agora: () => 100 * dia, ...semEspera });
  assert.equal(armazem.m.get('carlos').quando, 100 * dia);
  for (const [quando, doCache] of [[107 * dia, true], [115 * dia, false]]) {
    lf.pedidos.length = 0;
    await historicoDoLastfm('carlos', { buscar: lf.buscar, armazem, agora: () => quando, ...semEspera });
    const pedidos = lf.pedidos.filter((p) => p.method === 'user.getrecenttracks');
    assert.equal(pedidos.every((p) => p.from === '1001'), doCache, `${quando / dia}`);
  }
});
