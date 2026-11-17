// Números dos gráficos da Dupla no app web (desenhados em HTML por graficos.js, sem Plotly).
// São os mesmos números das figuras de graficos.py (o app para PC): paridade em tests/test_paridade_dupla.py.
// Aqui também ficam as frases dos títulos e as escalas: funções puras, testadas em tests/js/graficos.test.mjs.
import { fmtNum } from './dupla.js';
import { MESES } from './stories/logica.js';

export const VISIVEIS = 8; // artistas à vista em "Quem puxa"; o resto fica no "Ver mais"
export const LIMIARES = [60, 40, 40]; // perfis.LIMIAR_FAVORITOS, LIMIAR_REPEAT e LIMIAR_MADRUGADA, em %
const DIAS = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo'];

export const mesLongo = (m) => `${MESES[Number(m.slice(5)) - 1]}/${m.slice(0, 4)}`;
export const mesCurto = (m) => `${MESES[Number(m.slice(5)) - 1]}/${m.slice(2, 4)}`;
const pct = (x) => `${fmtNum(x, 1)}%`;
const maior = (lista) => lista.indexOf(Math.max(...lista));

const participacao = (b, plays, artista) => ((b.contagens.get(artista) || 0) / plays) * 100;

// As três proporções dos arquétipos (perfis.classificar_proporcoes), em fração.
function tracos(p, b) {
  const soma = (lista, n) => [...lista].sort((x, y) => y - x).slice(0, n).reduce((s, x) => s + x, 0);
  const madrugada = b.porHora.slice(0, 6).reduce((s, x) => s + x, 0); // 00h a 05h59
  return [soma(b.contagens.values(), 2) / p.plays, soma(b.faixas.values(), 10) / p.plays, madrugada / p.plays];
}

// Todos os meses do primeiro ao último dos dois; mês sem escuta de um lado (ou dos dois) vale 0 h.
function mesesContinuos(mapas) {
  const chaves = mapas.flatMap((m) => [...m.keys()]);
  if (!chaves.length) return [];
  const [ini, fim] = [Math.min(...chaves), Math.max(...chaves)];
  const meses = [];
  for (let m = ini; m <= fim; m = m % 100 === 12 ? m + 89 : m + 1) {
    const [a, b] = mapas.map((x) => (x.get(m) || 0) / 60);
    meses.push({ mes: `${Math.floor(m / 100)}-${String(m % 100).padStart(2, '0')}`, a, b });
  }
  return meses;
}

/** Os números dos 4 gráficos (`graficos` da resposta do app), a partir de compararDupla. */
export function graficosDupla(r) {
  const [pa, pb] = r.perfis, [ba, bb] = r._bruto;
  return {
    artistas: r.ordem.map((nome) => ({ nome, a: participacao(ba, pa.plays, nome), b: participacao(bb, pb.plays, nome) })),
    horas: [[ba, pa], [bb, pb]].map(([b, p]) => b.porHora.map((n) => (n / p.plays) * 100)),
    dias: [[ba, pa], [bb, pb]].map(([b, p]) => b.diaHora.map((linha) => (linha.reduce((s, n) => s + n, 0) / p.plays) * 100)),
    tracos: { a: tracos(pa, ba).map((x) => x * 100), b: tracos(pb, bb).map((x) => x * 100), limiares: LIMIARES },
    meses: mesesContinuos([ba.horasMes, bb.horasMes]),
    fuso: r.fuso,
  };
}

// ---- Escalas -------------------------------------------------------------------------------------

/** Largura (0–1) de cada meia-barra: pelo maior % dos 8 à vista; um extra maior trava em 1. */
export function escalaArtistas(artistas) {
  const topo = Math.max(...artistas.slice(0, VISIVEIS).flatMap((x) => [x.a, x.b]), 0) || 1;
  return (v) => Math.min(1, v / topo);
}

/** Altura (0–1) de cada barrinha da hora: pelo pico da própria pessoa. */
export const escalaHoras = (horas) => {
  const topo = Math.max(...horas) || 1;
  return horas.map((v) => v / topo);
};

/** Grade do eixo Y de "Horas por mês": 0, passo e 2 × passo, com passo "redondo" e topo ≥ 1. */
export function gradeHoras(meses) {
  const topo = Math.max(...meses.flatMap((m) => [m.a, m.b]), 1);
  const base = 10 ** Math.floor(Math.log10(topo / 2));
  // Passo de pelo menos 1 h: os rótulos são inteiros (fmtNum sem casas).
  const passo = Math.max(1, [1, 2, 5, 10].map((f) => f * base).find((x) => 2 * x >= topo));
  return { topo: 2 * passo, linhas: [0, passo, 2 * passo] };
}

/** Rótulos do eixo dos meses: primeiro, último e viradas de ano, sem dois a menos de 15% da largura. */
export function rotulosMeses(meses) {
  const n = meses.length;
  if (n <= 1) return n ? [{ i: 0, x: 50 }] : [];
  const x = (i) => (i / (n - 1)) * 100;
  const escolhidos = [0, n - 1];
  meses.forEach((m, i) => {
    if (m.mes.endsWith('-01') && escolhidos.every((j) => Math.abs(x(i) - x(j)) >= 15)) escolhidos.push(i);
  });
  return escolhidos.sort((p, q) => p - q).map((i) => ({ i, x: x(i) }));
}

// ---- Títulos -------------------------------------------------------------------------------------

const quaseIgual = (a, b) => a > 0 && b > 0 && (Math.abs(a - b) < 2 || Math.max(a, b) / Math.min(a, b) < 1.25);

function tituloArtistas(artistas, [na, nb]) {
  const vistos = artistas.slice(0, VISIVEIS);
  if (!vistos.length) return 'Nenhum artista para comparar neste período';
  // Só é "quase igual" quando todos os visíveis são; senão, a maior diferença entre os que não são.
  const diferentes = vistos.filter((y) => !quaseIgual(y.a, y.b));
  if (!diferentes.length) return 'Os dois puxam os favoritos quase igual';
  const x = diferentes.reduce((m, y) => (Math.abs(y.a - y.b) > Math.abs(m.a - m.b) ? y : m));
  const [mais, menos, nMais, nMenos] = x.a >= x.b ? [x.a, x.b, na, nb] : [x.b, x.a, nb, na];
  return `${x.nome} pesa mais para ${nMais}: ${pct(mais)} dos plays, contra ${pct(menos)} de ${nMenos}`;
}

// null: sem plays; -1: sem pico claro (o pico não chega a 1,2 × a média); senão, a hora do pico.
function pico(horas) {
  const soma = horas.reduce((s, x) => s + x, 0);
  if (soma <= 0) return null;
  const h = maior(horas);
  return horas[h] < 1.2 * (soma / 24) ? -1 : h;
}

function tituloHoras(horas, [na, nb]) {
  const [pa, pb] = horas.map(pico);
  const temPico = (p) => p !== null && p >= 0; // null >= 0 é true no JS
  if (pa === -1 && pb === -1) return 'Os dois ouvem o dia todo, sem hora de pico';
  if (temPico(pa) && pa === pb) return `Os dois ouvem mais às ${pa}h`;
  const frase = (nome, p, curta) => {
    if (p === null) return `${nome} não tem plays neste período`;
    if (p === -1) return `${nome} ouve o dia todo, sem hora de pico`;
    return curta ? `${nome}, às ${p}h` : `${nome} ouve mais às ${p}h`;
  };
  // "Ana ouve mais às 18h; Bruno, às 12h": a forma curta só quando as duas frases são de pico.
  return `${frase(na, pa, false)}; ${frase(nb, pb, temPico(pa) && temPico(pb))}`;
}

function linhaDias(dias, horas, fuso, nomes) {
  const ks = [0, 1].filter((k) => pico(horas[k]) !== null);
  const dia = (k) => DIAS[maior(dias[k])];
  let texto = ks.map((k) => `${nomes[k]}, ${dia(k)}`).join('; ');
  if (ks.length === 2 && dia(0) === dia(1)) texto = `${dia(0)} para os dois`;
  return `${texto ? `Dia com mais plays: ${texto}. ` : ''}Horário de ${fuso}.`;
}

const tracosTexto = (n) => (n === 0 ? 'nenhum' : n === 1 ? '1 traço' : `${n} traços`);
function tituloTracos({ a, b, limiares }, [na, nb]) {
  const [ta, tb] = [a, b].map((v) => v.filter((x, i) => x >= limiares[i]).length);
  if (!ta && !tb) return 'Nenhum dos dois atingiu os limiares de traço';
  if (ta === tb) return `Os dois têm ${tracosTexto(ta)}`;
  return `${na} tem ${tracosTexto(ta)}; ${nb}, ${tracosTexto(tb)}`;
}

function tituloMeses(meses, [na, nb]) {
  const topo = (k) => {
    const valores = meses.map((m) => (k ? m.b : m.a));
    return Math.max(...valores, 0) > 0 ? meses[maior(valores)] : null;
  };
  const [ma, mb] = [topo(0), topo(1)];
  const h = (x) => `${fmtNum(x, 0)} h`;
  if (!ma && !mb) return 'Nenhuma hora ouvida neste período';
  if (ma && mb && ma.mes === mb.mes) return `Os dois ouviram mais em ${mesLongo(ma.mes)} (${h(ma.a)} e ${h(mb.b)})`;
  const frase = (nome, m, v, curta) => {
    if (!m) return `${nome} não ouviu nada neste período`;
    return `${nome}${curta ? ', em' : ' ouviu mais em'} ${mesLongo(m.mes)} (${h(v)})`;
  };
  return `${frase(na, ma, ma?.a, false)}; ${frase(nb, mb, mb?.b, Boolean(ma && mb))}`;
}

/** As frases dos títulos (o fato principal de cada gráfico), sem gênero: os nomes são digitados. */
export function destaques(g, nomes) {
  return {
    artistas: tituloArtistas(g.artistas, nomes),
    horas: tituloHoras(g.horas, nomes),
    dias: linhaDias(g.dias, g.horas, g.fuso, nomes),
    tracos: tituloTracos(g.tracos, nomes),
    meses: tituloMeses(g.meses, nomes),
  };
}
