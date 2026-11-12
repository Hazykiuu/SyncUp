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

// Topo dos pôsteres: as 4 barras do SyncUp, em degradê verde → violeta como no site, e o período.
const BARRAS = ['#1ed760', '#55cc94', '#8dc2cb', '#c4b7ff']; // = color-mix do estilo.css (0, 33, 67 e 100%)
function topo(ctx, d) {
  [0.55, 1, 0.4, 0.75].forEach((h, k) => { ctx.fillStyle = BARRAS[k]; retangulo(ctx, M + k * 16, 150 - 48 * h, 10, 48 * h, 5); ctx.fill(); });
  ctx.fillStyle = '#fff'; ctx.font = FONTE(900, 48); ctx.fillText('SyncUp', M + 78, 150);
  ctx.font = FONTE(400, 34); ctx.fillStyle = 'rgba(255,255,255,.7)'; ctx.textAlign = 'right';
  ctx.fillText(`${mesAno(d.inicio)} → ${mesAno(d.fim)}`, L - M, 148); ctx.textAlign = 'left';
}

// Pé dos pôsteres: o convite em duas linhas discretas, separadas por um fio. A ênfase é a pessoa, não o site.
function pe(ctx) {
  ctx.fillStyle = 'rgba(255,255,255,.16)'; ctx.fillRect(M, A - 220, UTIL, 2);
  ctx.fillStyle = '#fff'; ctx.font = FONTE(800, 36); ctx.fillText('Compare a sua sintonia comigo', M, A - 150);
  ctx.fillStyle = 'rgba(255,255,255,.7)'; ctx.font = FONTE(400, 32); ctx.fillText('hazykiuu.github.io/SyncUp', M, A - 100);
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

  topo(ctx, d);

  // Nome e horas.
  ctx.fillStyle = '#fff'; ctx.font = FONTE(900, 150);
  ctx.fillText(cortar(ctx, d.nome.toUpperCase(), UTIL), M, 345);
  ctx.font = FONTE(900, 112); ctx.fillStyle = VERDE;
  const horas = fmtNum(d.horas);
  ctx.fillText(horas, M, 485);
  const xh = M + ctx.measureText(horas).width + 20;
  ctx.font = FONTE(400, 38); ctx.fillStyle = 'rgba(255,255,255,.88)';
  ctx.fillText(cortar(ctx, 'horas de música', L - M - xh), xh, 440);
  ctx.fillText(cortar(ctx, `${fmtNum(d.horas / 24)} dias sem parar`, L - M - xh), xh, 485);

  // Artista da vida: foto à esquerda, texto ao lado (nunca por cima).
  const yA = 570, lado = 380;
  capa(ctx, foto, a.nome, M, yA, lado, 16);
  const xt = M + lado + 48, wt = L - M - xt;
  ctx.fillStyle = 'rgba(255,255,255,.7)'; ctx.font = FONTE(800, 30); ctx.fillText('ARTISTA DA VIDA', xt, yA + 110);
  ctx.fillStyle = '#fff'; ctx.font = FONTE(900, 78);
  const palavras = a.nome.split(' '); let linha = '', linhas = [];
  for (const w of palavras) { const t = linha ? `${linha} ${w}` : w; if (ctx.measureText(t).width > wt && linha) { linhas.push(linha); linha = w; } else linha = t; }
  linhas.push(linha); linhas = linhas.slice(0, 2);
  linhas.forEach((l, k) => ctx.fillText(cortar(ctx, l, wt), xt, yA + 195 + k * 84));
  ctx.fillStyle = 'rgba(255,255,255,.7)'; ctx.font = FONTE(400, 36);
  ctx.fillText(`${fmtNum(a.plays)} plays`, xt, yA + 195 + linhas.length * 84 + 10);

  // Top 5 músicas: capas lado a lado + legenda numerada.
  const yC = 1040, gap = 24, lc = (UTIL - 4 * gap) / 5;
  top.forEach((m, k) => capa(ctx, capasTop[k], m.nome, M + k * (lc + gap), yC, lc, 10));
  ctx.font = FONTE(400, 32); ctx.fillStyle = 'rgba(255,255,255,.88)';
  ctx.fillText(cortar(ctx, top.map((m, k) => `${k + 1} ${m.nome}`).join(' · '), UTIL), M, yC + lc + 56);

  // Arquétipo e pico.
  const yP = yC + lc + 110;
  pilula(ctx, `pico às ${d.pico_hora}h`, pilula(ctx, p.nome, M, yP), yP);

  // Logo do Spotify (regra das capas), só se alguma capa veio dele.
  if (logo) ctx.drawImage(logo, M, yP + 140, 240, 240 * (225.25 / 823.46));

  pe(ctx);

  return new Promise((ok, falha) => canvas.toBlob((blob) => (blob ? ok(blob) : falha(new Error('Não deu para gerar a imagem.'))), 'image/png'));
}

// Pôster da Dupla (último story): mesmo layout do story, sem capas. Verde = A, violeta = B, rosa = juntos.
const VIOLETA = '#c4b7ff', ROSA = '#f573a0';
export async function desenharPosterDupla(d) {
  await Promise.all([FONTE(900, 64), FONTE(800, 36), FONTE(400, 36)].map((f) => document.fonts.load(f).catch(() => null)));
  const canvas = Object.assign(document.createElement('canvas'), { width: L, height: A });
  const ctx = canvas.getContext('2d');
  const s = d.sintonia;

  // Fundo: preto com o degradê da dupla (verde no alto, violeta embaixo) e o véu.
  ctx.fillStyle = '#0b0b0c'; ctx.fillRect(0, 0, L, A);
  for (const [cx, cy, raio, cor] of [[L * 0.1, 0, A * 0.8, 'rgba(30,215,96,.75)'], [L, A, A * 0.8, 'rgba(196,183,255,.6)']]) {
    const m = ctx.createRadialGradient(cx, cy, 0, cx, cy, raio);
    m.addColorStop(0, cor); m.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = m; ctx.fillRect(0, 0, L, A);
  }
  const veu = ctx.createLinearGradient(0, 0, 0, A * 0.7);
  veu.addColorStop(0, 'rgba(0,0,0,.5)'); veu.addColorStop(1, 'rgba(0,0,0,.75)');
  ctx.fillStyle = veu; ctx.fillRect(0, 0, L, A);

  topo(ctx, d);

  // Avatares sobrepostos com as iniciais (A na frente, como no story).
  const inicial = (nome) => (nome.trim()[0] || '?').toUpperCase();
  [[d.b, VIOLETA, M + 150], [d.a, VERDE, M + 60]].forEach(([p, cor, cx]) => {
    ctx.beginPath(); ctx.arc(cx, 300, 60, 0, 2 * Math.PI); ctx.fillStyle = cor; ctx.fill();
    ctx.lineWidth = 6; ctx.strokeStyle = '#0b0b0c'; ctx.stroke();
    ctx.fillStyle = '#000'; ctx.font = FONTE(900, 56); ctx.textAlign = 'center'; ctx.fillText(inicial(p.nome), cx, 320); ctx.textAlign = 'left';
  });

  // "Ana + Bruno" numa linha (a fonte encolhe até 88 px); se não couber, "Ana +" / "Bruno" em duas.
  const largura = (px) => { ctx.font = FONTE(900, px); return ctx.measureText(`${d.a.nome} + ${d.b.nome}`).width; };
  let px = 140;
  while (px > 88 && largura(px) > UTIL) px -= 4;
  const umaLinha = largura(px) <= UTIL;
  if (!umaLinha) ctx.font = FONTE(900, (px = 100));
  const nomeA = umaLinha ? d.a.nome : cortar(ctx, d.a.nome, UTIL - ctx.measureText(' +').width);
  ctx.fillStyle = VERDE; ctx.fillText(nomeA, M, 520);
  ctx.fillStyle = '#fff'; ctx.fillText(' +', M + ctx.measureText(nomeA).width, 520);
  const dy = umaLinha ? 0 : 110; // tudo abaixo desce uma linha
  ctx.fillStyle = VIOLETA;
  if (umaLinha) ctx.fillText(d.b.nome, M + ctx.measureText(`${nomeA} + `).width, 520);
  else ctx.fillText(cortar(ctx, d.b.nome, UTIL), M, 520 + dy);

  // Escuta em comum.
  const pct = `${fmtNum(Math.round(d.match * 100))}%`;
  ctx.fillStyle = '#fff'; ctx.font = FONTE(900, 240); ctx.fillText(pct, M, 790 + dy);
  const xp = M + ctx.measureText(pct).width + 28;
  ctx.font = FONTE(800, 44); ctx.fillText('de escuta', xp, 712 + dy); ctx.fillText('em comum', xp, 768 + dy);
  ctx.font = FONTE(400, 38); ctx.fillStyle = 'rgba(255,255,255,.85)';
  ctx.fillText(`${fmtNum(d.total_comuns)} ${d.total_comuns === 1 ? 'artista' : 'artistas'} em comum`, M, 860 + dy);

  // Em sintonia (rosa): só quando houve música ao mesmo tempo.
  let y = 920 + dy;
  if (s?.momentos > 0) {
    const h = s.musica ? 250 : 190;
    retangulo(ctx, M, y, UTIL, h, 40);
    ctx.fillStyle = 'rgba(255,255,255,.07)'; ctx.fill();
    ctx.strokeStyle = 'rgba(245,115,160,.8)'; ctx.lineWidth = 4; ctx.stroke();
    ctx.fillStyle = ROSA; ctx.font = FONTE(800, 30); ctx.fillText('EM SINTONIA', M + 48, y + 70);
    ctx.fillStyle = '#fff'; ctx.font = FONTE(900, 60); ctx.fillText(cortar(ctx, `${fmtNum(s.minutos)} min ouvindo juntos`, UTIL - 96), M + 48, y + 145);
    if (s.musica) { ctx.font = FONTE(400, 36); ctx.fillStyle = 'rgba(255,255,255,.85)'; ctx.fillText(cortar(ctx, `A música de vocês: ${s.musica.nome}`, UTIL - 96), M + 48, y + 210); }
    y += h + 50;
  }

  // Artistas em comum em pílulas (quebram de linha; o que não cabe em 2 linhas fica de fora).
  let xc = M, linhas = 1;
  for (const c of d.em_comum) {
    ctx.font = FONTE(800, 36);
    const nome = cortar(ctx, c.nome, UTIL - 64);
    const w = ctx.measureText(nome).width + 64;
    if (xc + w > L - M) { if (++linhas > 2) break; xc = M; y += 96; }
    xc = pilula(ctx, nome, xc, y);
  }
  if (d.em_comum.length) y += 96 + 40;

  // Regra de ética do projeto: o número fala da escuta, não das pessoas.
  ctx.fillStyle = 'rgba(255,255,255,.6)'; ctx.font = FONTE(400, 30);
  ctx.fillText('Mede a escuta neste período, não afinidade entre pessoas.', M, A - 270);

  pe(ctx);

  return new Promise((ok, falha) => canvas.toBlob((blob) => (blob ? ok(blob) : falha(new Error('Não deu para gerar a imagem.'))), 'image/png'));
}

// Celular: abre a folha de compartilhar (Instagram, WhatsApp…). Sem suporte: baixa o PNG.
export async function compartilhar(blob, nome = 'syncup-wrapped.png', titulo = 'Meu SyncUp Wrapped') {
  const arquivo = new File([blob], nome, { type: 'image/png' });
  if (navigator.canShare?.({ files: [arquivo] })) {
    try {
      await navigator.share({ files: [arquivo], title: titulo, text: 'Qual é a nossa sintonia? hazykiuu.github.io/SyncUp' });
      return 'compartilhado';
    } catch (e) { if (e.name === 'AbortError') return 'cancelado'; }
  }
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement('a'), { href: url, download: arquivo.name });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return 'baixado';
}
