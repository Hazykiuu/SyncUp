// Stories do Match como duetos, desenhados a partir de duetos() (match.js), na moldura dos stories.
// Ordem: abertura, um story por dupla (ou trio) formada e o dueto mais afinado por último (pôster).
import { html } from 'preact-htm';
import { CORES } from '../batalha.js';
import { duetos, linhaDoPar, melhorPar } from '../match.js';
import { fmtNum } from './logica.js';
import { Contador, Entra, Kicker, Slide } from './slides.js';

const ROSA = [245, 115, 160];
export const LIMITE_STORY = 3; // refrão e Lado B nos stories e no pôster

// Duas faixas, uma por pessoa, sobrepostas no meio: o trecho comum tem a largura do jaccard (com piso visível).
// shortcut: as duas pessoas ganham a mesma largura (o resultado não traz o tamanho de cada ranking).
export const larguraComum = (j) => (j > 0 ? Math.max(j, 0.04) : 0);
export function Faixas({ l, cor }) {
  const n = l.refrao.length;
  return html`<div class="faixas" style=${{ '--j': larguraComum(l.jaccard), '--ca': cor(l.x), '--cb': cor(l.y) }} role="img"
    aria-label=${n ? `Faixas de ${l.x} e ${l.y}: o trecho do meio são os ${n === 1 ? 'artista em comum' : `${n} artistas em comum`}` : `Faixas de ${l.x} e ${l.y}: nenhum artista em comum`}>
    <i class="faixa-a"></i><i class="faixa-b"></i><i class="faixa-comum"></i></div>
    <p class="faixas-legenda">Artistas em comum</p>`;
}
export const Nomes = ({ nomes, cor, tag = 'h3', classe = '' }) => html`<${tag} class=${`dueto-nomes ${classe}`}>${nomes.map((n, k) => html`${k > 0 && html`<span class="dueto-x" aria-hidden="true"> × </span>`}<span style=${{ color: cor(n) }}>${n}</span>`)}<span class="sr-only">${nomes.join(' e ')}</span></${tag}>`;
const refraoTexto = (lista) => lista.slice(0, LIMITE_STORY).join(' · ');

function Abertura({ r, cor, i }) {
  return html`<${Slide} tipo="abertura" classe="sm" i=${i} cor=${ROSA}>
    <${Kicker}>SyncUp · Match<//>
    <${Entra} i=${1} tag="h2" classe="st-titulo">Os duetos do grupo<//>
    <${Entra} i=${2} classe="sm-elenco">${r.nomes.map((n) => html`<b style=${{ color: cor(n) }}>${n}</b>`)}<//>
    <${Entra} i=${3} tag="p">${r.nomes.length} pessoas, ${r.pares.length} ${r.pares.length === 1 ? 'grupo' : 'grupos'}. O dueto mais afinado sai no fim.<//>
  <//>`;
}

function Linha({ l, cor, ativo, grande }) {
  return html`<div class="sm-linha">
    ${!grande && html`<p class="sm-subpar">${l.x} × ${l.y}</p>`}
    <p class="sm-nota"><span class=${grande ? 'st-mega' : 'sm-pct'}>${grande && ativo !== undefined ? html`<${Contador} valor=${l.pontuacao} casas=${1} ativo=${ativo} />` : fmtNum(l.pontuacao, 1)}%</span><span class="sm-nivel">${l.nivel}</span></p>
    <${Faixas} l=${l} cor=${cor} /></div>`;
}

function Grupo({ d, n, cor, ativo, i }) {
  const trio = d.nomes.length === 3;
  return html`<${Slide} tipo=${`par-${n}`} classe="sm" i=${i} cor=${ROSA}>
    <${Kicker}>${trio ? 'Um trio' : `Dueto nº ${n + 1}`}<//>
    <${Entra} i=${1}><${Nomes} nomes=${d.nomes} cor=${cor} classe=${`st-titulo menor st-quebra${trio ? ' sm-trio' : ''}`} /><//>
    <${Entra} i=${2} classe="sm-linhas">${d.linhas.map((l) => html`<${Linha} l=${l} cor=${cor} ativo=${ativo} grande=${!trio} />`)}<//>
    <${Entra} i=${3} tag="p" classe="sm-refrao"><span>Refrão em comum</span> ${d.refrao.length ? refraoTexto(d.refrao) : 'Nenhum artista em comum nos rankings.'}<//>
    ${!trio && html`<${Entra} i=${4} classe="sm-ladob">${d.ladoB.map((p) => html`<p><span>Lado B de ${p.para}</span> ${p.origens[0].artistas.length ? refraoTexto(p.origens[0].artistas) : 'nada de novo para indicar.'}</p>`)}<//>`}
  <//>`;
}

function Poster({ r, cor, i }) {
  const [x, y] = melhorPar(r);
  const l = linhaDoPar(r, x, y);
  return html`<${Slide} tipo="poster" classe="sm s-poster" i=${i} cor=${ROSA}>
    <${Entra} i=${0} classe="st-poster-topo"><span class="marca"><span class="logo" aria-hidden="true"><i></i><i></i><i></i><i></i></span>SyncUp</span><small>Match</small><//>
    <${Kicker} i=${1}>O dueto mais afinado<//>
    <${Entra} i=${2}><${Nomes} nomes=${[x, y]} cor=${cor} tag="h2" classe="st-titulo st-quebra" /><//>
    <${Entra} i=${3} classe="sm-linhas"><${Linha} l=${l} cor=${cor} grande=${true} /><//>
    ${l.refrao.length > 0 && html`<${Entra} i=${4} tag="p" classe="sm-refrao"><span>Refrão em comum</span> ${refraoTexto(l.refrao)}<//>`}
    <${Entra} i=${5} tag="p" classe="st-poster-pe">Qual é a nossa sintonia? · <b>hazykiuu.github.io/SyncUp</b><//>
  <//>`;
}

export function slidesDoMatch(r) {
  const cor = (n) => CORES[r.nomes.indexOf(n) % CORES.length];
  return [
    { tipo: 'abertura', render: (p) => html`<${Abertura} r=${r} cor=${cor} ...${p} />` },
    ...duetos(r).map((d, n) => ({ tipo: `par-${n}`, titulo: d.nomes.join(' × '), render: (p) => html`<${Grupo} d=${d} n=${n} cor=${cor} ...${p} />` })),
    { tipo: 'poster', titulo: 'O dueto mais afinado', render: (p) => html`<${Poster} r=${r} cor=${cor} ...${p} />` },
  ];
}
