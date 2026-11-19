// Stories da Batalha, desenhados a partir do JSON de montarBatalha (batalha.js), na moldura dos stories.
// Ordem: abertura, uma rodada por story, dupla mais afinada, quadro de medalhas e o pódio por último (regra do Carlos).
// Selos e títulos na tipografia do Kicker; pódio sem mola nem quique (trava anti-slop do plano).
import { html } from 'preact-htm';
import { fmtNum, NOTA_APROX } from './logica.js';
import { Contador, Entra, Kicker, Slide } from './slides.js';

const rgb = (hex) => [1, 3, 5].map((k) => parseInt(hex.slice(k, k + 2), 16));
const inicial = (nome) => ([...nome.trim()][0] || '?').toUpperCase();
const SELOS = { 'por-um-triz': 'Por um triz', massacre: 'Massacre' };
const MEDALHAS = [['ouro', 'ouro', 'ouros'], ['prata', 'prata', 'pratas'], ['bronze', 'bronze', 'bronzes']];
const textoMedalhas = (m) => MEDALHAS.filter(([t]) => m[t]).map(([t, um, varios]) => `${m[t]} ${m[t] === 1 ? um : varios}`).join(', ') || 'sem medalha';
const Avatar = ({ l, classe = '' }) => html`<span class=${`sb-avatar ${classe}`} style=${{ '--lut': l.cor }} aria-hidden="true">${inicial(l.nome)}</span>`;
const Medalhas = ({ m }) => html`<span class="sb-medalhas"><span class="sr-only">${textoMedalhas(m)}</span>
  ${MEDALHAS.map(([t]) => m[t] > 0 && html`<span class=${`sb-med ${t}`} aria-hidden="true"><i></i>${m[t]}</span>`)}</span>`;
const ordemMedalhas = (b) => b.lutadores.map((_, i) => i).sort((i, j) => {
  const x = b.lutadores[i].medalhas, y = b.lutadores[j].medalhas;
  return y.ouro - x.ouro || y.prata - x.prata || y.bronze - x.bronze || i - j;
});

function Abertura({ b, i }) {
  return html`<${Slide} tipo="abertura" classe="sb" i=${i} cor=${rgb(b.lutadores[0].cor)}>
    <${Kicker}>SyncUp · Batalha<//>
    <${Entra} i=${1} tag="h2" classe="st-titulo">${b.lutadores.length} na arena<//>
    <${Entra} i=${2} classe="sb-elenco">${b.lutadores.map((l) => html`<span><${Avatar} l=${l} /><b>${l.nome}</b></span>`)}<//>
    <${Entra} i=${3} tag="p">${b.rodadas.length} rodadas. Quem vence leva ouro; o pódio sai no fim.<//>
  <//>`;
}

// Cada rodada tem um desenho ligado ao que mede (pista, discos, constelação…), na ordem da classificação.
// Frações: do maior valor da rodada, ou da escala natural (% e 24 h). Animações: só transform, opacidade e traço.
const FRASES = {
  horas: 'Horas de música no período.', plays: 'Plays de pelo menos 30 segundos.', artistas: 'Artistas diferentes que cada um ouviu.',
  musicas: 'Músicas diferentes na estante de cada um.', sequencia: 'Dias seguidos ouvindo, sem falhar um.', dia: 'O dia em que mais ouviu, nas 24 horas.',
  coruja: 'Fatia dos plays entre meia-noite e 6 h.', repeteco: 'A mesma música, repetida num dia só.', fa: 'Fatia dos plays no artista favorito.',
  paciencia: 'Fatia de músicas puladas. Aqui, menos é melhor.',
};
const arco = (f, classe = '') => html`<circle class="sb-arco-fundo" cx="20" cy="20" r="15" pathLength="1" />
  <circle class=${`sb-arco ${classe}`} cx="20" cy="20" r="15" pathLength="1" style=${{ '--f': f, strokeDasharray: `${f} 1` }} />`;
const GLIFOS = {
  // Pequenos múltiplos: um desenho por pessoa, numa grade.
  plays: (f) => html`<svg viewBox="0 0 40 40" class="sb-glifo"><circle cx="20" cy="20" r="18" class="sb-vinil" />
    ${[13, 9.5].map((r) => html`<circle cx="20" cy="20" r=${r} class="sb-sulco" />`)}${arco(f)}<circle cx="20" cy="20" r="3.4" class="sb-selo-disco" /></svg>`,
  fa: (f) => html`<svg viewBox="0 0 40 40" class="sb-glifo">${arco(f, 'grosso')}</svg>`,
  dia: (f) => html`<svg viewBox="0 0 40 40" class="sb-glifo">${Array.from({ length: 24 }, (_, h) => {
    const a = (h / 24) * 2 * Math.PI, x = 20 + 17 * Math.sin(a), y = 20 - 17 * Math.cos(a), x2 = 20 + 14.5 * Math.sin(a), y2 = 20 - 14.5 * Math.cos(a);
    return html`<line x1=${x.toFixed(1)} y1=${y.toFixed(1)} x2=${x2.toFixed(1)} y2=${y2.toFixed(1)} class=${h < Math.round(f * 24) ? 'sb-hora acesa' : 'sb-hora'} style=${{ '--n': h }} />`;
  })}</svg>`,
  coruja: (f, k) => html`<svg viewBox="0 0 40 40" class="sb-glifo"><defs><clipPath id=${`sb-lua-${k}`}><rect x="2" y="2" width=${(36 * f).toFixed(1)} height="36" class="sb-lua-luz" /></clipPath></defs>
    <circle cx="20" cy="20" r="16" class="sb-lua" /><circle cx="20" cy="20" r="16" class="sb-lua acesa" clip-path=${`url(#sb-lua-${k})`} /></svg>`,
};
// Lineares: uma linha por pessoa.
const LINHAS = {
  horas: (f) => html`<span class="sb-pista"><i class="sb-corredor" style=${{ '--f': f }}></i></span>`,
  artistas: (f) => html`<span class="sb-pontos">${Array.from({ length: 20 }, (_, n) => html`<i class=${n < Math.max(1, Math.round(f * 20)) ? 'aceso' : ''} style=${{ '--n': n }}></i>`)}</span>`,
  sequencia: (f) => html`<span class="sb-corrente">${Array.from({ length: 14 }, (_, n) => html`<i class=${n < Math.max(1, Math.round(f * 14)) ? 'aceso' : ''} style=${{ '--n': n }}></i>`)}</span>`,
  repeteco: (f, v, maior) => {
    const marcas = maior <= 25 ? v : Math.round(f * 25);
    return html`<span class="sb-tally">${Array.from({ length: Math.ceil(marcas / 5) }, (_, g) => {
      const n = Math.min(5, marcas - g * 5);
      return html`<i class=${`g${n}`} style=${{ '--n': g }}>${Array.from({ length: Math.min(n, 4) }, () => html`<b></b>`)}${n === 5 && html`<s></s>`}</i>`;
    })}</span>`;
  },
  paciencia: (f) => html`<span class="sb-casas">${Array.from({ length: 10 }, (_, n) => html`<i class=${n < Math.round(f * 10) ? 'pulou' : ''} style=${{ '--n': n }}></i>`)}</span>`,
};

function Rodada({ b, r, i }) {
  const ordem = r.valores.map((_, k) => k).sort((x, y) => r.posicoes[x] - r.posicoes[y] || x - y);
  const venc = ordem.filter((k) => r.posicoes[k] === 1);
  const maior = Math.max(...r.valores) || 1;
  const escala = { coruja: 100, fa: 100, paciencia: 100, dia: 24 }[r.chave] ?? maior;
  const fracao = (v) => Math.min(1, v / escala);
  const pessoa = (k) => b.lutadores[k];
  let corpo;
  if (GLIFOS[r.chave]) {
    corpo = html`<ol class=${`sb-grade sb-${r.chave}`}>${ordem.map((k, n) => html`
      <li class=${`entra${r.posicoes[k] === 1 ? ' lider' : ''}`} style=${{ '--i': 3 + n * 0.4, '--lut': pessoa(k).cor }}>
        ${GLIFOS[r.chave](fracao(r.valores[k]), k)}<span class="sb-nome">${pessoa(k).nome}</span><em>${fmtNum(r.valores[k], r.casas)}</em></li>`)}</ol>`;
  } else if (r.chave === 'musicas') {
    corpo = html`<ol class="sb-estante">${ordem.map((k, n) => html`
      <li class=${`entra${r.posicoes[k] === 1 ? ' lider' : ''}`} style=${{ '--i': 3 + n * 0.4, '--lut': pessoa(k).cor, '--f': Math.max(0.03, fracao(r.valores[k])) }}>
        <em>${fmtNum(r.valores[k], r.casas)}</em><span class="sb-lombada"></span><span class="sb-nome">${pessoa(k).nome}</span></li>`)}</ol>`;
  } else {
    const linha = LINHAS[r.chave] || LINHAS.horas;
    corpo = html`<ol class=${`sb-linhas sb-${r.chave}`}>${ordem.map((k, n) => html`
      <li class=${`entra${r.posicoes[k] === 1 ? ' lider' : ''}`} style=${{ '--i': 3 + n * 0.4, '--lut': pessoa(k).cor }}>
        <span class="sb-pos">${r.posicoes[k]}º</span><span class="sb-nome">${pessoa(k).nome}</span>
        ${linha(fracao(r.valores[k]), r.valores[k], maior)}<em>${fmtNum(r.valores[k], r.casas)}</em></li>`)}</ol>`;
  }
  return html`<${Slide} tipo=${`rodada-${r.chave}`} classe=${`sb sb-r-${r.chave}`} i=${i} cor=${rgb(pessoa(venc[0]).cor)}>
    <${Entra} i=${0} classe="sb-cabeca"><span class="st-kicker">${r.titulo}</span>${r.destaque && html`<span class="sb-selo">${SELOS[r.destaque]}</span>`}<//>
    <${Entra} i=${1} tag="h3" classe="st-titulo menor sb-vence">${venc.map((k) => pessoa(k).nome).join(' e ')}<//>
    <${Entra} i=${2} tag="p" classe="sb-valor"><b>${fmtNum(r.valores[venc[0]], r.casas)}</b> ${r.unidade}<//>
    ${corpo}
    <${Entra} i=${6} tag="p" classe="st-nota">${FRASES[r.chave]}${b.aproximado && (r.chave === 'horas' || r.chave === 'dia') ? ` ${NOTA_APROX}` : ''}<//>
    ${r.alerta && html`<${Entra} i=${7} tag="p" classe="sb-rodape"><span class="sb-selo">Dedinho nervoso</span> ${r.alerta.nome} pulou ${fmtNum(r.alerta.valor, 1)}%<//>`}
  <//>`;
}

function Afinada({ b, ativo, i }) {
  const [x, y] = b.afinada.par.map((k) => b.lutadores[k]);
  return html`<${Slide} tipo="afinada" classe="sb" i=${i} cor=${[245, 115, 160]}>
    <${Kicker}>A dupla mais afinada<//>
    <${Entra} i=${1} classe="sb-dupla"><${Avatar} l=${x} /><${Avatar} l=${y} /><//>
    <${Entra} i=${2} tag="h3" classe="st-titulo menor st-quebra">${x.nome} & ${y.nome}<//>
    <${Entra} i=${3} classe="st-cartao st-vidro"><div class="st-mega"><${Contador} valor=${b.afinada.valor} casas=${1} ativo=${ativo} />%</div>
      <span class="st-rotulo">de escuta em comum</span><//>
    ${b.afinada.artistaComum && html`<${Entra} i=${4} tag="p" classe="sb-unidos">Unidos por <b>${b.afinada.artistaComum}</b><//>`}
    <${Entra} i=${5} tag="p" classe="st-nota">Conta só o que vocês ouviram neste período.<//>
  <//>`;
}

function Quadro({ b, i }) {
  return html`<${Slide} tipo="medalhas" classe="sb" i=${i} cor=${[245, 197, 66]}>
    <${Kicker}>Quadro de medalhas<//>
    <${Entra} i=${1} tag="h3" classe="st-titulo menor">${b.detalhe ? 'Decidido no detalhe' : 'Contagem final'}<//>
    <ol class="sb-quadro">${ordemMedalhas(b).map((k, n) => {
      const l = b.lutadores[k];
      return html`<li class="entra" style=${{ '--i': 2 + n * 0.5 }}><${Avatar} l=${l} classe="mini" /><span class="sb-nome">${l.nome}</span><${Medalhas} m=${l.medalhas} /></li>`;
    })}</ol>
  <//>`;
}

// Último story: o pódio (2º, 1º, 3º), o título de classe e o convite para comparar. Empates: "Empate no topo" ou "Empate geral".
function Podio({ b, i }) {
  const campeoes = b.campeoes.map((k) => b.lutadores[k]);
  const ordem = ordemMedalhas(b).slice(0, 3);
  const igual = (x, y) => x.ouro === y.ouro && x.prata === y.prata && x.bronze === y.bronze;
  const pos = ordem.map((k, n) => 1 + ordem.slice(0, n).filter((j) => !igual(b.lutadores[j].medalhas, b.lutadores[k].medalhas)).length);
  const geral = campeoes.length >= 3;
  return html`<${Slide} tipo="podio" classe="sb s-poster" i=${i} cor=${rgb(campeoes[0].cor)}>
    <${Entra} i=${0} classe="st-poster-topo"><span class="marca"><span class="logo" aria-hidden="true"><i></i><i></i><i></i><i></i></span>SyncUp</span><small>Batalha</small><//>
    <${Entra} i=${1} classe="sb-cabeca"><span class="st-kicker">${campeoes.length === 1 ? 'Quem levou' : campeoes.length === 2 ? 'Empate no topo' : 'Empate geral'}</span><//>
    ${!geral && html`<${Entra} i=${2} tag="h2" classe="st-titulo sb-vence">${campeoes.map((l) => l.nome).join(' e ')}<//>`}
    ${geral
      ? html`<${Entra} i=${2} classe="sb-empate">${campeoes.map((l) => html`<span><${Avatar} l=${l} classe="mini" /><b>${l.nome}</b></span>`)}<//>
        <${Entra} i=${3} tag="p">Todos com ${textoMedalhas(campeoes[0].medalhas)}.<//>`
      : html`<ol class="sb-podio" aria-label="Pódio">${[1, 0, 2].filter((n) => n < ordem.length).map((n) => {
        const l = b.lutadores[ordem[n]];
        return html`<li class=${`p${pos[n]}`} style=${{ '--lut': l.cor, '--k': 2 - n }}>
          <${Avatar} l=${l} /><b class="sb-nome">${l.nome}</b>
          ${pos[n] === 1 && b.titulo && html`<small class="sb-titulo">${b.titulo}</small>`}
          <${Medalhas} m=${l.medalhas} /><span class="sb-bloco"><span>${pos[n]}º</span></span></li>`;
      })}</ol>`}
    <${Entra} i=${6} tag="p" classe="st-poster-pe">Compare comigo · <b>hazykiuu.github.io/SyncUp</b><//>
  <//>`;
}

// Slides na ordem do plano; cada rodada tem tipo próprio (o player usa o tipo como chave).
export function slidesDaBatalha(b) {
  return [
    { tipo: 'abertura', render: (p) => html`<${Abertura} b=${b} ...${p} />` },
    ...b.rodadas.map((r) => ({ tipo: `rodada-${r.chave}`, titulo: r.titulo, render: (p) => html`<${Rodada} b=${b} r=${r} ...${p} />` })),
    { tipo: 'afinada', render: (p) => html`<${Afinada} b=${b} ...${p} />` },
    { tipo: 'medalhas', render: (p) => html`<${Quadro} b=${b} ...${p} />` },
    { tipo: 'podio', render: (p) => html`<${Podio} b=${b} ...${p} />` },
  ];
}
