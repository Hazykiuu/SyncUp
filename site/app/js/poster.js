// PNG do pôster (último story) desenhado em Canvas no navegador: 1080×1920, rápido mesmo no
// celular e sem Pillow. Mesmo layout do story; capas nítidas e nada por cima (regras do Spotify).
import { capaTeste, chaveCapa } from './stories/slides.js';
import { ajustarCor, corReserva, cortar, fmtNum, hashNome, mesAno } from './stories/logica.js';

const L = 1080, A = 1920, M = 90, UTIL = L - 2 * M;
const VERDE = '#1ed760';
const FONTE = (peso, px) => `${peso} ${px}px Figtree, system-ui, sans-serif`;
const doSpotify = (url) => /^https:\/\/[^/]*(scdn\.co|spotifycdn\.com)\//.test(url || '');

function imagem(src) {
  if (!src) return Promise.resolve(null);
  return new Promise((ok) => {
    const img = new Image();
    img.crossOrigin = 'anonymous'; // CORS * no Spotify: o canvas continua exportável
    img.onload = () => ok(img);
    img.onerror = () => ok(null);
    img.src = src;
  });
}

function retangulo(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, r);
}

// Cor média da foto (como no story), ou a de reserva.
function corDe(img) {
  if (!img) return corReserva(0);
  try {
    const c = Object.assign(document.createElement('canvas'), { width: 16, height: 16 }).getContext('2d');
    c.drawImage(img, 0, 0, 16, 16);
    const px = c.getImageData(0, 0, 16, 16).data, soma = [0, 0, 0];
    for (let k = 0; k < px.length; k += 4) { soma[0] += px[k]; soma[1] += px[k + 1]; soma[2] += px[k + 2]; }
    return ajustarCor(...soma.map((s) => s / 256));
  } catch { return corReserva(0); }
}

// Capa nítida (cantos arredondados), ou a capa tipográfica com a mesma matiz do story.
function capa(ctx, img, nome, x, y, lado, raio) {
  ctx.save();
  retangulo(ctx, x, y, lado, lado, raio);
  ctx.clip();
  if (img) ctx.drawImage(img, x, y, lado, lado);
  else {
    const h = hashNome(nome || '?') % 360, g = ctx.createLinearGradient(x, y, x + lado, y + lado);
    g.addColorStop(0, `hsl(${h} 70% 50%)`); g.addColorStop(1, `hsl(${h + 40} 70% 32%)`);
    ctx.fillStyle = g; ctx.fillRect(x, y, lado, lado);
    ctx.fillStyle = '#fff'; ctx.font = FONTE(900, lado * 0.45); ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText((nome || '?').slice(0, 1).toUpperCase(), x + lado / 2, y + lado / 2);
    ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
  }
  ctx.restore();
}

function pilula(ctx, texto, x, y) {
  ctx.font = FONTE(800, 36);
  const w = ctx.measureText(texto).width + 64;
  retangulo(ctx, x, y, w, 76, 38);
  ctx.fillStyle = 'rgba(255,255,255,.08)'; ctx.fill();
  ctx.strokeStyle = 'rgba(255,255,255,.2)'; ctx.lineWidth = 2; ctx.stroke();
  ctx.fillStyle = '#fff'; ctx.fillText(texto, x + 32, y + 50);
  return x + w + 20;
}

export async function desenharPoster(d, capas) {
  await Promise.all([FONTE(900, 64), FONTE(800, 36), FONTE(400, 36)].map((f) => document.fonts.load(f).catch(() => null)));
  const url = (item, tipo) => capaTeste(item) || capas?.get(chaveCapa(item, tipo))?.url || null;
  const a = d.artista_vida, top = d.top_musicas.slice(0, 5), p = d.arquetipos.principal;
  const [foto, ...capasTop] = await Promise.all([imagem(url(a, 'artista')), ...top.map((m) => imagem(url(m, 'faixa')))]);
  const temSpotify = [url(a, 'artista'), ...top.map((m) => url(m, 'faixa'))].some(doSpotify);
  const logo = temSpotify ? await imagem('marcas/spotify-logo-branco.svg') : null;

  const canvas = Object.assign(document.createElement('canvas'), { width: L, height: A });
  const ctx = canvas.getContext('2d');
  const [r, g, b] = corDe(foto);

  // Fundo: preto, duas manchas da cor da foto e o véu (igual ao CSS do story).
  ctx.fillStyle = '#0b0b0c'; ctx.fillRect(0, 0, L, A);
  for (const [cx, cy, raio, alfa] of [[L * 0.15, 0, A * 0.9, 0.95], [L, A, A * 0.8, 0.55]]) {
    const m = ctx.createRadialGradient(cx, cy, 0, cx, cy, raio);
    m.addColorStop(0, `rgba(${r},${g},${b},${alfa})`); m.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = m; ctx.fillRect(0, 0, L, A);
  }
  const veu = ctx.createLinearGradient(0, 0, 0, A * 0.7);
  veu.addColorStop(0, 'rgba(0,0,0,.55)'); veu.addColorStop(1, 'rgba(0,0,0,.78)');
  ctx.fillStyle = veu; ctx.fillRect(0, 0, L, A);

  // Topo: as 4 barras do SyncUp + período.
  [0.55, 1, 0.4, 0.75].forEach((h, k) => { ctx.fillStyle = VERDE; retangulo(ctx, M + k * 16, 150 - 48 * h, 10, 48 * h, 5); ctx.fill(); });
  ctx.fillStyle = '#fff'; ctx.font = FONTE(900, 48); ctx.fillText('SyncUp', M + 78, 150);
  ctx.font = FONTE(400, 34); ctx.fillStyle = 'rgba(255,255,255,.7)'; ctx.textAlign = 'right';
  ctx.fillText(`${mesAno(d.inicio)} → ${mesAno(d.fim)}`, L - M, 148); ctx.textAlign = 'left';

  // Nome e horas.
  ctx.fillStyle = '#fff'; ctx.font = FONTE(900, 132);
  ctx.fillText(cortar(ctx, d.nome.toUpperCase(), UTIL), M, 330);
  ctx.font = FONTE(900, 76); ctx.fillStyle = VERDE;
  const horas = fmtNum(d.horas);
  ctx.fillText(horas, M, 430);
  const xh = M + ctx.measureText(horas).width + 18;
  ctx.font = FONTE(400, 38); ctx.fillStyle = 'rgba(255,255,255,.88)';
  ctx.fillText(cortar(ctx, `horas de música · ${fmtNum(d.horas / 24)} dias sem parar`, L - M - xh), xh, 428);

  // Artista da vida: foto à esquerda, texto ao lado (nunca por cima).
  const yA = 500, lado = 360;
  capa(ctx, foto, a.nome, M, yA, lado, 16);
  const xt = M + lado + 48, wt = L - M - xt;
  ctx.fillStyle = 'rgba(255,255,255,.7)'; ctx.font = FONTE(800, 30); ctx.fillText('ARTISTA DA VIDA', xt, yA + 110);
  ctx.fillStyle = '#fff'; ctx.font = FONTE(900, 70);
  const palavras = a.nome.split(' '); let linha = '', linhas = [];
  for (const w of palavras) { const t = linha ? `${linha} ${w}` : w; if (ctx.measureText(t).width > wt && linha) { linhas.push(linha); linha = w; } else linha = t; }
  linhas.push(linha); linhas = linhas.slice(0, 2);
  linhas.forEach((l, k) => ctx.fillText(cortar(ctx, l, wt), xt, yA + 190 + k * 76));
  ctx.fillStyle = 'rgba(255,255,255,.7)'; ctx.font = FONTE(400, 36);
  ctx.fillText(`${fmtNum(a.plays)} plays`, xt, yA + 190 + linhas.length * 76 + 10);

  // Top 5 músicas: capas lado a lado + legenda numerada.
  const yC = 940, gap = 24, lc = (UTIL - 4 * gap) / 5;
  top.forEach((m, k) => capa(ctx, capasTop[k], m.nome, M + k * (lc + gap), yC, lc, 10));
  ctx.font = FONTE(400, 32); ctx.fillStyle = 'rgba(255,255,255,.88)';
  ctx.fillText(cortar(ctx, top.map((m, k) => `${k + 1} ${m.nome}`).join(' · '), UTIL), M, yC + lc + 56);

  // Arquétipo e pico.
  const yP = yC + lc + 110;
  pilula(ctx, `pico às ${d.pico_hora}h`, pilula(ctx, p.nome, M, yP), yP);

  // Convite: o gancho para quem vê o story abrir o SyncUp.
  const yK = yP + 130, hK = 300;
  retangulo(ctx, M, yK, UTIL, hK, 48);
  ctx.fillStyle = 'rgba(255,255,255,.07)'; ctx.fill();
  ctx.strokeStyle = 'rgba(30,215,96,.75)'; ctx.lineWidth = 4; ctx.stroke();
  ctx.fillStyle = '#fff'; ctx.font = FONTE(900, 66); ctx.fillText('Qual é a nossa sintonia?', M + 56, yK + 110);
  ctx.fillStyle = VERDE; ctx.font = FONTE(800, 46); ctx.fillText('Compare comigo →', M + 56, yK + 185);
  ctx.fillStyle = 'rgba(255,255,255,.85)'; ctx.font = FONTE(400, 40); ctx.fillText('hazykiuu.github.io/SyncUp', M + 56, yK + 250);

  // Logo do Spotify (regra das capas), só se alguma capa veio dele.
  if (logo) ctx.drawImage(logo, M, yK + hK + 70, 240, 240 * (225.25 / 823.46));

  return new Promise((ok, falha) => canvas.toBlob((blob) => (blob ? ok(blob) : falha(new Error('Não deu para gerar a imagem.'))), 'image/png'));
}

// Celular: abre a folha de compartilhar (Instagram, WhatsApp…). Sem suporte: baixa o PNG.
export async function compartilhar(blob) {
  const arquivo = new File([blob], 'syncup-wrapped.png', { type: 'image/png' });
  if (navigator.canShare?.({ files: [arquivo] })) {
    try {
      await navigator.share({ files: [arquivo], title: 'Meu SyncUp Wrapped', text: 'Qual é a nossa sintonia? hazykiuu.github.io/SyncUp' });
      return 'compartilhado';
    } catch (e) { if (e.name === 'AbortError') return 'cancelado'; }
  }
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement('a'), { href: url, download: arquivo.name });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return 'baixado';
}
