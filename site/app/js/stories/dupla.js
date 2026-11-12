// Stories da Dupla, desenhados a partir de `dupla` (JSON da ponte), na moldura do Wrapped.
// Cor com significado fixo: verde = pessoa A, violeta = pessoa B, rosa = os dois juntos (sintonia).
import { html } from 'preact-htm';
import { dataBr, fmtNum, fraseEmComum, frasePosicao, fraseRelogios, mesAno, textoCents } from './logica.js';
import { Contador, Entra, Kicker, Slide } from './slides.js';

const ROSA = [245, 115, 160];
const inicial = (nome) => (nome.trim()[0] || '?').toUpperCase();
const Avatares = ({ d }) => html`<div class="st-avatares" aria-hidden="true"><span>${inicial(d.a.nome)}</span><span>${inicial(d.b.nome)}</span></div>`;
const Nomes = ({ d }) => html`<span class="st-a">${d.a.nome}</span> + <span class="st-b">${d.b.nome}</span>`;
const plural = (n, um, varios) => `${fmtNum(n)} ${n === 1 ? um : varios}`;

// Afinador da sintonia (cents em logica.js): a agulha (rosa = os dois juntos) gira até o valor; escala de −50 a +50 cents, A4 = 440 Hz.
const TRACOS = Array.from({ length: 21 }, (_, k) => (k - 10) * 5);
function Afinador({ match }) {
  const ponto = (c, r) => { const a = (c / 50) * (Math.PI / 2); return [100 + r * Math.sin(a), 100 - r * Math.cos(a)]; };
  return html`<svg class="st-afinador" viewBox="0 0 200 118" aria-hidden="true" style=${{ '--ang': `${(-(1 - match) * 90).toFixed(1)}deg` }}>
    ${TRACOS.map((c) => { const longo = c % 25 === 0, [x1, y1] = ponto(c, 90), [x2, y2] = ponto(c, longo ? 76 : 82);
      return html`<line class=${Math.abs(c) <= 5 ? 'centro' : longo ? 'longo' : ''} x1=${x1.toFixed(1)} y1=${y1.toFixed(1)} x2=${x2.toFixed(1)} y2=${y2.toFixed(1)} />`; })}
    <line class="agulha" x1="100" y1="100" x2="100" y2="22" /><circle class="pivo" cx="100" cy="100" r="5" />
    <text x="100" y="116">A4 · 440 Hz</text>
  </svg>`;
}

function Abertura({ d, ativo, i }) {
  return html`<${Slide} tipo="abertura" classe="st-duo" i=${i}>
    <${Kicker}>SyncUp · Dupla<//>
    <${Entra} i=${1}><${Avatares} d=${d} /><//>
    <${Entra} i=${2} tag="h2" classe="st-titulo menor st-quebra"><${Nomes} d=${d} /><//>
    <${Entra} i=${3} classe="st-cartao st-vidro">
      <${Afinador} match=${d.match} />
      <div class="st-mega"><${Contador} valor=${d.match * 100} ativo=${ativo} />%</div>
      <span class="st-rotulo">de escuta em comum · ${textoCents(d.match)}</span>
    <//>
    <${Entra} i=${4} tag="p" classe="st-destaque">${fraseEmComum(d.match)}<//>
    <${Entra} i=${5} tag="p">${plural(d.total_comuns, 'artista', 'artistas')} em comum · ${mesAno(d.inicio)} → ${mesAno(d.fim)}<//>
    <${Entra} i=${6} tag="p" classe="st-nota">Mede a escuta neste período, não afinidade entre pessoas.<//>
  <//>`;
}

// Barras lado a lado na mesma escala: dá para comparar entre artistas e entre pessoas.
function EmComum({ d, i }) {
  const maximo = Math.max(1, ...d.em_comum.flatMap((c) => [c.plays_a, c.plays_b]));
  const linha = (nome, plays, lado, k) => html`<div class="st-par">
    <small>${nome}</small><i class=${`st-barra-valor ${lado}`} style=${{ '--valor': plays ? Math.max(plays / maximo, 0.015) : 0, '--i': k }}></i><em>${fmtNum(plays)}</em></div>`;
  return html`<${Slide} tipo="em_comum" classe="st-duo" i=${i}>
    <${Kicker}>O que une vocês<//>
    <${Entra} i=${1} tag="h3" classe="st-titulo menor">${plural(d.total_comuns, 'artista', 'artistas')} em comum<//>
    <ol class="st-comuns">${d.em_comum.map((c, k) => html`
      <li class="entra" style=${{ '--i': k + 2 }}><b>${c.nome}</b>
        ${linha(d.a.nome, c.plays_a, 'a', k + 2)}${linha(d.b.nome, c.plays_b, 'b', k + 2)}</li>`)}</ol>
    <${Entra} i=${6} tag="p" classe="st-nota">Plays de cada um, no período comparado.<//>
  <//>`;
}

function Frente({ d, i }) {
  const cartao = (pessoa, outra, favorito, lado, k) => html`<${Entra} i=${k} classe=${`st-vidro st-lado-${lado}`}>
    <small class=${`st-${lado}`}>O nº 1 de ${pessoa.nome}</small>
    <b>${favorito.nome}</b>
    <small>${fmtNum(favorito.plays)} plays · ${frasePosicao(favorito.posicao_no_outro, outra.nome)}</small>
  <//>`;
  return html`<${Slide} tipo="frente" classe="st-duo" i=${i}>
    <${Kicker}>Frente a frente<//>
    <${Entra} i=${1} tag="h3" classe="st-titulo menor">O favorito de cada um<//>
    <div class="st-frente">${cartao(d.a, d.b, d.favoritos[0], 'a', 2)}${cartao(d.b, d.a, d.favoritos[1], 'b', 3)}</div>
    <${Entra} i=${4} classe="st-chips">
      <span class="st-vidro"><span class="st-a">${d.a.nome}</span> · <b>${fmtNum(d.a.horas)}</b> h de música</span>
      <span class="st-vidro"><span class="st-b">${d.b.nome}</span> · <b>${fmtNum(d.b.horas)}</b> h de música</span>
    <//>
  <//>`;
}

// Os links não trocam de story (data-interativo) e abrem a busca do Spotify em outra aba.
function Apresentar({ d, i }) {
  return html`<${Slide} tipo="apresentar" classe="st-duo" i=${i}>
    <${Kicker}>Para apresentar<//>
    <${Entra} i=${1} tag="h3" classe="st-titulo menor">Um som de cada um para o outro<//>
    <ul class="st-pontes">${d.apresentar.map((p, k) => html`
      <li class="entra st-vidro" style=${{ '--i': k + 2 }}>
        <small>De <span class=${p.de === d.a.nome ? 'st-a' : 'st-b'}>${p.de}</span> para ${p.para}</small>
        <a href=${p.link} target="_blank" rel="noopener" data-interativo>${p.artista}</a>
        <small>${fmtNum(p.plays)} plays de ${p.de}</small>
      </li>`)}</ul>
    <${Entra} i=${7} tag="p" classe="st-nota">Sugestões de artistas que não aparecem no período do outro.<//>
  <//>`;
}

// Um relógio de 24 h com as duas pessoas: por hora, a barra de A e a de B lado a lado.
function RelogioDuplo({ a, b }) {
  const ponto = (h, r) => { const ang = (h / 24) * 2 * Math.PI - Math.PI / 2; return [100 + r * Math.cos(ang), 100 + r * Math.sin(ang)]; };
  const barras = (pessoa, lado, desvio) => {
    const maior = Math.max(...pessoa.plays_por_hora) || 1;
    return pessoa.plays_por_hora.map((v, h) => {
      const [x1, y1] = ponto(h + desvio, 40), [x2, y2] = ponto(h + desvio, 40 + 50 * (v / maior));
      return html`<line class=${`${lado}${h === pessoa.pico_hora ? ' pico' : ''}`} style=${{ '--i': h }} x1=${x1} y1=${y1} x2=${x2} y2=${y2} />`;
    });
  };
  return html`<svg class="st-relogio st-relogio-duplo" viewBox="0 0 200 200" aria-hidden="true">
    <circle cx="100" cy="100" r="34" class="st-relogio-centro" />
    ${barras(a, 'a', -0.2)}${barras(b, 'b', 0.2)}
    ${[0, 6, 12, 18].map((h) => { const [x, y] = ponto(h, 98); return html`<text x=${x} y=${y + 3}>${h}h</text>`; })}
  </svg>`;
}

function Relogios({ d, i }) {
  return html`<${Slide} tipo="relogios" classe="st-duo" i=${i}>
    <${Kicker}>Os relógios de vocês<//>
    <${Entra} i=${1} tag="h3" classe="st-titulo menor">${fraseRelogios(d.a.pico_hora, d.b.pico_hora)}<//>
    <${Entra} i=${2} classe="st-relogio-caixa"><${RelogioDuplo} a=${d.a} b=${d.b} /><//>
    <${Entra} i=${3} classe="st-chips">
      <span class="st-vidro"><span class="st-a">${d.a.nome}</span> · pico às <b>${d.a.pico_hora}h</b></span>
      <span class="st-vidro"><span class="st-b">${d.b.nome}</span> · pico às <b>${d.b.pico_hora}h</b></span>
    <//>
  <//>`;
}

function Sintonia({ d, ativo, i }) {
  const s = d.sintonia;
  if (!s.momentos) {
    return html`<${Slide} tipo="sintonia" cor=${ROSA} i=${i}>
      <${Kicker}>Em sintonia<//>
      <${Entra} i=${1} tag="h3" classe="st-titulo menor">Ainda não ouviram a mesma música ao mesmo tempo neste período.<//>
      <${Entra} i=${2} classe="st-cartao st-vidro">
        <div class="st-mega"><${Contador} valor=${s.quase} ativo=${ativo} /></div>
        <span class="st-rotulo">vezes quase juntos (até 1 h de diferença)</span>
      <//>
    <//>`;
  }
  return html`<${Slide} tipo="sintonia" cor=${ROSA} i=${i}>
    <${Kicker}>Em sintonia<//>
    <${Entra} i=${1} tag="h3" classe="st-titulo menor">Vocês ouviram juntos<//>
    <${Entra} i=${2} classe="st-cartao st-vidro">
      <div class="st-mega"><${Contador} valor=${s.minutos} ativo=${ativo} /></div>
      <span class="st-rotulo">minutos ao mesmo tempo</span>
    <//>
    <${Entra} i=${3} tag="p">Foram <strong>${plural(s.momentos, 'momento', 'momentos')}</strong> com a mesma música tocando para os dois, no mesmo instante.<//>
    <${Entra} i=${4} classe="st-chips">
      ${s.hora_favorita != null && html`<span class="st-vidro"><b>${s.hora_favorita}h</b> a hora favorita</span>`}
      ${s.dia_favorito && html`<span class="st-vidro">mais na <b>${s.dia_favorito}</b></span>`}
      <span class="st-vidro"><b>${fmtNum(s.quase)}</b> quase juntos</span>
    <//>
  <//>`;
}

function SintoniaMusica({ d, i }) {
  const s = d.sintonia, m = s.musica, p = s.primeira;
  const maior = Math.max(...s.por_mes.map(([, v]) => v)) || 1;
  const rotulo = (mes, k) => (k === 0 || mes.endsWith('-01') ? `${mes.slice(5)}/${mes.slice(2, 4)}` : '');
  return html`<${Slide} tipo="sintonia_musica" cor=${ROSA} i=${i}>
    <${Kicker}>A música de vocês<//>
    <${Entra} i=${1} tag="h2" classe="st-nome-xxl st-nome-medio">${m.nome}<//>
    <${Entra} i=${2} tag="p" classe="st-sub">${m.artista}<//>
    <${Entra} i=${3} classe="st-chips">
      <span class="st-vidro"><b>${fmtNum(m.vezes)}</b> ${m.vezes === 1 ? 'vez juntos' : 'vezes juntos'}</span>
      <span class="st-vidro"><b>${fmtNum(m.minutos)}</b> min</span>
    <//>
    ${p && html`<${Entra} i=${4} tag="p">A primeira vez foi com <strong>${p.musica}</strong>, em ${dataBr(p.data)}, às ${p.data.slice(11, 16)}.<//>`}
    ${s.por_mes.length > 1 && html`<${Entra} i=${5} classe="st-meses">
      <small>Quando a sintonia aconteceu</small>
      <div class="st-colunas">${s.por_mes.map(([mes, v], k) => html`<div><span></span><i style=${{ '--valor': v / maior, '--i': k }}></i><em>${rotulo(mes, k)}</em></div>`)}</div>
    <//>`}
    <${Entra} i=${6} tag="p" classe="st-nota">Ao mesmo tempo = a mesma faixa tocando para os dois, com pelo menos 30 s em comum.<//>
  <//>`;
}

// Último story = o pôster para o print: termina com o convite para comparar no SyncUp.
function Poster({ d, ativo, i }) {
  const s = d.sintonia;
  return html`<${Slide} tipo="poster" classe="st-duo" i=${i}>
    <${Entra} i=${0} classe="st-poster-topo">
      <span class="marca"><span class="logo" aria-hidden="true"><i></i><i></i><i></i><i></i></span>SyncUp</span>
      <small>${mesAno(d.inicio)} → ${mesAno(d.fim)}</small>
    <//>
    <${Entra} i=${1}><${Avatares} d=${d} /><//>
    <${Entra} i=${2} tag="h2" classe="st-titulo menor st-quebra"><${Nomes} d=${d} /><//>
    <${Entra} i=${3} tag="p"><b class="st-poster-horas"><${Contador} valor=${d.match * 100} ativo=${ativo} />%</b> de escuta em comum · ${plural(d.total_comuns, 'artista', 'artistas')} em comum<//>
    ${s?.momentos > 0 && html`<${Entra} i=${4} classe="st-cartao st-vidro st-poster-sintonia">
      <span class="st-kicker">Em sintonia</span>
      <b>${fmtNum(s.minutos)} min ouvindo juntos</b>
      ${s.musica && html`<small>A música de vocês: ${s.musica.nome}</small>`}
    <//>`}
    ${d.em_comum.length > 0 && html`<${Entra} i=${5} classe="st-poster-fatos">${d.em_comum.map((c) => html`<span class="st-vidro">${c.nome}</span>`)}<//>`}
    <${Entra} i=${6} tag="p" classe="st-poster-pe">Compare a sua sintonia comigo · <b>hazykiuu.github.io/SyncUp</b><//>
  <//>`;
}

export const SLIDES_DUPLA = {
  abertura: Abertura, em_comum: EmComum, frente: Frente, apresentar: Apresentar, relogios: Relogios,
  sintonia: Sintonia, sintonia_musica: SintoniaMusica, poster: Poster,
};
