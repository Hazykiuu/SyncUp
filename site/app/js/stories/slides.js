// Slides novos do Wrapped ("Capa Viva" + "Liquid Glass"), desenhados a partir de `dados` (JSON da ponte).
// Os que ainda não foram refeitos vêm do HTML antigo do núcleo (stories.py), até a Fase 3.
import { html, useEffect, useRef, useState } from 'preact-htm';
import { ajustarCor, corReserva, fmtNum, fmtPct, hashNome, mesAno } from './logica.js';

// shortcut: capas de teste locais (?capas=teste) até a Fase 4 trazer as do iTunes.
const CAPAS_TESTE = new URLSearchParams(location.search).get('capas') === 'teste';
const capaDe = (nome) => (CAPAS_TESTE && nome ? `fixtures/capas/capa-${(hashNome(nome) % 8) + 1}.jpg` : null);

// Contador que sobe até o valor (menos movimento: valor final direto).
function Contador({ valor, casas = 0, ativo }) {
  const [v, setV] = useState(ativo ? 0 : valor);
  useEffect(() => {
    if (!ativo || matchMedia('(prefers-reduced-motion: reduce)').matches) { setV(valor); return undefined; }
    let quadro, inicio;
    const passo = (t) => { inicio ??= t; const p = Math.min(1, (t - inicio) / 1200); setV(valor * (1 - (1 - p) ** 3)); if (p < 1) quadro = requestAnimationFrame(passo); };
    quadro = requestAnimationFrame(passo);
    return () => cancelAnimationFrame(quadro);
  }, [ativo, valor]);
  return fmtNum(v, casas);
}

// Moldura comum: fundo (capa borrada ou gradiente), véu e a cor da capa em --capa.
function Slide({ tipo, i, capa, children }) {
  const raiz = useRef(null);
  const [cor, setCor] = useState(corReserva(i));
  const lerCor = (e) => {
    try {
      const c = Object.assign(document.createElement('canvas'), { width: 16, height: 16 }).getContext('2d', { willReadFrequently: true });
      c.drawImage(e.target, 0, 0, 16, 16);
      const px = c.getImageData(0, 0, 16, 16).data;
      const soma = [0, 0, 0];
      for (let k = 0; k < px.length; k += 4) { soma[0] += px[k]; soma[1] += px[k + 1]; soma[2] += px[k + 2]; }
      setCor(ajustarCor(...soma.map((s) => s / 256)));
    } catch { /* imagem sem CORS: fica a cor de reserva */ }
  };
  return html`
    <section ref=${raiz} class=${`su-story ativo st s-${tipo}`} style=${{ '--capa': cor.join(' ') }}>
      <div class="st-fundo" aria-hidden="true">${capa && html`<img src=${capa} alt="" crossorigin="anonymous" onLoad=${lerCor} />`}</div>
      <div class="st-veu" aria-hidden="true"></div>
      <div class="st-conteudo">${children}</div>
    </section>`;
}

// Capa nítida, ou a "capa tipográfica" (inicial num quadrado de matiz estável) quando não há.
function Capa({ nome, classe = '' }) {
  const src = capaDe(nome);
  return src
    ? html`<img class=${`st-capa ${classe}`} src=${src} alt="" crossorigin="anonymous" />`
    : html`<span class=${`st-capa st-capa-tipo ${classe}`} style=${{ '--hue': hashNome(nome || '?') % 360 }} aria-hidden="true">${(nome || '?').slice(0, 1).toUpperCase()}</span>`;
}

const Entra = ({ i, tag = 'div', classe = '', children }) => html`<${tag} class=${`entra ${classe}`} style=${{ '--i': i }}>${children}<//>`;

export function Intro({ d, ativo, i }) {
  const dias = d.horas / 24;
  return html`<${Slide} tipo="intro" i=${i} capa=${capaDe(d.top_musicas[0]?.artista)}>
    <${Entra} i=${0} tag="span" classe="st-kicker">SyncUp Wrapped · vida toda<//>
    <${Entra} i=${1} tag="h2" classe="st-titulo">${d.nome},<br />sua vida no Spotify<//>
    <${Entra} i=${2} tag="p" classe="st-sub">${mesAno(d.inicio)} → ${mesAno(d.fim)}<//>
    <${Entra} i=${3} classe="st-cartao vidro">
      <div class="st-mega"><${Contador} valor=${d.horas} ativo=${ativo} /></div>
      <span class="st-rotulo">horas de música</span>
    <//>
    <${Entra} i=${4} tag="p">Isso dá <strong>${fmtNum(dias, 1)} dias inteiros</strong> sem parar, em ${fmtNum(d.dias_com_musica)} dias com música.<//>
  <//>`;
}

export function Artista({ d, ativo, i }) {
  const a = d.artista_vida;
  return html`<${Slide} tipo="artista" i=${i} capa=${capaDe(a.nome)}>
    <${Entra} i=${0} tag="span" classe="st-kicker">O artista da sua vida<//>
    <${Entra} i=${1} classe="st-capa-palco"><${Capa} nome=${a.nome} classe="flutua grande" /><//>
    <${Entra} i=${2} tag="h2" classe="st-nome-xxl">${a.nome}<//>
    <${Entra} i=${3} classe="st-chips">
      <span class="vidro"><b><${Contador} valor=${a.plays} ativo=${ativo} /></b> plays</span>
      <span class="vidro"><b><${Contador} valor=${a.horas} ativo=${ativo} /></b> horas</span>
      <span class="vidro"><b>${fmtPct(d.participacao_artista_vida)}</b> de tudo</span>
    <//>
    <${Entra} i=${4} tag="p">Vocês se conheceram em <strong>${mesAno(d.descoberta_artista_vida)}</strong>.<//>
  <//>`;
}

export function TopMusicas({ d, i }) {
  const maximo = d.top_musicas[0]?.plays || 1;
  return html`<${Slide} tipo="top_musicas" i=${i} capa=${capaDe(d.top_musicas[0]?.artista)}>
    <${Entra} i=${0} tag="span" classe="st-kicker">As que mais tocaram<//>
    <${Entra} i=${1} tag="h3" classe="st-titulo">Músicas<//>
    <ol class="st-lista">
      ${d.top_musicas.map((m, k) => html`
        <li class="entra" style=${{ '--i': k + 2 }}>
          <span class="st-pos">${k + 1}</span>
          ${k < 3 ? html`<${Capa} nome=${m.nome} classe=${`n${k + 1}`} />` : html`<span class="st-capa-vazia"></span>`}
          <span class="st-meta"><b>${m.nome}</b><small>${m.artista}</small>
            <i class="st-barra-valor" style=${{ '--valor': m.plays / maximo }}></i></span>
          <em>${fmtNum(m.plays)}</em>
        </li>`)}
    </ol>
  <//>`;
}

// Slide antigo (HTML do núcleo, já escapado em stories.py): mostrado como está até ser refeito.
export const Antigo = ({ html: conteudo, replay }) => html`<div class="st-antigo"
  onClick=${(e) => { if (e.target.closest('.su-replay')) replay(); }}
  dangerouslySetInnerHTML=${{ __html: conteudo }} />`;

export const NOVOS = { intro: Intro, artista: Artista, top_musicas: TopMusicas };
