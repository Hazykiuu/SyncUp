// Convite por código (o mesmo formato de convite.py): "SYNCUP1." + base64url(zlib(JSON compacto)).
// Só os rankings viajam. O código vem de fora: tudo é conferido antes de virar perfil.
import { PERIODOS, TAMANHO_RANKING } from './match.js';

export const PREFIXO = 'SYNCUP1.';
const MAXIMO_CODIGO = 20_000; // caracteres: um código real tem ~3 mil
const MAXIMO_JSON = 100_000; // bytes depois de descompactar: barra "zip bomb" no código
const MAXIMO_NOME = 60;
const MAXIMO_TEXTO = 200;
const ALTERADO = 'O convite está incompleto ou foi alterado. Copie o código inteiro de novo.';

const tamanho = (s) => [...s].length; // pontos de código, como o len() do Python

const SEM_SUPORTE = 'Este navegador não sabe abrir convites. Atualize o navegador ou use outro (Chrome, Firefox, Safari 16.4+).';

async function passar(bytes, stream, limite = Infinity) {
  const leitor = new Blob([bytes]).stream().pipeThrough(stream).getReader();
  const partes = [];
  let total = 0;
  for (;;) {
    const { done, value } = await leitor.read();
    if (done) break;
    total += value.length;
    if (total > limite) { await leitor.cancel(); throw new Error(ALTERADO); }
    partes.push(value);
  }
  return new Uint8Array(await new Blob(partes).arrayBuffer());
}

export async function gerarConvite(perfil) {
  if (typeof CompressionStream === 'undefined') throw new Error(SEM_SUPORTE);
  const dados = {
    n: [...perfil.nome.trim()].slice(0, MAXIMO_NOME).join(''),
    a: Object.fromEntries(PERIODOS.map((p) => [p, (perfil.top_artistas[p] || []).slice(0, TAMANHO_RANKING)])),
    m: Object.fromEntries(PERIODOS.map((p) => [p, (perfil.top_musicas[p] || []).slice(0, TAMANHO_RANKING).map((m) => [m.musica, m.artista])])),
  };
  const z = await passar(new TextEncoder().encode(JSON.stringify(dados)), new CompressionStream('deflate'));
  let bin = '';
  for (const b of z) bin += String.fromCharCode(b);
  return PREFIXO + btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function texto(v, limite = MAXIMO_TEXTO) {
  if (typeof v !== 'string' || !v.trim() || tamanho(v) > limite) throw new Error(ALTERADO);
  return v.trim();
}
function lista(v) {
  if (!Array.isArray(v) || v.length > TAMANHO_RANKING) throw new Error(ALTERADO);
  return v;
}
const objeto = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);

export async function lerConvite(codigo) {
  codigo = (codigo || '').replace(/\s+/g, ''); // tolera quebras de linha do aplicativo de mensagem
  if (!codigo.startsWith(PREFIXO)) throw new Error('Isso não parece um convite do SyncUp (ele começa com "SYNCUP1.").');
  if (tamanho(codigo) > MAXIMO_CODIGO) throw new Error('O convite é grande demais. Peça para a pessoa gerar de novo.');
  if (typeof DecompressionStream === 'undefined') throw new Error(SEM_SUPORTE);
  let nome, top_artistas, top_musicas;
  try {
    const bin = atob(codigo.slice(PREFIXO.length).replace(/-/g, '+').replace(/_/g, '/'));
    const dados = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(
      await passar(Uint8Array.from(bin, (c) => c.charCodeAt(0)), new DecompressionStream('deflate'), MAXIMO_JSON)));
    if (!objeto(dados) || !objeto(dados.a) || !objeto(dados.m)) throw new Error(ALTERADO);
    nome = texto(dados.n, MAXIMO_NOME);
    top_artistas = Object.fromEntries(PERIODOS.map((p) => [p, lista(dados.a[p] ?? []).map((a) => texto(a))]));
    top_musicas = Object.fromEntries(PERIODOS.map((p) => [p, lista(dados.m[p] ?? [])
      .filter((m) => Array.isArray(m) && m.length === 2).map(([musica, artista]) => ({ musica: texto(musica), artista: texto(artista) }))]));
  } catch {
    throw new Error(ALTERADO);
  }
  if (!PERIODOS.some((p) => top_artistas[p].length)) throw new Error(`O convite de ${nome} não tem nenhum ranking de artistas.`);
  return { nome, fonte: 'convite', top_artistas, top_musicas };
}

// Um por linha, ou quebrados pelo aplicativo de mensagem: pedaço sem o prefixo continua o código anterior.
export function separarConvites(textoColado) {
  const codigos = [];
  for (const pedaco of (textoColado || '').split(/\s+/).filter(Boolean)) {
    if (pedaco.startsWith(PREFIXO) || !codigos.length) codigos.push(pedaco);
    else codigos[codigos.length - 1] += pedaco;
  }
  return codigos;
}
