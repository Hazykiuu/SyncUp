// Aba Gráficos da Dupla: 4 gráficos em HTML (e um SVG pequeno), sem Plotly. Celular primeiro.
// Cada cartão: título com o fato principal, uma linha do que se mede, o desenho (aria-hidden) e a
// mesma informação numa tabela sr-only. Sem animação: é dado para ler.
import { html, useState } from 'preact-htm';
import { fmtNum } from './dupla.js';
import { destaques, escalaArtistas, escalaHoras, gradeHoras, mesCurto, mesLongo, rotulosMeses, VISIVEIS } from './graficos-dupla.js';

const pct = (x) => `${fmtNum(x, 1)}%`;
const LADOS = ['a', 'b'];

// sr-only num div em volta: uma <table> não encolhe para 1 px e, com nomes longos, alargava a página no celular.
function Tabela({ titulo, colunas, linhas }) {
  return html`<div class="sr-only"><table><caption>${titulo}</caption>
    <thead><tr>${colunas.map((c) => html`<th scope="col">${c}</th>`)}</tr></thead>
    <tbody>${linhas.map(([cab, ...resto]) => html`<tr><th scope="row">${cab}</th>${resto.map((v) => html`<td>${v}</td>`)}</tr>`)}</tbody>
  </table></div>`;
}

function Cartao({ id, titulo, sub, largo, children }) {
  return html`<section class=${`gr-cartao vidro${largo ? ' gr-largo' : ''}`} aria-labelledby=${id}>
    <h3 id=${id}>${titulo}</h3><p class="gr-sub">${sub}</p>${children}</section>`;
}

// Meia-barra: largura pela escala; mínimo de 2 px quando o valor passa de 0 (senão some).
const largura = (v, w) => (v > 0 ? `max(2px, ${(w * 100).toFixed(2)}%)` : '0');

function LinhaArtista({ x, escala }) {
  return html`<li class="gr-art">
    <span class="gr-nome">${x.nome}</span>
    <span class="gr-val">${pct(x.a)}</span>
    <span class="gr-trilho gr-esq"><i class="gr-barra a" style=${{ inlineSize: largura(x.a, escala(x.a)) }}></i></span>
    <span class="gr-trilho"><i class="gr-barra b" style=${{ inlineSize: largura(x.b, escala(x.b)) }}></i></span>
    <span class="gr-val gr-dir">${pct(x.b)}</span>
  </li>`;
}

function Artistas({ g, d, nomes }) {
  const escala = escalaArtistas(g.artistas);
  const vistos = g.artistas.slice(0, VISIVEIS), resto = g.artistas.slice(VISIVEIS);
  return html`<${Cartao} id="gr-t-artistas" titulo=${d.artistas} largo sub=${`Parte dos plays de cada um que vai para cada artista. Os ${g.artistas.length} mais ouvidos pelos dois.`}>
    <ol class="gr-arts" aria-hidden="true">${vistos.map((x) => html`<${LinhaArtista} x=${x} escala=${escala} />`)}</ol>
    ${resto.length > 0 && html`<details class="dp-mais"><summary>Ver mais ${resto.length}<span class="sr-only"> no gráfico (a tabela já traz todos)</span></summary>
      <ol class="gr-arts" start=${VISIVEIS + 1} aria-hidden="true">${resto.map((x) => html`<${LinhaArtista} x=${x} escala=${escala} />`)}</ol></details>`}
    <${Tabela} titulo="Parte dos plays por artista" colunas=${['Artista', ...nomes]} linhas=${g.artistas.map((x) => [x.nome, pct(x.a), pct(x.b)])} />
  <//>`;
}

// O rótulo do pico perto da borda encosta para dentro, para não sair do cartão.
const ladoRotulo = (h) => (h <= 2 ? 'gr-ini' : h >= 21 ? 'gr-fim' : '');

function Horas({ g, d, nomes }) {
  return html`<${Cartao} id="gr-t-horas" titulo=${d.horas} sub=${d.dias}>
    <div class="gr-eq" aria-hidden="true">
      ${g.horas.map((horas, k) => {
        const alturas = escalaHoras(horas), soma = horas.reduce((s, x) => s + x, 0);
        const pico = horas.indexOf(Math.max(...horas));
        return html`<div class="gr-eq-pessoa">
          <span class="gr-quem"><i class=${LADOS[k]}></i>${nomes[k]}</span>
          ${soma > 0 ? html`<div class="gr-eq-barras">${horas.map((v, h) => html`<span class="gr-eq-col">
              ${h === pico && html`<b class=${`gr-pico ${ladoRotulo(h)}`}>${pct(v)}</b>`}
              <i class=${`gr-barra ${LADOS[k]}`} style=${{ blockSize: largura(v, alturas[h]) }}></i></span>`)}</div>`
            : html`<p class="gr-vazio">Sem plays neste período.</p>`}
        </div>`;
      })}
      <div class="gr-eq-horas">${[0, 6, 12, 18].map((h) => html`<span style=${{ gridColumn: h + 1 }}>${h}h</span>`)}</div>
    </div>
    <${Tabela} titulo="Parte dos plays em cada hora" colunas=${['Hora', ...nomes]} linhas=${g.horas[0].map((v, h) => [`${h}h`, pct(v), pct(g.horas[1][h])])} />
  <//>`;
}

const TRACOS = [
  ['Top 2 artistas', 'Quanto dos plays vai para os 2 artistas mais ouvidos.'],
  ['Top 10 faixas', 'Quanto dos plays vai para as 10 músicas mais ouvidas.'],
  ['Madrugada', 'Quanto dos plays cai entre 0h e 5h59.'],
];

function Tracos({ g, d, nomes }) {
  const { limiares } = g.tracos;
  return html`<${Cartao} id="gr-t-tracos" titulo=${d.tracos} sub="Regras experimentais: o risco branco marca a partir de quanto conta como traço.">
    <ul class="gr-tracos" aria-hidden="true">${TRACOS.map(([nome, frase], i) => html`<li>
      <p class="gr-traco-nome">${nome}<small>${frase} Conta como traço a partir de ${limiares[i]}%.</small></p>
      ${LADOS.map((lado, k) => {
        const v = g.tracos[lado][i];
        return html`<div class="gr-traco-linha">
          <span class="gr-quem"><i class=${lado}></i>${nomes[k]}</span>
          <span class="gr-trilho-t"><i class=${`gr-barra ${lado}`} style=${{ inlineSize: largura(v, Math.min(1, v / 100)) }}></i><s style=${{ insetInlineStart: `${limiares[i]}%` }}></s></span>
          <span class=${`gr-val gr-dir${v >= limiares[i] ? ' gr-forte' : ''}`}>${pct(v)}</span>
        </div>`;
      })}
    </li>`)}</ul>
    <${Tabela} titulo="Traços de escuta" colunas=${['Traço', ...nomes, 'Limiar']} linhas=${TRACOS.map(([nome], i) => [nome, pct(g.tracos.a[i]), pct(g.tracos.b[i]), `${limiares[i]}%`])} />
  <//>`;
}

function Meses({ g, d, nomes }) {
  const { meses } = g;
  const [foco, setFoco] = useState(-1);
  if (!meses.length) return null;
  const { topo, linhas } = gradeHoras(meses);
  const n = meses.length;
  const x = (i) => (n === 1 ? 50 : (i / (n - 1)) * 100);
  const y = (v) => 100 - (v / topo) * 100;
  const pontos = (lado) => meses.map((m, i) => `${x(i)},${y(m[lado])}`).join(' ');
  // Toque ou mouse: o mês mais perto do dedo. Sem bloquear a rolagem (nada de touch-action: none).
  const escolher = (e) => {
    const caixa = e.currentTarget.getBoundingClientRect();
    // O dedo pode sair da caixa sem soltar (o toque continua mandando eventos): limita ao primeiro e ao último mês.
    setFoco(n === 1 ? 0 : Math.max(0, Math.min(n - 1, Math.round(((e.clientX - caixa.left) / caixa.width) * (n - 1)))));
  };
  const m = meses[Math.max(0, foco)];
  const pontosVistos = foco >= 0 ? [foco] : n === 1 ? [0] : [];
  return html`<${Cartao} id="gr-t-meses" titulo=${d.meses} largo sub="Horas ouvidas em cada mês, contando todas as execuções. O primeiro e o último mês podem estar pela metade.">
    <p class="gr-leitura" aria-hidden="true">${foco >= 0
      ? html`<b>${mesLongo(m.mes)}</b> <span><i class="a"></i>${fmtNum(m.a, 0)} h</span> <span><i class="b"></i>${fmtNum(m.b, 0)} h</span>`
      : 'Toque ou passe o mouse no gráfico para ver cada mês.'}</p>
    <div class="gr-meses" aria-hidden="true">
      <div class="gr-eixo-y">${linhas.map((v) => html`<span style=${{ insetBlockEnd: `${(v / topo) * 100}%` }}>${fmtNum(v, 0)} h</span>`)}</div>
      <div class="gr-plot" onPointerDown=${escolher} onPointerMove=${escolher} onPointerLeave=${(e) => e.pointerType === 'mouse' && setFoco(-1)}>
        ${linhas.map((v) => html`<span class="gr-grade" style=${{ insetBlockEnd: `${(v / topo) * 100}%` }}></span>`)}
        ${foco >= 0 && html`<span class="gr-mira" style=${{ insetInlineStart: `${x(foco)}%` }}></span>`}
        ${n > 1 && html`<svg viewBox="0 0 100 100" preserveAspectRatio="none">
          <polyline class="gr-linha a" points=${pontos('a')} vector-effect="non-scaling-stroke" />
          <polyline class="gr-linha b" points=${pontos('b')} vector-effect="non-scaling-stroke" />
        </svg>`}
        ${pontosVistos.flatMap((i) => LADOS.map((lado) => html`<span class=${`gr-ponto ${lado}`} style=${{ insetInlineStart: `${x(i)}%`, insetBlockStart: `${y(meses[i][lado])}%` }}></span>`))}
      </div>
      <div class="gr-eixo-x">${rotulosMeses(meses).map(({ i, x: px }) => html`<span class=${i === 0 && n > 1 ? 'gr-ini' : i === n - 1 && n > 1 ? 'gr-fim' : ''} style=${{ insetInlineStart: `${px}%` }}>${mesCurto(meses[i].mes)}</span>`)}</div>
    </div>
    <${Tabela} titulo="Horas por mês" colunas=${['Mês', ...nomes]} linhas=${meses.map((mes) => [mesLongo(mes.mes), `${fmtNum(mes.a, 1)} h`, `${fmtNum(mes.b, 1)} h`])} />
  <//>`;
}

export function GraficosDupla({ g, nomes }) {
  const d = destaques(g, nomes);
  return html`<div class="gr">
    <p class="gr-chave">${nomes.map((nome, k) => html`<span><i class=${LADOS[k]}></i>${nome}</span>`)}</p>
    <${Artistas} g=${g} d=${d} nomes=${nomes} />
    <${Horas} g=${g} d=${d} nomes=${nomes} />
    <${Tracos} g=${g} d=${d} nomes=${nomes} />
    <${Meses} g=${g} d=${d} nomes=${nomes} />
  </div>`;
}
