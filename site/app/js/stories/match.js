// Stories do Match, desenhados a partir de conciliar() (match.js), na moldura dos stories.
// Ordem: abertura, um story por par (ou trio) formado e o casal do grupo por último (pôster).
import { html } from 'preact-htm';
import { CORES } from '../batalha.js';
import { chave, melhorPar } from '../match.js';
import { fmtNum } from './logica.js';
import { Contador, Entra, Kicker, Slide } from './slides.js';

const ROSA = [245, 115, 160];
const inicial = (nome) => ([...nome.trim()][0] || '?').toUpperCase();
const coracoes = (p) => (p > 0 ? Math.max(1, Math.round(Math.min(1, p / 25) * 5)) : 0);
const CORACAO = 'M12 21s-7.5-4.6-9.6-9.4C.9 8 3.1 4 6.9 4c2.2 0 3.7 1.2 5.1 3 1.4-1.8 2.9-3 5.1-3 3.8 0 6 4 4.5 7.6C19.5 16.4 12 21 12 21Z';
const Coracao = ({ cheio = true }) => html`<svg viewBox="0 0 24 24" class=${`sm-coracao${cheio ? ' cheio' : ''}`} aria-hidden="true"><path d=${CORACAO} /></svg>`;

function Casal({ nomes, cor }) {
  return html`<span class="sm-casal" aria-hidden="true">${nomes.map((n, k) => html`${k > 0 && html`<span class="sm-elo"><${Coracao} /></span>`}<span class="sm-avatar" style=${{ '--lut': cor(n) }}>${inicial(n)}</span>`)}</span>`;
}
const Medidor = ({ p }) => html`<span class="sm-medidor" role="img" aria-label=${`${coracoes(p)} de 5 corações`}>${[1, 2, 3, 4, 5].map((k) => html`<${Coracao} cheio=${k <= coracoes(p)} />`)}</span>`;

function Abertura({ r, cor, i }) {
  return html`<${Slide} tipo="abertura" classe="sm" i=${i} cor=${ROSA}>
    <${Kicker}>SyncUp · Match<//>
    <${Entra} i=${1} tag="h2" classe="st-titulo">Quem combina com quem?<//>
    <${Entra} i=${2} classe="sm-elenco">${r.nomes.map((n) => html`<span><span class="sm-avatar mini" style=${{ '--lut': cor(n) }} aria-hidden="true">${inicial(n)}</span><b>${n}</b></span>`)}<//>
    <${Entra} i=${3} tag="p">${r.nomes.length} pessoas, ${r.pares.length} ${r.pares.length === 1 ? 'par' : 'pares'}. O casal do grupo sai no fim.<//>
  <//>`;
}

function Par({ r, g, n, cor, ativo, i }) {
  const c = r.detalhes[chave(g[0], g[1])];
  return html`<${Slide} tipo=${`par-${n}`} classe="sm" i=${i} cor=${ROSA}>
    <${Kicker}>${g.length === 3 ? 'Um trio' : `Par nº ${n + 1}`}<//>
    <${Entra} i=${1}><${Casal} nomes=${g} cor=${cor} /><//>
    <${Entra} i=${2} tag="h3" classe="st-titulo menor st-quebra">${g.join(g.length === 3 ? ', ' : ' & ')}<//>
    <${Entra} i=${3} classe="st-cartao st-vidro sm-nota"><div class="st-mega"><${Contador} valor=${c.pontuacao} casas=${1} ativo=${ativo} />%</div>
      <span class="sm-fita">${c.nivel}</span><${Medidor} p=${c.pontuacao} /><//>
    ${c.artistas_comuns.length > 0 && html`<${Entra} i=${4} tag="p" classe="sm-unidos">Unidos por <b>${c.artistas_comuns.slice(0, 3).join(', ')}</b><//>`}
  <//>`;
}

function Poster({ r, cor, i }) {
  const [x, y, c] = melhorPar(r);
  return html`<${Slide} tipo="poster" classe="sm s-poster" i=${i} cor=${ROSA}>
    <${Entra} i=${0} classe="st-poster-topo"><span class="marca"><span class="logo" aria-hidden="true"><i></i><i></i><i></i><i></i></span>SyncUp</span><small>Match</small><//>
    <${Kicker} i=${1}>O casal do grupo<//>
    <${Entra} i=${2}><${Casal} nomes=${[x, y]} cor=${cor} /><//>
    <${Entra} i=${3} tag="h2" classe="st-titulo st-quebra">${x} & ${y}<//>
    <${Entra} i=${4} classe="sm-nota"><div class="st-mega">${fmtNum(c.pontuacao, 1)}%</div><span class="sm-fita">${c.nivel}</span><${Medidor} p=${c.pontuacao} /><//>
    ${c.artistas_comuns.length > 0 && html`<${Entra} i=${5} tag="p" classe="sm-unidos">Unidos por <b>${c.artistas_comuns.slice(0, 3).join(', ')}</b><//>`}
    <${Entra} i=${6} tag="p" classe="st-poster-pe">Qual é a nossa sintonia? · <b>hazykiuu.github.io/SyncUp</b><//>
  <//>`;
}

export function slidesDoMatch(r) {
  const cor = (n) => CORES[r.nomes.indexOf(n) % CORES.length];
  return [
    { tipo: 'abertura', render: (p) => html`<${Abertura} r=${r} cor=${cor} ...${p} />` },
    ...r.pares.map((g, n) => ({ tipo: `par-${n}`, titulo: g.join(g.length === 3 ? ', ' : ' & '), render: (p) => html`<${Par} r=${r} g=${g} n=${n} cor=${cor} ...${p} />` })),
    { tipo: 'poster', titulo: 'O casal do grupo', render: (p) => html`<${Poster} r=${r} cor=${cor} ...${p} />` },
  ];
}
