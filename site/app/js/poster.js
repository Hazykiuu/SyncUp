// PNG do pôster (último story) desenhado em Canvas no navegador: 1080×1920, rápido mesmo no
// celular e sem Pillow. Mesmo layout do story; capas nítidas e nada por cima (regras do Spotify).
import { capaTeste, chaveCapa, corMedia, doSpotify } from './stories/slides.js';
import { corReserva, cortar, fmtNum, hashNome, mesAno } from './stories/logica.js';

const L = 1080, A = 1920, M = 90, UTIL = L - 2 * M;
const VERDE = '#1ed760';
const FONTE = (peso, px) => `${peso} ${px}px Figtree, system-ui, sans-serif`;

function imagem(src) {
  if (!src) return Promise.resolve(null);
  return new Promise((ok) => {
    const img = new Image();
    img.crossOrigin = 'anonymous'; // CORS * no Spotify: o canvas continua exportável
    img.onload = () => ok(img);
    img.onerror = () => ok(null);
    setTimeout(() => ok(null), 8000); // rede ruim: o pôster sai sem essa capa, nunca "Gerando…" para sempre
    img.src = src;
  });
}

function retangulo(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, r);
}

// Cor média da foto (como no story), ou a de reserva.
const corDe = (img) => (img && corMedia(img)) || corReserva(0);

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
function topo(ctx, d, direita = `${mesAno(d.inicio)} → ${mesAno(d.fim)}`) {
  [0.55, 1, 0.4, 0.75].forEach((h, k) => { ctx.fillStyle = BARRAS[k]; retangulo(ctx, M + k * 16, 150 - 48 * h, 10, 48 * h, 5); ctx.fill(); });
  ctx.fillStyle = '#fff'; ctx.font = FONTE(900, 48); ctx.fillText('SyncUp', M + 78, 150);
  ctx.font = FONTE(400, 34); ctx.fillStyle = 'rgba(255,255,255,.7)'; ctx.textAlign = 'right';
  ctx.fillText(direita, L - M, 148); ctx.textAlign = 'left';
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

// Pôster da Batalha (o pódio, último story): campeão, título de classe, pódio de vidro e, no rodapé, a dupla mais
// afinada numa linha própria, com respiro antes do convite (mesma sobriedade do pôster da Dupla).
const MEDALHA = { ouro: '#f5c542', prata: '#c9d1d9', bronze: '#d08b4f' }; // os mesmos de --ouro/--prata/--bronze (estilo.css)
const rgba = (hex, a) => `rgba(${[1, 3, 5].map((k) => parseInt(hex.slice(k, k + 2), 16)).join(',')},${a})`;
export async function desenharPosterBatalha(b) {
  await Promise.all([FONTE(900, 64), FONTE(800, 36), FONTE(400, 36)].map((f) => document.fonts.load(f).catch(() => null)));
  const canvas = Object.assign(document.createElement('canvas'), { width: L, height: A });
  const ctx = canvas.getContext('2d');
  const inicial = (nome) => ([...nome.trim()][0] || '?').toUpperCase();
  const ordem = b.lutadores.map((_, i) => i).sort((i, j) => {
    const x = b.lutadores[i].medalhas, y = b.lutadores[j].medalhas;
    return y.ouro - x.ouro || y.prata - x.prata || y.bronze - x.bronze || i - j;
  });
  const campeoes = b.campeoes.map((k) => b.lutadores[k]);

  // Fundo: a cor de quem levou no alto, a do 2º embaixo, e o véu (como os stories).
  ctx.fillStyle = '#0b0b0c'; ctx.fillRect(0, 0, L, A);
  for (const [cx, cy, raio, cor] of [[L * 0.1, 0, A * 0.8, rgba(campeoes[0].cor, 0.7)], [L, A, A * 0.7, rgba(b.lutadores[ordem[1]].cor, 0.45)]]) {
    const m = ctx.createRadialGradient(cx, cy, 0, cx, cy, raio);
    m.addColorStop(0, cor); m.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = m; ctx.fillRect(0, 0, L, A);
  }
  const veu = ctx.createLinearGradient(0, 0, 0, A * 0.7);
  veu.addColorStop(0, 'rgba(0,0,0,.5)'); veu.addColorStop(1, 'rgba(0,0,0,.75)');
  ctx.fillStyle = veu; ctx.fillRect(0, 0, L, A);
  topo(ctx, null, 'Batalha');

  const kicker = (texto, y) => {
    ctx.fillStyle = 'rgba(255,255,255,.8)'; ctx.font = FONTE(800, 30);
    if ('letterSpacing' in ctx) ctx.letterSpacing = '4px';
    ctx.fillText(texto.toUpperCase(), M, y);
    if ('letterSpacing' in ctx) ctx.letterSpacing = '0px';
  };
  const avatar = (l, cx, cy, r) => {
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, 2 * Math.PI); ctx.fillStyle = l.cor; ctx.fill();
    ctx.fillStyle = '#000'; ctx.font = FONTE(900, r * 0.95); ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(inicial(l.nome), cx, cy + r * 0.04); ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
  };
  const medalhas = (m, x, y) => {
    const itens = ['ouro', 'prata', 'bronze'].filter((t) => m[t] > 0);
    ctx.font = FONTE(800, 34);
    const larg = itens.reduce((s, t) => s + 40 + ctx.measureText(String(m[t])).width + 24, 0) - 24;
    let xi = x - larg / 2;
    for (const t of itens) {
      ctx.beginPath(); ctx.arc(xi + 14, y - 12, 14, 0, 2 * Math.PI); ctx.fillStyle = MEDALHA[t]; ctx.fill();
      ctx.fillStyle = '#fff'; ctx.fillText(String(m[t]), xi + 40, y);
      xi += 40 + ctx.measureText(String(m[t])).width + 24;
    }
  };

  const geral = campeoes.length >= 3;
  kicker(campeoes.length === 1 ? 'Quem levou' : campeoes.length === 2 ? 'Empate no topo' : 'Empate geral', 330);
  if (!geral) {
    // O nome encolhe até 80 px; dois campeões que não cabem numa linha vão um em cada linha.
    let px = 130;
    const nome = campeoes.map((l) => l.nome).join(' e ');
    ctx.font = FONTE(900, px);
    while (px > 80 && ctx.measureText(nome).width > UTIL) ctx.font = FONTE(900, (px -= 4));
    const linhas = ctx.measureText(nome).width > UTIL && campeoes.length === 2 ? [`${campeoes[0].nome} e`, campeoes[1].nome] : [nome];
    ctx.fillStyle = '#fff';
    linhas.forEach((texto, k) => ctx.fillText(cortar(ctx, texto, UTIL), M, 330 + px + 20 + k * (px + 10)));
    if (b.titulo) kicker(b.titulo, 330 + px + 90);
    // Pódio: 2º, 1º, 3º; quem empata no placar fica à mesma altura.
    const top = ordem.slice(0, 3);
    const igual = (x, y) => x.ouro === y.ouro && x.prata === y.prata && x.bronze === y.bronze;
    const pos = top.map((k, n) => 1 + top.slice(0, n).filter((j) => !igual(b.lutadores[j].medalhas, b.lutadores[k].medalhas)).length);
    const gap = 30, w = (UTIL - 2 * gap) / 3, base = 1420, altura = { 1: 420, 2: 320, 3: 240 };
    [1, 0, 2].filter((n) => n < top.length).forEach((n, coluna) => {
      const l = b.lutadores[top[n]], h = altura[pos[n]], x = M + coluna * (w + gap), y = base - h;
      const g = ctx.createLinearGradient(0, y, 0, base);
      g.addColorStop(0, rgba(l.cor, 0.55)); g.addColorStop(1, rgba(l.cor, 0.12));
      retangulo(ctx, x, y, w, h, [36, 36, 12, 12]); ctx.fillStyle = g; ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,.16)'; ctx.lineWidth = 2; ctx.stroke();
      ctx.fillStyle = 'rgba(255,255,255,.55)'; ctx.fillRect(x + 30, y + 1, w - 60, 2);
      ctx.fillStyle = '#fff'; ctx.font = FONTE(900, 72); ctx.textAlign = 'center'; ctx.fillText(`${pos[n]}º`, x + w / 2, y + 100);
      ctx.textAlign = 'left';
      const r = pos[n] === 1 ? 84 : 66;
      medalhas(l.medalhas, x + w / 2, y - 40);
      ctx.font = FONTE(800, 40); ctx.textAlign = 'center'; ctx.fillStyle = '#fff'; ctx.fillText(cortar(ctx, l.nome, w), x + w / 2, y - 100);
      ctx.textAlign = 'left';
      avatar(l, x + w / 2, y - 150 - r, r);
    });
  } else {
    let y = 450;
    for (const l of campeoes) {
      avatar(l, M + 44, y - 16, 44);
      ctx.fillStyle = '#fff'; ctx.font = FONTE(900, 60); ctx.fillText(cortar(ctx, l.nome, UTIL - 130), M + 120, y + 4);
      y += 130;
    }
    const m = campeoes[0].medalhas;
    ctx.font = FONTE(400, 38); ctx.fillStyle = 'rgba(255,255,255,.85)';
    ctx.fillText(`Todos com ${['ouro', 'prata', 'bronze'].filter((t) => m[t]).map((t) => `${m[t]} ${t}${m[t] === 1 ? '' : 's'}`).join(', ')}.`, M, y + 10);
  }

  // Rodapé: a dupla mais afinada numa linha própria, com respiro antes do convite.
  const [nomeX, nomeY] = b.afinada.par.map((k) => b.lutadores[k].nome);
  kicker('A dupla mais afinada', A - 360);
  ctx.fillStyle = '#fff'; ctx.font = FONTE(800, 42);
  ctx.fillText(cortar(ctx, `${nomeX} & ${nomeY} — ${fmtNum(b.afinada.valor, 1)}%`, UTIL), M, A - 300);
  pe(ctx);

  return new Promise((ok, falha) => canvas.toBlob((blob) => (blob ? ok(blob) : falha(new Error('Não deu para gerar a imagem.'))), 'image/png'));
}

// Pôster do Match: o casal do grupo em rosa, com a nota, a fita do nível, os corações e o que une os dois.
const CORACAO = new Path2D('M12 21s-7.5-4.6-9.6-9.4C.9 8 3.1 4 6.9 4c2.2 0 3.7 1.2 5.1 3 1.4-1.8 2.9-3 5.1-3 3.8 0 6 4 4.5 7.6C19.5 16.4 12 21 12 21Z');
export async function desenharPosterMatch(r, x, y, c, cores) {
  await Promise.all([FONTE(900, 64), FONTE(800, 36), FONTE(400, 36)].map((f) => document.fonts.load(f).catch(() => null)));
  const canvas = Object.assign(document.createElement('canvas'), { width: L, height: A });
  const ctx = canvas.getContext('2d');
  const coracao = (cx, cy, lado, cor) => {
    ctx.save(); ctx.translate(cx - lado / 2, cy - lado / 2); ctx.scale(lado / 24, lado / 24); ctx.fillStyle = cor; ctx.fill(CORACAO); ctx.restore();
  };

  // Fundo vinho com brilho rosa e a renda no alto e embaixo.
  ctx.fillStyle = '#170b13'; ctx.fillRect(0, 0, L, A);
  for (const [cx, cy, raio, cor] of [[0, 0, A * 0.75, 'rgba(245,115,160,.55)'], [L, A, A * 0.7, rgba(cores[x], 0.35)]]) {
    const m = ctx.createRadialGradient(cx, cy, 0, cx, cy, raio);
    m.addColorStop(0, cor); m.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = m; ctx.fillRect(0, 0, L, A);
  }
  ctx.fillStyle = 'rgba(245,115,160,.6)';
  for (let k = 0; k * 40 < L + 40; k++) for (const yy of [0, A]) { ctx.beginPath(); ctx.arc(k * 40 + 20, yy, 14, 0, 2 * Math.PI); ctx.fill(); }
  for (let k = 0; k < 14; k++) coracao((k * 197) % L, 200 + ((k * 331) % (A - 400)), 24 + (k % 4) * 10, 'rgba(245,115,160,.18)');
  topo(ctx, null, 'Match');

  ctx.textAlign = 'center';
  ctx.fillStyle = ROSA; ctx.font = FONTE(800, 32);
  if ('letterSpacing' in ctx) ctx.letterSpacing = '5px';
  ctx.fillText('O CASAL DO GRUPO', L / 2, 360);
  if ('letterSpacing' in ctx) ctx.letterSpacing = '0px';

  // O casal: duas iniciais e o coração no meio.
  const raio = 110, cy = 560;
  for (const [n, cx] of [[x, L / 2 - 120], [y, L / 2 + 120]]) {
    ctx.beginPath(); ctx.arc(cx, cy, raio + 10, 0, 2 * Math.PI); ctx.fillStyle = 'rgba(245,115,160,.6)'; ctx.fill();
    ctx.beginPath(); ctx.arc(cx, cy, raio, 0, 2 * Math.PI); ctx.fillStyle = cores[n]; ctx.fill();
    ctx.fillStyle = '#120810'; ctx.font = FONTE(900, 110); ctx.textBaseline = 'middle';
    ctx.fillText(([...n.trim()][0] || '?').toUpperCase(), cx, cy + 6); ctx.textBaseline = 'alphabetic';
  }
  ctx.shadowColor = 'rgba(245,115,160,.9)'; ctx.shadowBlur = 30; coracao(L / 2, cy, 120, ROSA); ctx.shadowBlur = 0;

  let px = 110;
  const nomes = `${x} & ${y}`;
  ctx.font = FONTE(900, px);
  while (px > 64 && ctx.measureText(nomes).width > UTIL) ctx.font = FONTE(900, (px -= 4));
  ctx.fillStyle = '#fff'; ctx.fillText(cortar(ctx, nomes, UTIL), L / 2, 820);

  const nota = ctx.createLinearGradient(0, 900, 0, 1160);
  nota.addColorStop(0, '#ffffff'); nota.addColorStop(0.55, '#ffc2d9'); nota.addColorStop(1, ROSA);
  ctx.fillStyle = nota; ctx.font = FONTE(900, 260); ctx.shadowColor = 'rgba(245,115,160,.6)'; ctx.shadowBlur = 50;
  ctx.fillText(`${fmtNum(c.pontuacao, 1)}%`, L / 2, 1130); ctx.shadowBlur = 0;

  // Fita com pontas recortadas.
  ctx.font = FONTE(800, 34);
  const texto = c.nivel.toUpperCase(), w = ctx.measureText(texto).width + 120, fy = 1190, fh = 70;
  ctx.beginPath(); ctx.moveTo(L / 2 - w / 2, fy); ctx.lineTo(L / 2 + w / 2, fy); ctx.lineTo(L / 2 + w / 2 - 22, fy + fh / 2);
  ctx.lineTo(L / 2 + w / 2, fy + fh); ctx.lineTo(L / 2 - w / 2, fy + fh); ctx.lineTo(L / 2 - w / 2 + 22, fy + fh / 2); ctx.closePath();
  ctx.fillStyle = ROSA; ctx.fill();
  ctx.fillStyle = '#2a0a1a'; ctx.fillText(texto, L / 2, fy + 47);

  const cheios = c.pontuacao > 0 ? Math.max(1, Math.round(Math.min(1, c.pontuacao / 25) * 5)) : 0;
  for (let k = 0; k < 5; k++) coracao(L / 2 + (k - 2) * 90, 1340, 70, k < cheios ? ROSA : 'rgba(255,255,255,.18)');

  if (c.artistas_comuns.length) {
    ctx.fillStyle = ROSA; ctx.font = FONTE(800, 30);
    if ('letterSpacing' in ctx) ctx.letterSpacing = '4px';
    ctx.fillText('VOCÊS DOIS AMAM', L / 2, 1480);
    if ('letterSpacing' in ctx) ctx.letterSpacing = '0px';
    ctx.fillStyle = '#fff'; ctx.font = FONTE(800, 44);
    c.artistas_comuns.slice(0, 3).forEach((a, k) => ctx.fillText(cortar(ctx, a, UTIL), L / 2, 1550 + k * 60));
  }
  ctx.textAlign = 'left';
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
