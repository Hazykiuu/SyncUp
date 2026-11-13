// Leitor do histórico no navegador (regras de dados.py). Rodar: node --test tests/js/*.test.mjs
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { deflateRawSync } from 'node:zlib';

import { LIMITE_ENTRADA, entradaIgnorada, familiaPlataforma, instanteUtc, lerHistorico, normalizarNome } from '../../site/app/js/historico.js';

// ZIP mínimo (sem CRC: o leitor não confere). `mentir` declara um tamanho menor que o real.
function zip(arquivos, { metodo = 8, mentir = false, declarar } = {}) {
  const partes = [], diretorio = [];
  let pos = 0;
  for (const [nome, texto] of Object.entries(arquivos)) {
    const nomeB = Buffer.from(nome), dados = Buffer.from(texto), comp = metodo === 8 ? deflateRawSync(dados) : dados;
    const tamanho = declarar ?? (mentir ? Math.max(1, dados.length - 10) : dados.length);
    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0); local.writeUInt16LE(metodo, 8);
    local.writeUInt32LE(comp.length, 18); local.writeUInt32LE(tamanho, 22); local.writeUInt16LE(nomeB.length, 26);
    const central = Buffer.alloc(46);
    central.writeUInt32LE(0x02014b50, 0); central.writeUInt16LE(metodo, 10);
    central.writeUInt32LE(comp.length, 20); central.writeUInt32LE(tamanho, 24); central.writeUInt16LE(nomeB.length, 28);
    central.writeUInt32LE(pos, 42);
    partes.push(local, nomeB, comp);
    diretorio.push(central, nomeB);
    pos += 30 + nomeB.length + comp.length;
  }
  const dir = Buffer.concat(diretorio), fim = Buffer.alloc(22);
  fim.writeUInt32LE(0x06054b50, 0); fim.writeUInt16LE(diretorio.length / 2, 8); fim.writeUInt16LE(diretorio.length / 2, 10);
  fim.writeUInt32LE(dir.length, 12); fim.writeUInt32LE(pos, 16);
  return new Uint8Array(Buffer.concat([...partes, dir, fim]));
}

const ev = (ts, artista, musica = 'Faixa', ms = 60_000, extra = {}) => ({
  ts, ms_played: ms, master_metadata_track_name: musica, master_metadata_album_artist_name: artista, ...extra,
});
const json = (eventos) => JSON.stringify(eventos);
const ler = (arquivos, opcoes) => lerHistorico(Object.entries(arquivos).map(([nome, bytes]) => ({ nome, bytes })), opcoes);
const isoLocal = (ms) => new Date(ms).toISOString().slice(0, 19);

test('lê o ZIP do Spotify e descarta o que o Python descarta', async () => {
  const eventos = [
    ev('2024-01-01T12:00:00Z', ' Ana ', ' Hit ', 60_000, { skipped: false, shuffle: true, offline: false, platform: 'Android OS 13 (moto g)', reason_end: 'trackdone', spotify_track_uri: 'spotify:track:abc' }),
    ev('2024-01-01T13:00:00Z', 'Ana', 'Ep', 60_000, { episode_name: 'Episódio' }), // podcast
    ev('2024-01-01T14:00:00Z', 'Ana', 'Hit', -1), // ms inválido
    ev('2024-01-01T15:00:00Z', 'Ana', 'Hit', true), // booleano não é número
    ev('2024-02-30T15:00:00Z', 'Ana', 'Hit'), // data impossível
    ev('2024-01-01T16:00:00Z', '   ', 'Hit'), // sem artista
    ev('2024-01-01T17:00:00Z', 'Bia', null),
    ev('2024-01-01T18:00:00Z', 'Bia', 'Outra', '45000'), // número em texto vale (pandas aceita)
    'não é um evento',
  ];
  const c = await ler({
    'h.zip': zip({
      'Spotify Extended Streaming History/Streaming_History_Audio_2024.json': json(eventos),
      'Spotify Extended Streaming History/ReadMeFirst.pdf': 'pdf',
      '__MACOSX/._Streaming_History_Audio_2024.json': 'lixo',
      'Spotify Extended Streaming History/Userdata.json': json({ username: 'x' }), // não é lista de histórico
    }),
  });
  assert.deepEqual(c.musica, ['Hit', 'Outra']);
  assert.deepEqual(c.artista, ['Ana', 'Bia']);
  assert.deepEqual(c.ms, [60_000, 45_000]);
  assert.deepEqual([c.pulada[0], c.aleatorio[0], c.offline[0], c.plataforma[0], c.motivo[0], c.uri[0]], [false, true, false, 'Android', 'trackdone', 'spotify:track:abc']);
  assert.deepEqual([c.pulada[1], c.plataforma[1], c.uri[1]], [null, null, null]);
  assert.equal(isoLocal(c.local[0]), '2024-01-01T09:00:00'); // São Paulo, UTC-3
});

test('JSON solto com BOM, ZIP sem compressão e as opções de dados', async () => {
  const eventos = [
    ev('2024-01-01T12:00:00Z', 'Various Artists', 'Coletânea'),
    ev('2024-01-01T12:00:00Z', 'Ana', 'Hit'),
    ev('2024-01-01T12:00:00Z', 'Ana', 'Hit'), // repetido no mesmo instante
    ev('2024-01-01T13:00:00Z', 'Zé', '(Falsa) Esperança'),
  ];
  const bom = new Uint8Array([0xef, 0xbb, 0xbf, ...Buffer.from(json(eventos))]);
  assert.equal((await ler({ 'a.json': bom })).utc.length, 4);
  assert.equal((await ler({ 'a.zip': zip({ 'a.json': json(eventos) }, { metodo: 0 }) })).utc.length, 4);
  const c = await ler({ 'a.json': bom }, { varios: 'ignorar', deduplicar: true, musicas: ' falsa esperança \n', fuso: 'Europe/Lisbon' });
  assert.deepEqual(c.musica, ['Hit']);
  assert.equal(isoLocal(c.local[0]), '2024-01-01T12:00:00'); // Lisboa no inverno = UTC
  assert.equal((await ler({ 'a.json': bom }, { artistas: 'ZÉ' })).utc.length, 3);
});

test('partes: deduplica entre arquivos e recusa a mesma parte duas vezes', async () => {
  const a = Buffer.from(json([ev('2024-01-01T12:00:00Z', 'Ana', 'Hit')]));
  const b = Buffer.from(json([ev('2024-01-01T12:00:00Z', 'Ana', 'Hit'), ev('2024-01-02T12:00:00Z', 'Bia', 'Outra')]));
  assert.equal((await ler({ 'a.json': a, 'b.json': b })).utc.length, 3);
  assert.equal((await ler({ 'a.json': a, 'b.json': b }, { deduplicar: true })).utc.length, 2);
  await assert.rejects(ler({ 'a.json': a, 'c.json': Buffer.from(a) }), /mesmo conteúdo/);
});

test('horário de verão de São Paulo (2018): a hora local segue a troca', async () => {
  const c = await ler({ 'a.json': Buffer.from(json([ev('2018-11-04T02:30:00Z', 'Ana'), ev('2018-11-04T03:30:00Z', 'Ana'), ev('2019-02-17T02:30:00Z', 'Ana')])) });
  assert.deepEqual(c.local.map(isoLocal), ['2018-11-03T23:30:00', '2018-11-04T01:30:00', '2019-02-16T23:30:00']);
});

test('erros com as mensagens do Python', async () => {
  const bom = zip({ 'a.json': json([ev('2024-01-01T12:00:00Z', 'Ana')]) });
  await assert.rejects(ler({ 'a.zip': bom.subarray(0, bom.length - 30) }), /ZIP está inválido/);
  await assert.rejects(ler({ 'a.zip': zip({ 'a.json': json([ev('2024-01-01T12:00:00Z', 'Ana', 'Uma música com nome comprido')]) }, { mentir: true }) }), /ZIP está inválido/);
  // Entrada declarada acima do teto: recusada antes de alocar (sem precisar de 65 MB de verdade).
  await assert.rejects(ler({ 'a.zip': zip({ 'a.json': '[]' }, { declarar: LIMITE_ENTRADA + 1 }) }), /grande demais para o navegador/);
  await assert.rejects(ler({ 'a.zip': zip({ 'a.json': '[{"ts": ' }) }), /JSON inválido/);
  await assert.rejects(ler({ 'a.json': new Uint8Array([0x5b, 0xff, 0x5d]) }), /UTF-8/);
  await assert.rejects(ler({ 'a.json': Buffer.from(json([{ ts: '2024-01-01T12:00:00Z', ms_played: 1 }])) }), /histórico estendido/);
  await assert.rejects(ler({ 'a.txt': Buffer.from('[]') }), /ZIP ou JSON/);
  await assert.rejects(ler({ 'a.json': Buffer.from('[]') }, { fuso: 'Marte/Olympus' }), /Fuso inválido/);
  await assert.rejects(ler({}), /pelo menos um/);
});

test('ajudantes: nomes, plataformas, entradas e datas', () => {
  assert.equal(normalizarNome('  Various   Artists!! '), 'variousartists');
  assert.equal(normalizarNome('Straße'), normalizarNome('STRASSE')); // casefold do Python
  assert.equal(normalizarNome('Ação_1'), 'ação1');
  assert.equal(familiaPlataforma('web_player windows 10'), 'Navegador');
  assert.equal(familiaPlataforma('iOS 17.1 (iPhone15,2)'), 'iOS');
  assert.equal(familiaPlataforma('not_applicable'), null);
  assert.equal(familiaPlataforma('Geladeira'), 'Outro');
  assert.ok(entradaIgnorada('pasta/') && entradaIgnorada('a/__MACOSX/x.json') && entradaIgnorada('a/._x.json') && entradaIgnorada('a/x.pdf'));
  assert.ok(!entradaIgnorada('Spotify Extended Streaming History/Streaming_History_Audio_2024.JSON'));
  assert.equal(instanteUtc('2024-02-29T10:00:00Z'), Date.UTC(2024, 1, 29, 10));
  assert.equal(instanteUtc('2024-01-01 10:00:00+01:00'), Date.UTC(2024, 0, 1, 9));
  assert.equal(instanteUtc('2024-01-01T10:00:00'), Date.UTC(2024, 0, 1, 10)); // sem fuso = UTC
  assert.equal(instanteUtc('2024-01-01'), Date.UTC(2024, 0, 1)); // só a data = meia-noite
  assert.equal(instanteUtc('2024-01-01T10:30'), Date.UTC(2024, 0, 1, 10, 30)); // sem segundos
  for (const ruim of ['2023-02-29T10:00:00Z', '2024-01-01T24:00:00Z', '2024-13-01T00:00:00Z', 'ontem', null]) assert.ok(Number.isNaN(instanteUtc(ruim)), ruim);
});
