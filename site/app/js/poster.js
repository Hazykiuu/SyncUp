// PNG do pôster (último story) desenhado em Canvas no navegador: 1080×1920, rápido mesmo no
// celular e sem Pillow. Mesmo layout do story; capas nítidas e nada por cima (regras do Spotify).
import { linhaDoPar } from './match.js';
import { larguraComum, LIMITE_STORY } from './stories/match.js';
import { capaTeste, chaveCapa, corMedia, doSpotify } from './stories/slides.js';
import { aprox, corReserva, cortar, fmtNum, hashNome, mesAno } from './stories/logica.js';
import { MEDIR_FPS } from './stories/player.js';

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

// Tema dos stories (1.18) no Canvas: "capa de playlist" (a cor vem do alto e se apaga em #121212, com o mesmo
// véu do CSS) e o vidro com borda de luz. `extra`: uma segunda luz no canto de baixo (o violeta de B na Dupla).
const SUP_1 = '#121212';
const rgbTexto = ([r, g, b], a) => `rgba(${r},${g},${b},${a})`;
function fundoPlaylist(ctx, cor, extra = null) {
  ctx.fillStyle = SUP_1; ctx.fillRect(0, 0, L, A);
  // Elipse larga como a do CSS (140% × 70%): escala o eixo x para o raio vertical virar o de referência.
  ctx.save(); ctx.translate(L * 0.22, -A * 0.08); ctx.scale((1.4 * L) / (0.7 * A), 1);
  const g = ctx.createRadialGradient(0, 0, 0, 0, 0, 0.7 * A);
  [[0, 0.95], [0.42, 0.45], [0.7, 0.08], [0.88, 0]].forEach(([p, a]) => g.addColorStop(p, rgbTexto(cor, a)));
  ctx.fillStyle = g; ctx.fillRect(-L * 2, -A, L * 6, A * 3); ctx.restore();
  if (extra) {
    const e = ctx.createRadialGradient(L, A * 1.05, 0, L, A * 1.05, A * 0.5);
    e.addColorStop(0, rgbTexto(extra, 0.3)); e.addColorStop(1, rgbTexto(extra, 0));
    ctx.fillStyle = e; ctx.fillRect(0, 0, L, A);
  }
  const veu = ctx.createLinearGradient(0, 0, 0, A);
  veu.addColorStop(0, 'rgba(0,0,0,.42)'); veu.addColorStop(0.45, 'rgba(18,18,18,.5)'); veu.addColorStop(1, 'rgba(18,18,18,.82)');
  ctx.fillStyle = veu; ctx.fillRect(0, 0, L, A);
}
// Peça dos pôsteres (como .st-vidro): superfície escura translúcida e fio claro de 1 px, sem aro nem brilho.
function vidro(ctx, x, y, w, h, raio) {
  retangulo(ctx, x, y, w, h, raio);
  ctx.fillStyle = 'rgba(0,0,0,.28)'; ctx.fill();
  ctx.strokeStyle = 'rgba(255,255,255,.16)'; ctx.lineWidth = 2; ctx.stroke();
}
// Kicker do Spotify: 700, tracking curto, branco cheio (como .st-kicker).
function kickerEm(ctx, texto, x, y, cor = '#fff', alinhamento = 'left') {
  ctx.fillStyle = cor; ctx.font = FONTE(700, 30); ctx.textAlign = alinhamento;
  if ('letterSpacing' in ctx) ctx.letterSpacing = '2px';
  ctx.fillText(texto.toUpperCase(), x, y);
  if ('letterSpacing' in ctx) ctx.letterSpacing = '0px';
  ctx.textAlign = 'left';
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

function pilula(ctx, texto, x, y, cor) {
  ctx.font = FONTE(800, 36);
  const w = ctx.measureText(texto).width + 64;
  vidro(ctx, x, y, w, 76, 38, cor);
  ctx.font = FONTE(800, 36); ctx.fillStyle = '#fff'; ctx.fillText(texto, x + 32, y + 50);
  return x + w + 20;
}

// Quebra o texto em linhas que cabem na largura (por palavra; palavra maior que a linha é partida). Nunca corta.
export function quebrar(ctx, texto, largura) {
  const linhas = []; let linha = '';
  for (const palavra of String(texto).split(/\s+/).filter(Boolean)) {
    let w = palavra;
    while (ctx.measureText(w).width > largura) { // palavra sozinha não cabe: parte no último caractere que cabe
      let n = w.length; while (n > 1 && ctx.measureText(w.slice(0, n)).width > largura) n--;
      if (linha) { linhas.push(linha); linha = ''; }
      linhas.push(w.slice(0, n)); w = w.slice(n);
    }
    const t = linha ? `${linha} ${w}` : w;
    if (linha && ctx.measureText(t).width > largura) { linhas.push(linha); linha = w; } else linha = t;
  }
  if (linha) linhas.push(linha);
  return linhas.length ? linhas : [''];
}
// Encolhe a fonte (de px até min) até o texto caber em maxLinhas; no mínimo, aceita mais linhas (nunca corta).
function caber(ctx, texto, largura, peso, px, min, maxLinhas) {
  let linhas;
  for (; ; px -= 4) { ctx.font = FONTE(peso, px); linhas = quebrar(ctx, texto, largura); if (linhas.length <= maxLinhas || px - 4 < min) break; }
  return { linhas, px };
}

// Pôster do Wrapped = o último story (resumo): período sob o logo, iniciais e "Sua retrospectiva", nome, horas em
// destaque, o Artista da vida com a luz da capa atrás, as 5 mais tocadas e as pílulas. Nenhum texto é cortado:
// o que não cabe quebra a linha ou encolhe a fonte, e os blocos se distribuem na altura que sobra.
export async function desenharPoster(d, capas) {
  await Promise.all([FONTE(900, 64), FONTE(800, 36), FONTE(400, 36), FONTE(700, 30), FONTE(500, 38)].map((f) => document.fonts.load(f).catch(() => null)));
  const url = (item, tipo) => capaTeste(item) || capas?.get(chaveCapa(item, tipo))?.url || null;
  const a = d.artista_vida, top = d.top_musicas.slice(0, 5), p = d.arquetipos.principal;
  const [foto, ...capasTop] = await Promise.all([imagem(url(a, 'artista')), ...top.map((m) => imagem(url(m, 'faixa')))]);
  const temSpotify = [url(a, 'artista'), ...top.map((m) => url(m, 'faixa'))].some(doSpotify);
  const logo = temSpotify ? await imagem('marcas/spotify-logo-branco.svg') : null;

  const canvas = Object.assign(document.createElement('canvas'), { width: L, height: A });
  const ctx = canvas.getContext('2d');
  const cor = corDe(foto);

  // Medidas de cada bloco antes de desenhar. Se tudo não couber entre o topo e o pé, encolhe tudo por igual (e)
  // até caber; o espaço que sobra é distribuído entre os blocos.
  const topoFim = 230, baseLivre = A - 260 - (logo ? 90 : 0);
  const medir = (e) => {
    const m = { e };
    m.nome = caber(ctx, d.nome.toUpperCase(), UTIL, 900, Math.round(150 * e), Math.round(64 * e), 2);
    m.lado = Math.round(380 * e); m.xt = M + m.lado + 48; m.wt = L - M - m.xt;
    m.artista = caber(ctx, a.nome, m.wt, 900, Math.round(78 * e), Math.round(36 * e), 3);
    m.lc = Math.round(((UTIL - 4 * 24) / 5) * Math.min(1, e + 0.15));
    m.fm = Math.round(32 * Math.max(e, 0.6)); m.lm = Math.round(m.fm * 1.3);
    ctx.font = FONTE(400, m.fm);
    m.musicas = top.map((x) => quebrar(ctx, x.nome, UTIL - 40));
    m.horasPx = Math.round(104 * e);
    m.hNome = 60 + m.nome.linhas.length * m.nome.px * 0.95 + m.horasPx * 1.08 + 52;
    m.hArtista = Math.max(m.lado, 110 + m.artista.linhas.length * m.artista.px * 1.08 + 50);
    m.hMusicas = m.lc + 30 + m.musicas.flat().length * m.lm;
    ctx.font = FONTE(800, 36);
    m.emDuas = M + ctx.measureText(p.nome).width + 64 + 20 + ctx.measureText(`pico às ${d.pico_hora}h`).width + 64 > L - M;
    m.hPilulas = m.emDuas ? 172 : 76;
    m.total = m.hNome + m.hArtista + m.hMusicas + m.hPilulas;
    return m;
  };
  let med = medir(1);
  for (let e = 0.95; med.total + 5 * 16 > baseLivre - topoFim && e >= 0.5; e -= 0.05) med = medir(e);
  const { nome, lado, xt, artista, lc, fm, lm, musicas, horasPx, hNome, hArtista, hMusicas, hPilulas, emDuas: pilulasEmDuas } = med;
  const vao = Math.max(16, (baseLivre - topoFim - med.total) / 5);
  let y = topoFim + vao;
  const yArt = y + hNome + vao;

  // Fundo escuro com uma luz só, na cor da capa, atrás do Artista da vida.
  ctx.fillStyle = '#0b0b0e'; ctx.fillRect(0, 0, L, A);
  const luz = ctx.createRadialGradient(M + lado / 2, yArt + lado / 2, 0, M + lado / 2, yArt + lado / 2, 900);
  luz.addColorStop(0, rgbTexto(cor, 0.42)); luz.addColorStop(0.5, rgbTexto(cor, 0.12)); luz.addColorStop(1, rgbTexto(cor, 0));
  ctx.fillStyle = luz; ctx.fillRect(0, 0, L, A);

  // Topo: logo e, embaixo, o período.
  [0.55, 1, 0.4, 0.75].forEach((h, k) => { ctx.fillStyle = BARRAS[k]; retangulo(ctx, M + k * 16, 150 - 48 * h, 10, 48 * h, 5); ctx.fill(); });
  ctx.fillStyle = '#fff'; ctx.font = FONTE(900, 48); ctx.fillText('SyncUp', M + 78, 150);
  ctx.fillStyle = 'rgba(255,255,255,.7)'; ctx.font = FONTE(400, 32); ctx.fillText(`${mesAno(d.inicio)} → ${mesAno(d.fim)}`, M, 205);

  // Identidade: iniciais + "Sua retrospectiva", o nome e as horas.
  ctx.beginPath(); ctx.arc(M + 30, y + 22, 30, 0, 2 * Math.PI); ctx.fillStyle = VERDE; ctx.fill();
  ctx.fillStyle = '#0b0b0e'; ctx.font = FONTE(900, 32); ctx.textAlign = 'center'; ctx.fillText(([...d.nome.trim()][0] || '?').toUpperCase(), M + 30, y + 34); ctx.textAlign = 'left';
  kickerEm(ctx, 'Sua retrospectiva', M + 80, y + 33, 'rgba(255,255,255,.65)');
  y += 60;
  ctx.fillStyle = '#fff'; ctx.font = FONTE(900, nome.px);
  nome.linhas.forEach((l) => { y += nome.px * 0.95; ctx.fillText(l, M, y); });
  y += horasPx * 1.08; ctx.fillStyle = '#1db954'; ctx.font = FONTE(800, horasPx); ctx.fillText(`${aprox(d.aproximado)}${fmtNum(d.horas)} horas`, M, y);
  y += 52; ctx.fillStyle = 'rgba(255,255,255,.75)'; ctx.font = FONTE(500, 38); ctx.fillText(`de música · ${fmtNum(d.horas / 24)} dias sem parar`, M, y);

  // Artista da vida: foto à esquerda, texto ao lado (nunca por cima), o nome em quantas linhas precisar.
  y = yArt;
  capa(ctx, foto, a.nome, M, y, lado, 16);
  kickerEm(ctx, 'Artista da vida', xt, y + 70);
  ctx.fillStyle = '#fff'; ctx.font = FONTE(900, artista.px);
  let ya = y + 70;
  artista.linhas.forEach((l) => { ya += artista.px * 1.08; ctx.fillText(l, xt, ya); });
  ctx.fillStyle = 'rgba(255,255,255,.7)'; ctx.font = FONTE(400, 36); ctx.fillText(`${fmtNum(a.plays)} plays`, xt, ya + 50);
  y += hArtista + vao;

  // Top 5: capas lado a lado e a lista numerada, uma música por linha (quebra se for longa).
  const gc = (UTIL - 5 * lc) / 4;
  top.forEach((m, k) => capa(ctx, capasTop[k], m.nome, M + k * (lc + gc), y, lc, 10));
  let ym = y + lc + 30;
  ctx.font = FONTE(400, fm);
  musicas.forEach((ls, k) => ls.forEach((l, j) => {
    ym += lm;
    if (j === 0) { ctx.fillStyle = VERDE; ctx.font = FONTE(800, fm); ctx.fillText(`${k + 1}`, M, ym); ctx.font = FONTE(400, fm); }
    ctx.fillStyle = 'rgba(255,255,255,.88)'; ctx.fillText(l, M + 40, ym);
  }));
  y += hMusicas + vao;

  // Arquétipo e pico (o segundo desce de linha se não couber ao lado).
  const x2 = pilula(ctx, p.nome, M, y, cor);
  if (pilulasEmDuas) pilula(ctx, `pico às ${d.pico_hora}h`, M, y + 96, cor); else pilula(ctx, `pico às ${d.pico_hora}h`, x2, y, cor);

  // Logo do Spotify (regra das capas), só se alguma capa veio dele.
  if (logo) ctx.drawImage(logo, M, A - 330, 240, 240 * (225.25 / 823.46));
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

  fundoPlaylist(ctx, [30, 215, 96], [196, 183, 255]);

  topo(ctx, d);

  // Avatares sobrepostos com as iniciais (A na frente, como no story).
  const inicial = (nome) => (nome.trim()[0] || '?').toUpperCase();
  [[d.b, VIOLETA, M + 150], [d.a, VERDE, M + 60]].forEach(([p, cor, cx]) => {
    ctx.beginPath(); ctx.arc(cx, 300, 60, 0, 2 * Math.PI); ctx.fillStyle = cor; ctx.fill();
    ctx.lineWidth = 6; ctx.strokeStyle = SUP_1; ctx.stroke();
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
    vidro(ctx, M, y, UTIL, h, 40, [245, 115, 160]);
    kickerEm(ctx, 'Em sintonia', M + 48, y + 70, ROSA);
    ctx.fillStyle = '#fff'; ctx.font = FONTE(900, 60); ctx.fillText(cortar(ctx, `${aprox(d.aproximado)}${fmtNum(s.minutos)} min ouvindo juntos`, UTIL - 96), M + 48, y + 145);
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
    xc = pilula(ctx, nome, xc, y, [30, 215, 96]);
  }
  if (d.em_comum.length) y += 96 + 40;

  // Regra de ética do projeto: o número fala da escuta, não das pessoas.
  ctx.fillStyle = 'rgba(255,255,255,.6)'; ctx.font = FONTE(400, 30);
  ctx.fillText('Conta só o que vocês ouviram neste período.', M, A - 270);

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

  // Fundo de playlist: a cor de quem levou no alto, a do 2º no canto de baixo (como os stories).
  const rgbDe = (hex) => [1, 3, 5].map((k) => parseInt(hex.slice(k, k + 2), 16));
  fundoPlaylist(ctx, rgbDe(campeoes[0].cor), ordem[1] === undefined ? null : rgbDe(b.lutadores[ordem[1]].cor));
  topo(ctx, null, 'Batalha');

  const kicker = (texto, y) => kickerEm(ctx, texto, M, y);
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
    // O nome encolhe até 80 px; dois campeões que não cabem numa linha vão um em cada linha. Nome longo ainda
    // encolhe até 64 px antes de ser cortado (o nome de quem levou é o que o pôster mostra).
    let px = 130;
    const nomes = campeoes.map((l) => l.nome);
    let linhas = [nomes.join(' e ')];
    const larga = () => Math.max(...linhas.map((t) => ctx.measureText(t).width)) > UTIL;
    ctx.font = FONTE(900, px);
    while (px > 80 && larga()) ctx.font = FONTE(900, (px -= 4));
    if (larga() && nomes.length === 2) linhas = [`${nomes[0]} e`, nomes[1]];
    while (px > 64 && larga()) ctx.font = FONTE(900, (px -= 4));
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
      retangulo(ctx, x, y, w, h, [36, 36, 12, 12]); ctx.fillStyle = rgba(l.cor, 0.34); ctx.fill(); // como .sb-bloco: cor chapada e fio claro
      ctx.strokeStyle = 'rgba(255,255,255,.16)'; ctx.lineWidth = 2; ctx.stroke();
      ctx.fillStyle = '#fff'; ctx.font = FONTE(900, 72); ctx.textAlign = 'center'; ctx.fillText(`${pos[n]}º`, x + w / 2, y + 100);
      ctx.textAlign = 'left';
      const r = pos[n] === 1 ? 84 : 66;
      medalhas(l.medalhas, x + w / 2, y - 40);
      ctx.font = FONTE(800, 40); ctx.textAlign = 'center'; ctx.fillStyle = '#fff'; ctx.fillText(cortar(ctx, l.nome, w), x + w / 2, y - 100);
      ctx.textAlign = 'left';
      avatar(l, x + w / 2, y - 150 - r, r);
    });
  } else {
    let y = 450, px = 60; // os nomes encolhem juntos até 48 px antes de cortar
    ctx.font = FONTE(900, px);
    while (px > 48 && campeoes.some((l) => ctx.measureText(l.nome).width > UTIL - 130)) ctx.font = FONTE(900, (px -= 2));
    for (const l of campeoes) {
      avatar(l, M + 44, y - 16, 44);
      ctx.fillStyle = '#fff'; ctx.font = FONTE(900, px); ctx.fillText(cortar(ctx, l.nome, UTIL - 130), M + 120, y + 4);
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
  const pct = ` — ${fmtNum(b.afinada.valor, 1)}%`; // nomes longos são cortados, a porcentagem nunca
  ctx.fillText(cortar(ctx, `${nomeX} & ${nomeY}`, UTIL - ctx.measureText(pct).width) + pct, M, A - 300);
  pe(ctx);

  return new Promise((ok, falha) => canvas.toBlob((blob) => (blob ? ok(blob) : falha(new Error('Não deu para gerar a imagem.'))), 'image/png'));
}

// Pôster do Match: o dueto mais afinado (os mesmos dados da tela e dos stories, de linhaDoPar), na capa rosa.
export async function desenharPosterMatch(r, x, y, _c, cores) {
  await Promise.all([FONTE(900, 64), FONTE(800, 36), FONTE(400, 36)].map((f) => document.fonts.load(f).catch(() => null)));
  const canvas = Object.assign(document.createElement('canvas'), { width: L, height: A });
  const ctx = canvas.getContext('2d');
  const l = linhaDoPar(r, x, y);
  fundoPlaylist(ctx, [245, 115, 160], [1, 3, 5].map((k) => parseInt(cores[x].slice(k, k + 2), 16)));
  topo(ctx, null, 'Match');
  kickerEm(ctx, 'O dueto mais afinado', M, 380);

  // Os dois nomes, cada um na sua cor, em duas linhas ligadas por "×"; a fonte encolhe até 72 px e depois corta.
  let px = 150;
  const cabe = () => [x, y].every((n) => ctx.measureText(n).width <= UTIL - 90);
  ctx.font = FONTE(900, px);
  while (px > 72 && !cabe()) ctx.font = FONTE(900, (px -= 6));
  ctx.fillStyle = cores[x]; ctx.fillText(cortar(ctx, x, UTIL - 90), M, 380 + px * 1.15);
  ctx.fillStyle = 'rgba(255,255,255,.55)'; ctx.font = FONTE(400, px); ctx.fillText('×', M, 380 + px * 2.2);
  const lx = M + ctx.measureText('× ').width;
  ctx.font = FONTE(900, px); ctx.fillStyle = cores[y]; ctx.fillText(cortar(ctx, y, L - M - lx), lx, 380 + px * 2.2);

  // A nota (comparação dos rankings) e o nível em texto.
  const yNota = 1010;
  ctx.fillStyle = '#fff'; ctx.font = FONTE(900, 230); ctx.fillText(`${fmtNum(l.pontuacao, 1)}%`, M - 8, yNota);
  ctx.font = FONTE(800, 44); ctx.fillText(l.nivel, M, yNota + 75);
  ctx.font = FONTE(400, 30); ctx.fillStyle = 'rgba(255,255,255,.7)'; ctx.fillText('comparação dos rankings de artistas e músicas', M, yNota + 125);

  // As duas faixas (mesma geometria de .faixas): o trecho do meio são os artistas em comum.
  const j = larguraComum(l.jaccard), fy = 1210, fh = 16, w = UTIL * (1 + j) / 2;
  ctx.fillStyle = cores[x]; retangulo(ctx, M, fy, w, fh, fh / 2); ctx.fill();
  ctx.fillStyle = cores[y]; retangulo(ctx, L - M - w, fy + 30, w, fh, fh / 2); ctx.fill();
  if (j) { ctx.strokeStyle = '#fff'; ctx.lineWidth = 3; retangulo(ctx, M + UTIL * (1 - j) / 2, fy - 10, UTIL * j, 30 + fh + 20, 10); ctx.stroke(); }
  ctx.font = FONTE(400, 28); ctx.fillStyle = 'rgba(255,255,255,.7)'; ctx.fillText('Artistas em comum', M, fy + 100);

  kickerEm(ctx, 'Refrão em comum', M, 1400);
  ctx.fillStyle = '#fff'; ctx.font = FONTE(800, 44);
  const refrao = l.refrao.slice(0, LIMITE_STORY);
  if (!refrao.length) ctx.fillText('Nenhum artista em comum nos rankings.', M, 1470);
  refrao.forEach((a, k) => ctx.fillText(cortar(ctx, a, UTIL), M, 1470 + k * 60));
  pe(ctx);

  return new Promise((ok, falha) => canvas.toBlob((blob) => (blob ? ok(blob) : falha(new Error('Não deu para gerar a imagem.'))), 'image/png'));
}

// Celular: abre a folha de compartilhar (Instagram, WhatsApp…). Sem suporte: baixa o PNG.
export const segundos = (ms) => (ms / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 1 });
// Recado depois de compartilhar. O tempo só aparece com ?fps=1 (medição no celular), não para quem usa.
export const avisoPoster = (como, ms, arquivo) => (como === 'cancelado' ? ''
  : `${como === 'baixado' ? `Pôster salvo como ${arquivo}` : 'Pôster pronto'}${MEDIR_FPS ? ` em ${segundos(ms)} s` : ''}.`);

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
