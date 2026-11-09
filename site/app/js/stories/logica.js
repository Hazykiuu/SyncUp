// Lógica pura dos stories do Wrapped (sem DOM e sem Preact): testada com `node --test tests/js`.

/* ---------- Player: máquina de estados ---------- */
// Pausado enquanto houver algum motivo: soltar o dedo ("segurar") não retoma o que a pessoa
// pausou de propósito ("usuario"). O tempo do slide é a animação CSS; ela avisa com TEMPO.
export const MOTIVOS = ['usuario', 'segurar', 'interacao', 'oculta'];

export function inicial(total, { semMovimento = false } = {}) {
  return { i: 0, total, motivos: semMovimento ? ['usuario'] : [], fim: false, volta: 0 };
}

export function player(estado, acao) {
  const { i, total, motivos } = estado;
  const sem = (m) => motivos.filter((x) => x !== m);
  switch (acao.tipo) {
    case 'AVANCAR':
    case 'TEMPO':
      return i < total - 1 ? { ...estado, i: i + 1, fim: false } : { ...estado, fim: true };
    case 'VOLTAR':
      return { ...estado, i: Math.max(0, i - 1), fim: false, volta: estado.volta + (i === 0 ? 1 : 0) };
    case 'IR':
      return { ...estado, i: Math.max(0, Math.min(total - 1, acao.i)), fim: false };
    case 'PAUSAR':
      return motivos.includes(acao.motivo) ? estado : { ...estado, motivos: [...motivos, acao.motivo] };
    case 'RETOMAR':
      return { ...estado, motivos: sem(acao.motivo) };
    case 'ALTERNAR':
      return { ...estado, motivos: motivos.length ? [] : ['usuario'] };
    case 'REPLAY':
      return { ...estado, i: 0, fim: false, motivos: sem('usuario'), volta: estado.volta + 1 };
    default:
      return estado;
  }
}

export const pausado = (estado) => estado.fim || estado.motivos.length > 0;

/* ---------- Formatação (mesmas regras de formatacao.py / wrapped.py) ---------- */
const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];

export function fmtNum(valor, casas = 0) {
  return Number(valor).toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
}
export const fmtPct = (fracao, casas = 0) => `${fmtNum(fracao * 100, casas)}%`;

// As datas chegam em ISO local ("2019-12-31T21:00:36"): lidas pelo texto, sem fuso do navegador.
export function mesAno(iso) {
  const [ano, mes] = iso.slice(0, 7).split('-');
  return `${MESES[Number(mes) - 1]}/${ano}`;
}
export function dataBr(iso) {
  const [ano, mes, dia] = iso.slice(0, 10).split('-');
  return `${dia}/${mes}/${ano}`;
}

/* ---------- Cor reativa à capa ---------- */
// Média da capa → cor usável no tinte: saturação ≥ 35% e luminosidade entre 35% e 60%.
export function ajustarCor(r, g, b) {
  const [h, s, l] = paraHsl(r, g, b);
  return deHsl(h, Math.max(s, 0.35), Math.min(0.6, Math.max(0.35, l)));
}
function paraHsl(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b), l = (max + min) / 2;
  if (max === min) return [0, 0, l];
  const d = max - min, s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  const h = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [h / 6, s, l];
}
function deHsl(h, s, l) {
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s, p = 2 * l - q;
  const canal = (t) => {
    t = (t + 1) % 1;
    const v = t < 1 / 6 ? p + (q - p) * 6 * t : t < 1 / 2 ? q : t < 2 / 3 ? p + (q - p) * (2 / 3 - t) * 6 : p;
    return Math.round(v * 255);
  };
  return [canal(h + 1 / 3), canal(h), canal(h - 1 / 3)];
}

// Sem capa: verde e violeta alternando por slide (a mesma ideia dos pares --bg1/--bg2 de hoje).
export const corReserva = (i) => (i % 2 ? [196, 183, 255] : [30, 215, 96]);

// Número estável por nome (capa de teste e matiz da capa tipográfica).
export function hashNome(texto) {
  let h = 0;
  for (const c of texto) h = (h * 31 + c.codePointAt(0)) >>> 0;
  return h;
}
