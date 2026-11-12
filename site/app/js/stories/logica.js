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

// Metade vai para o par, como o format do Python (12,25 → 12,2); navegador antigo ignora e arredonda para cima.
export function fmtNum(valor, casas = 0) {
  return Number(valor).toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas, roundingMode: 'halfEven' });
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

// Comparação de nomes vindos de fontes diferentes: sem acento, caixa e pontuação.
export const normalizar = (t) => t.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();

// Pôster em Canvas: texto que não cabe na largura termina em "…" (ctx só precisa de measureText).
export function cortar(ctx, texto, largura) {
  if (ctx.measureText(texto).width <= largura) return texto;
  let fim = texto.length;
  while (fim > 0 && ctx.measureText(`${texto.slice(0, fim).trimEnd()}…`).width > largura) fim--;
  return `${texto.slice(0, fim).trimEnd()}…`;
}

// Número estável por nome (capa de teste e matiz da capa tipográfica).
export function hashNome(texto) {
  let h = 0;
  for (const c of texto) h = (h * 31 + c.codePointAt(0)) >>> 0;
  return h;
}

/* ---------- Quais slides entram (mesma ordem do núcleo) ---------- */
export function tiposDoWrapped(d, { capas = false } = {}) {
  const variosAnos = d.anos.length > 1;
  const temHabitos = Object.values(d.habitos || {}).some((v) => v !== null);
  return [
    'intro', 'primeira', 'artista', 'top_artistas', 'top_musicas',
    capas && d.top_musicas.length >= 9 && 'trilha', // mosaico de capas: só com as capas ligadas
    variosAnos && 'anos',
    d.quantidade_artistas >= 10 && 'descobertas', // com 1 ano só, entra a versão curta
    'recorde', 'relogio', 'maratona', 'fiel',
    temHabitos && 'habitos',
    'arquetipo', 'resumo',
  ].filter(Boolean);
}

/* ---------- Frases dinâmicas (texto aprovado no design; neutras em gênero) ---------- */
export function fraseRecorde(horas) {
  if (horas >= 12) return 'Mais horas de música do que de sono.';
  if (horas >= 8) return 'Um expediente inteiro de música.';
  if (horas >= 4) return `Dava para ouvir uns ${Math.floor((horas * 60) / 45)} álbuns inteiros.`;
  return 'Um dia intenso, no seu ritmo.';
}
export function fraseRepeticao(plays) {
  if (plays >= 20) return 'Isso não é ouvir, é estudar.';
  if (plays >= 10) return 'Virou a trilha daquele dia.';
  return 'Um dia com trilha sonora definida.';
}
export function fraseSequencia(dias) {
  if (dias >= 365) return 'Um ano inteiro sem um dia de silêncio.';
  if (dias >= 100) return `${Math.floor(dias / 30)} meses sem pausa.`;
  if (dias >= 30) return 'Mais de um mês inteiro, todo dia.';
  if (dias >= 7) return `Uma boa sequência de ${dias} dias.`;
  return 'Você ouve no seu ritmo, sem obrigação.';
}
export function fraseConstancia(fracao) {
  if (fracao >= 0.9) return 'Música é rotina.';
  if (fracao >= 0.6) return 'Quase todo dia tem trilha.';
  return 'Você escolhe os momentos.';
}

// Hábito em destaque: o que mais passa do limiar do arquétipo correspondente.
const HABITOS = [
  ['pulos', 0.35, (p) => `Dedo rápido: ${p} das faixas puladas.`],
  ['aleatorio', 0.6, (p) => `Quem escolhe é o aleatório: ${p} das vezes.`],
  ['fim_natural', 0.65, (p) => `Você ouve até o fim: ${p} das faixas.`],
  ['offline', 0.2, (p) => `Sem sinal, com som: ${p} offline.`],
];
export function habitoDestaque(habitos) {
  let melhor = null;
  for (const [chave, limiar, frase] of HABITOS) {
    const v = habitos?.[chave];
    if (v == null || v < limiar) continue;
    if (!melhor || v / limiar > melhor.razao) melhor = { chave, razao: v / limiar, frase: frase(fmtPct(v)) };
  }
  return melhor ? { chave: melhor.chave, frase: melhor.frase } : { chave: null, frase: 'Equilíbrio: nem pula demais, nem deixa tudo no aleatório.' };
}

// Story 7 com 1 ano só: "1 artista novo a cada N plays".
export function descobertasCurta(medida) {
  const n = Math.max(1, Math.round(1 / medida));
  return { n, frase: medida >= 0.06 ? 'Você vive caçando som novo.' : 'Você sabe do que gosta.' };
}

/* ---------- Stories da Dupla (dados: `dupla` da ponte) ---------- */
// Quais stories entram, na ordem. A sintonia tem 2 telas quando houve música ao mesmo tempo.
export function tiposDaDupla(d) {
  const s = d.sintonia;
  return [
    'abertura',
    d.em_comum.length > 0 && 'em_comum',
    d.favoritos.every(Boolean) && 'frente',
    d.apresentar.length > 0 && 'apresentar',
    'relogios',
    s && 'sintonia',
    s && s.momentos > 0 && s.musica && 'sintonia_musica',
    'poster',
  ].filter(Boolean);
}

// Frases neutras: falam da escuta no período, nunca de afinidade entre as pessoas.
// Sintonia como afinação: 100% de escuta em comum = afinados (0 cents); 0% = −50 cents.
export const centsDe = (match) => -Math.round((1 - match) * 50) || 0; // arredonda o desvio (13,5 → 14); || 0 evita "−0"
export const textoCents = (match) => { const c = centsDe(match); return c === 0 ? 'afinados' : `${String(c).replace('-', '−')} cents`; };

export function fraseEmComum(match) {
  if (match >= 0.6) return 'Quase a mesma trilha.';
  if (match >= 0.3) return 'Bastante coisa em comum.';
  if (match >= 0.1) return 'Alguns pontos em comum.';
  return 'Cada um no seu som.';
}
export function frasePosicao(posicao, nome) {
  if (posicao == null) return `Não aparece no ranking de ${nome}.`;
  if (posicao === 1) return `Também é o nº 1 de ${nome}.`;
  return `No ranking de ${nome}, é o ${posicao}º.`;
}
// Distância entre as horas de pico, dando a volta no relógio (23h e 1h ficam a 2 h).
export function fraseRelogios(picoA, picoB) {
  const distancia = Math.min(Math.abs(picoA - picoB), 24 - Math.abs(picoA - picoB));
  if (distancia <= 1) return 'Vocês ouvem no mesmo horário.';
  if (distancia <= 4) return 'Horários parecidos.';
  return 'Cada um no seu turno.';
}
