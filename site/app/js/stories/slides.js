// Slides novos do Wrapped ("Capa Viva" + "Liquid Glass"), desenhados a partir de `dados` (JSON da ponte).
// O Gradio continua com o HTML de stories.py; o app web usa só estes.
import { html, useEffect, useRef, useState } from 'preact-htm';
import {
  ajustarCor, corReserva, dataBr, descobertasCurta, fmtNum, fmtPct, fraseConstancia, fraseRecorde,
  fraseRepeticao, fraseSequencia, habitoDestaque, hashNome, mesAno,
} from './logica.js';

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
    <${Entra} i=${3} classe="st-cartao st-vidro">
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
      <span class="st-vidro"><b><${Contador} valor=${a.plays} ativo=${ativo} /></b> plays</span>
      <span class="st-vidro"><b><${Contador} valor=${a.horas} ativo=${ativo} /></b> horas</span>
      <span class="st-vidro"><b>${fmtPct(d.participacao_artista_vida)}</b> de tudo</span>
    <//>
    <${Entra} i=${4} tag="p">Vocês se conheceram em <strong>${mesAno(d.descoberta_artista_vida)}</strong>.<//>
  <//>`;
}

const Kicker = ({ i = 0, children }) => html`<${Entra} i=${i} tag="span" classe="st-kicker">${children}<//>`;
const hora = (iso) => iso.slice(11, 16);

export function Primeira({ d, i }) {
  const m = d.primeira_musica;
  return html`<${Slide} tipo="primeira" i=${i} capa=${capaDe(m.nome)}>
    <${Kicker}>Lá no começo<//>
    <${Entra} i=${1} tag="h3" classe="st-titulo menor">Tudo começou com<//>
    <${Entra} i=${2} classe="st-capa-palco"><${Capa} nome=${m.nome} classe="flutua grande" /><//>
    <${Entra} i=${3} tag="h2" classe="st-nome-xxl">${m.nome}<//>
    <${Entra} i=${4} tag="p" classe="st-sub">${m.artista}<//>
    <${Entra} i=${5} tag="p">em ${dataBr(d.primeira_data)}, às ${hora(d.primeira_data)}.<//>
  <//>`;
}

// Lista do top 5 (artistas ou músicas): capas em escada nas 3 primeiras, barra com a proporção.
function Top5({ itens, nome, sub, valor }) {
  const maximo = itens[0]?.plays || 1;
  return html`<ol class="st-lista">
    ${itens.map((m, k) => html`
      <li class="entra" style=${{ '--i': k + 2 }}>
        <span class="st-pos">${k + 1}</span>
        ${k < 3 ? html`<${Capa} nome=${nome(m)} classe=${`n${k + 1}`} />` : html`<span class="st-capa-vazia"></span>`}
        <span class="st-meta"><b>${nome(m)}</b><small>${sub(m)}</small>
          <i class="st-barra-valor" style=${{ '--valor': m.plays / maximo }}></i></span>
        <em>${valor(m)}</em>
      </li>`)}
  </ol>`;
}

export function TopArtistas({ d, i }) {
  return html`<${Slide} tipo="top_artistas" i=${i} capa=${capaDe(d.top_artistas[0]?.nome)}>
    <${Kicker}>Seu top 5 de todos os tempos<//>
    <${Entra} i=${1} tag="h3" classe="st-titulo">Artistas<//>
    <${Top5} itens=${d.top_artistas} nome=${(a) => a.nome} sub=${(a) => `${fmtNum(a.plays)} plays`} valor=${(a) => `${fmtNum(a.horas)} h`} />
  <//>`;
}

export function TopMusicas({ d, i }) {
  return html`<${Slide} tipo="top_musicas" i=${i} capa=${capaDe(d.top_musicas[0]?.nome)}>
    <${Kicker}>As que mais tocaram<//>
    <${Entra} i=${1} tag="h3" classe="st-titulo">Músicas<//>
    <${Top5} itens=${d.top_musicas} nome=${(m) => m.nome} sub=${(m) => m.artista} valor=${(m) => fmtNum(m.plays)} />
  <//>`;
}

export function Anos({ d, i }) {
  const maior = Math.max(...d.anos.map((a) => a.horas)) || 1;
  const topo = d.anos.reduce((a, b) => (b.horas > a.horas ? b : a));
  return html`<${Slide} tipo="anos" i=${i} capa=${capaDe(topo.top_musica?.nome)}>
    <${Kicker}>Ano a ano<//>
    <${Entra} i=${1} tag="h3" classe="st-titulo menor">${topo.ano} foi o seu ano mais musical<//>
    <ol class="st-anos">
      ${d.anos.map((a, k) => html`<li class=${`entra${a.ano === topo.ano ? ' st-ano-topo' : ''}`} style=${{ '--i': k + 2 }}>
        <span class="st-ano">${a.ano}</span>
        <span class="st-ano-barra"><i class="st-barra-valor" style=${{ '--valor': a.horas / maior, '--i': k + 2 }}></i><small>${a.top_artistas[0]?.nome || '—'}</small></span>
        <em>${fmtNum(a.horas)} h</em></li>`)}
    </ol>
    <${Entra} i=${d.anos.length + 2} tag="p" classe="st-nota">Barra: horas no ano · nome: artista nº 1 daquele ano.<//>
  <//>`;
}

export function Descobertas({ d, ativo, i }) {
  const varios = d.anos.length > 1;
  const curioso = d.anos.reduce((a, b) => (b.novos_artistas > a.novos_artistas ? b : a));
  const maior = Math.max(...d.anos.map((a) => a.novos_artistas)) || 1;
  const curta = descobertasCurta(d.medidas.descobertas || 0);
  return html`<${Slide} tipo="descobertas" i=${i} capa=${capaDe(d.anos.at(-1)?.top_artistas[0]?.nome)}>
    <${Kicker}>Descobertas<//>
    <${Entra} i=${1} classe="st-cartao st-vidro">
      <div class="st-mega"><${Contador} valor=${d.quantidade_artistas} ativo=${ativo} /></div>
      <span class="st-rotulo">artistas diferentes</span>
    <//>
    ${varios ? html`
      <${Entra} i=${2} tag="p">Seu ano mais curioso foi <strong>${curioso.ano}</strong>, com ${fmtNum(curioso.novos_artistas)} artistas novos.<//>
      <div class="st-colunas">${d.anos.map((a, k) => html`<div class="entra" style=${{ '--i': k + 3 }}>
        <em>${fmtNum(a.novos_artistas)}</em><i style=${{ '--valor': a.novos_artistas / maior }}></i><span>${String(a.ano).slice(2)}</span></div>`)}</div>` : html`
      <${Entra} i=${2} tag="p">1 artista novo a cada <strong>${fmtNum(curta.n)} plays</strong>.<//>
      <${Entra} i=${3} tag="p" classe="st-destaque">${curta.frase}<//>`}
  <//>`;
}

export function Recorde({ d, ativo, i }) {
  const r = d.repeticao_dia;
  return html`<${Slide} tipo="recorde" i=${i} capa=${capaDe(r.nome)}>
    <${Kicker}>O dia mais musical<//>
    <${Entra} i=${1} tag="h3" classe="st-titulo menor">${dataBr(d.dia_recorde)}<//>
    <${Entra} i=${2} classe="st-cartao st-vidro">
      <div class="st-mega"><${Contador} valor=${d.horas_dia_recorde} casas=${1} ativo=${ativo} /></div>
      <span class="st-rotulo">horas em um único dia</span>
    <//>
    <${Entra} i=${3} tag="p" classe="st-destaque">${fraseRecorde(d.horas_dia_recorde)}<//>
    ${d.artista_dia_recorde && html`<${Entra} i=${4} tag="p">Quem mais tocou: <strong>${d.artista_dia_recorde}</strong>.<//>`}
    <${Entra} i=${5} classe="st-callout st-vidro">Em ${dataBr(d.data_repeticao_dia)}, <strong>${r.nome}</strong> (${r.artista}) tocou <strong>${fmtNum(r.plays)} vezes</strong>. ${fraseRepeticao(r.plays)}<//>
  <//>`;
}

// Relógio de 24 h: uma barra radial por hora, o pico em destaque.
function Relogio({ plays, pico }) {
  const maior = Math.max(...plays) || 1;
  const ponto = (h, r) => { const a = (h / 24) * 2 * Math.PI - Math.PI / 2; return [100 + r * Math.cos(a), 100 + r * Math.sin(a)]; };
  return html`<svg class="st-relogio" viewBox="0 0 200 200" aria-hidden="true">
    <circle cx="100" cy="100" r="34" class="st-relogio-centro" />
    ${plays.map((v, h) => {
      const [x1, y1] = ponto(h, 40), [x2, y2] = ponto(h, 40 + 50 * (v / maior));
      return html`<line class=${h === pico ? 'pico' : ''} style=${{ '--i': h }} x1=${x1} y1=${y1} x2=${x2} y2=${y2} />`;
    })}
    ${[0, 6, 12, 18].map((h) => { const [x, y] = ponto(h, 98); return html`<text x=${x} y=${y + 3}>${h}h</text>`; })}
    <text x="100" y="105" class="st-relogio-pico">${pico}h</text>
  </svg>`;
}

export function RelogioSlide({ d, i }) {
  return html`<${Slide} tipo="relogio" i=${i}>
    <${Kicker}>Seu relógio musical<//>
    <${Entra} i=${1} tag="h3" classe="st-titulo menor">Seu horário de pico: ${d.pico_hora}h<//>
    <${Entra} i=${2} classe="st-relogio-caixa"><${Relogio} plays=${d.plays_por_hora} pico=${d.pico_hora} /><//>
    <div class="st-chips">${Object.entries(d.periodos).map(([k, v], n) => html`<span class="st-vidro entra" style=${{ '--i': n + 3 }}><b>${fmtPct(v)}</b> ${k}</span>`)}</div>
    <${Entra} i=${7} tag="p" classe="st-nota">Dia favorito: ${d.dia_semana_favorito} · fuso ${d.fuso_horario}<//>
  <//>`;
}

const Icone = ({ id, classe = '' }) => html`<svg class=${`st-icone ${classe}`} viewBox="0 0 64 64" aria-hidden="true"><use href=${`icones/arquetipos.svg#${id}`} /></svg>`;

export function Maratona({ d, ativo, i }) {
  const fracao = d.dias_com_musica / Math.max(d.dias_periodo, 1);
  return html`<${Slide} tipo="maratona" i=${i}>
    <${Kicker}>Constância<//>
    <${Entra} i=${1} classe="st-cartao st-vidro st-com-icone">
      <${Icone} id="maratonista" classe="desenha" />
      <div><div class="st-mega"><${Contador} valor=${d.sequencia} ativo=${ativo} /></div>
      <span class="st-rotulo">dias seguidos ouvindo música</span></div>
    <//>
    <${Entra} i=${2} tag="p" classe="st-destaque">${fraseSequencia(d.sequencia)}<//>
    <${Entra} i=${3} tag="p">De ${dataBr(d.inicio_sequencia)} a ${dataBr(d.fim_sequencia)}.<//>
    <${Entra} i=${4} tag="p">Música em <strong>${fmtNum(d.dias_com_musica)}</strong> dos ${fmtNum(d.dias_periodo)} dias (${fmtPct(fracao)}). ${fraseConstancia(fracao)}<//>
  <//>`;
}

// Story 11: anos clicáveis. A faixa é data-interativo (o player não trata como navegação);
// abrir um ano pausa o story (motivo "interacao") até "continuar", Esc ou trocar de slide.
export function Fiel({ d, ativo, i, controle }) {
  const [aberto, setAberto] = useState(null);
  const chips = useRef([]);
  const fechar = () => { setAberto(null); controle.retomar('interacao'); };
  const abrir = (ano) => { setAberto(ano); controle.pausar('interacao'); };
  useEffect(() => { if (!ativo && aberto !== null) fechar(); }, [ativo]);
  const tecla = (e, k) => {
    const passo = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
    if (passo) { e.preventDefault(); chips.current[(k + passo + d.anos.length) % d.anos.length]?.focus(); }
    if (e.key === 'Escape' && aberto !== null) { e.preventDefault(); fechar(); }
  };
  const ano = d.anos.find((a) => a.ano === aberto);
  return html`<${Slide} tipo="fiel" i=${i} capa=${capaDe(d.fiel.nome)}>
    <${Kicker}>Fidelidade<//>
    <${Entra} i=${1} tag="h3" classe="st-titulo menor">Presença mais constante no seu top 5<//>
    <${Entra} i=${2} tag="h2" classe="st-nome-xxl">${d.fiel.nome}<//>
    <${Entra} i=${3} tag="p">Esteve no seu top 5 anual em <strong>${d.anos_fiel} de ${d.anos.length} ano${d.anos.length === 1 ? '' : 's'}</strong>.<//>
    <${Entra} i=${4} classe="st-anos-chips">
      <div data-interativo role="group" aria-label="Anos: toque para ver o top daquele ano">
        ${d.anos.map((a, k) => html`<button type="button" ref=${(el) => (chips.current[k] = el)}
          class=${`st-vidro${d.fiel_anos.includes(a.ano) ? ' on' : ''}`} aria-pressed=${aberto === a.ano}
          onClick=${() => (aberto === a.ano ? fechar() : abrir(a.ano))} onKeyDown=${(e) => tecla(e, k)}>${a.ano}</button>`)}
      </div>
    <//>
    <div class="st-painel-ano" aria-live="polite">${ano && html`
      <div class="st-vidro" data-interativo>
        <b>${ano.ano}</b> · ${fmtNum(ano.horas)} h
        <ol>${ano.top_artistas.map((a) => html`<li>${a.nome}</li>`)}</ol>
        <button type="button" class="st-continuar" onClick=${fechar}>Continuar ▸</button>
      </div>`}</div>
  <//>`;
}

// Anel de proporção (SVG): 0–1 → traço.
const Anel = ({ valor, rotulo, destaque }) => html`<div class=${`st-anel${destaque ? ' destaque' : ''}`}>
  <svg viewBox="0 0 44 44" aria-hidden="true"><circle cx="22" cy="22" r="18" pathLength="1" class="fundo" /><circle cx="22" cy="22" r="18" pathLength="1" style=${{ '--valor': valor }} class="valor" /></svg>
  <b>${fmtPct(valor)}</b><span>${rotulo}</span></div>`;

export function Habitos({ d, i }) {
  const h = d.habitos, destaque = habitoDestaque(h);
  const aneis = [['aleatorio', 'no aleatório'], ['pulos', 'faixas puladas'], ['fim_natural', 'ouvidas até o fim'], ['offline', 'offline']].filter(([k]) => h[k] != null);
  const palco = d.plataformas[0];
  return html`<${Slide} tipo="habitos" i=${i}>
    <${Kicker}>Seus hábitos<//>
    <${Entra} i=${1} tag="h3" classe="st-titulo menor">Como você ouve<//>
    <${Entra} i=${2} classe="st-cartao st-vidro"><p class="st-destaque">${destaque.frase}</p><//>
    <div class="st-aneis">${aneis.map(([k, rotulo], n) => html`<div class="entra" style=${{ '--i': n + 3 }}><${Anel} valor=${h[k]} rotulo=${rotulo} destaque=${k === destaque.chave} /></div>`)}</div>
    ${palco && html`<${Entra} i=${8} tag="p">Seu palco principal: <strong>${palco[0]}</strong> (${fmtPct(palco[1])}).<//>`}
  <//>`;
}

// Mesmo texto de arquetipos.AVISO_ARQUETIPOS.
const AVISO_ARQUETIPOS = 'Arquétipos são regras sobre hábitos de escuta neste histórico. Não medem personalidade nem afinidade entre pessoas.';

export function Arquetipo({ d, i }) {
  const a = d.arquetipos, p = a.principal;
  const quase = a.quase.filter((q) => q.chave !== 'explorador');
  return html`<${Slide} tipo="arquetipo" i=${i}>
    <${Kicker}>Seu arquétipo de escuta<//>
    <${Entra} i=${1} classe="st-arquetipo-icone"><${Icone} id=${p.chave} classe="desenha grande" /><span class="sr-only">${p.icone}</span><//>
    <${Entra} i=${3} tag="h2" classe="st-nome-xxl">${p.nome}<//>
    <${Entra} i=${4} tag="p">${p.explicacao}<//>
    <div class="st-chips">
      ${a.secundarios.map((s, n) => html`<span class="st-vidro entra" style=${{ '--i': n + 5 }}><${Icone} id=${s.chave} classe="mini" /> ${s.nome}</span>`)}
      ${quase.map((q, n) => html`<span class="st-vidro entra quase" style=${{ '--i': n + 7 }}>quase ${q.nome} · ${q.limiar < 1 ? fmtPct(q.valor) : fmtNum(q.valor)}</span>`)}
    </div>
    <${Entra} i=${9} tag="p" classe="st-nota">${AVISO_ARQUETIPOS}<//>
  <//>`;
}

export function Resumo({ d, i, replay }) {
  const p = d.arquetipos.principal;
  return html`<${Slide} tipo="resumo" i=${i} capa=${capaDe(d.artista_vida.nome)}>
    <${Entra} i=${0} classe="st-resumo-topo">
      <span class="st-capa st-capa-tipo pequena" style=${{ '--hue': hashNome(d.nome) % 360 }} aria-hidden="true">${d.nome.slice(0, 1).toUpperCase()}</span>
      <div><span class="st-kicker">SyncUp Wrapped</span><b>${d.nome}</b><small>${mesAno(d.inicio)} → ${mesAno(d.fim)}</small></div>
    <//>
    <${Entra} i=${1} classe="st-resumo-grade st-vidro">
      <div><span>Top artistas</span><ol>${d.top_artistas.map((a) => html`<li>${a.nome}</li>`)}</ol></div>
      <div><span>Top músicas</span><ol>${d.top_musicas.map((m) => html`<li>${m.nome}</li>`)}</ol></div>
    <//>
    <${Entra} i=${2} classe="st-resumo-numeros">
      <div class="st-vidro"><span>Horas</span><b>${fmtNum(d.horas)}</b></div>
      <div class="st-vidro"><span>Artistas</span><b>${fmtNum(d.quantidade_artistas)}</b></div>
      <div class="st-vidro"><span>Arquétipo</span><b><${Icone} id=${p.chave} classe="mini" /> ${p.nome}</b></div>
    <//>
    <${Entra} i=${3}><button type="button" class="st-replay st-vidro" onClick=${replay}>↺ Ver de novo</button><//>
  <//>`;
}

export const NOVOS = {
  intro: Intro, primeira: Primeira, artista: Artista, top_artistas: TopArtistas, top_musicas: TopMusicas,
  anos: Anos, descobertas: Descobertas, recorde: Recorde, relogio: RelogioSlide, maratona: Maratona,
  fiel: Fiel, habitos: Habitos, arquetipo: Arquetipo, resumo: Resumo,
};
