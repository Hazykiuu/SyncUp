// Os 5 gráficos da Dupla no formato de figura do Plotly, iguais aos de graficos.py (o Python).
// O plotly.js segue carregando só quando a aba Gráficos abre; aqui só se montam os dados.
// Paridade da estrutura inteira em tests/test_paridade_dupla.py.
import { fmtNum, ROXO, VERDE } from './dupla.js';
import { TEMA } from './tema-plotly.js';

const FUNDO = '#181818', GRADE = '#2a2a2a', TEXTO = '#ffffff', SECUNDARIO = '#b3b3b3', VERDE_ESCURO = '#14833b';
const FONTE = 'Figtree, "Circular Std", "Helvetica Neue", Helvetica, Arial, sans-serif';
const CORES_GRUPO = [VERDE, ROXO, '#ffa42b', '#4cc9f0', '#f573a0', '#e8db5a'];
const DIAS_SEMANA = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'];
const LIMIARES = [60, 40, 40]; // perfis.LIMIAR_FAVORITOS, LIMIAR_REPEAT e LIMIAR_MADRUGADA, em %

// Escapa só & < >: o Plotly lê tags, mas mostra &quot; e &#x27; ao pé da letra (graficos._texto).
const texto = (t) => String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

// graficos._base: tema, fontes, separadores pt-BR, margens e transição comuns.
function base(titulo, altura, eixos = [['xaxis', 'yaxis']]) {
  const layout = {
    title: { font: { size: 20, color: TEXTO }, text: `<b>${titulo}</b>`, x: 0.01, xanchor: 'left', y: 0.98, yanchor: 'top' },
    font: { family: FONTE, size: 15, color: TEXTO },
    margin: { l: 45, r: 35, t: 110, b: 60 },
    legend: { font: { color: SECUNDARIO }, orientation: 'h', yanchor: 'bottom', y: 1.01, x: 0, bgcolor: 'rgba(0,0,0,0)' },
    hoverlabel: { font: { size: 15, family: FONTE, color: TEXTO }, bgcolor: '#282828', bordercolor: VERDE },
    transition: { duration: 650, easing: 'cubic-in-out' },
    height: altura,
    paper_bgcolor: FUNDO,
    plot_bgcolor: FUNDO,
    separators: ',.',
    template: TEMA,
  };
  for (const [x, y] of eixos) {
    layout[x] = { gridcolor: GRADE, zerolinecolor: SECUNDARIO, linecolor: GRADE };
    layout[y] = { gridcolor: GRADE, linecolor: GRADE };
  }
  return layout;
}

const participacao = (b, plays, artista) => ((b.contagens.get(artista) || 0) / plays) * 100;

function butterfly(r) {
  const artistas = r.ordem, nomes = artistas.map(texto);
  const [a, b] = r.perfis;
  const valores = [0, 1].map((k) => artistas.map((x) => participacao(r._bruto[k], r.perfis[k].plays, x)));
  const data = [[a, valores[0], -1, VERDE, 'A'], [b, valores[1], 1, ROXO, 'B']].map(([p, v, sinal, cor, prefixo]) => ({
    customdata: v,
    hovertemplate: '%{y}<br>%{customdata:.2f}% dos plays<extra>%{fullData.name}</extra>',
    marker: { color: cor, cornerradius: 6, line: { width: 0 } },
    name: texto(`${prefixo} · ${p.nome}`),
    orientation: 'h',
    x: v.map((x) => sinal * x),
    y: nomes,
    type: 'bar',
  }));
  const limite = Math.max(...valores[0], ...valores[1], 1) * 1.1;
  const ticks = [-limite, -limite / 2, 0, limite / 2, limite];
  const layout = base('Artistas: participação na escuta', Math.max(500, artistas.length * 40 + 180));
  Object.assign(layout.xaxis, {
    title: { font: { color: SECUNDARIO }, text: 'Participação nos plays de cada perfil (%)' },
    range: [-limite, limite],
    tickvals: ticks,
    ticktext: ticks.map((x) => `${fmtNum(Math.abs(x), 1)}%`),
  });
  Object.assign(layout.yaxis, { autorange: 'reversed', title: {}, showgrid: false });
  return { data, layout: { ...layout, barmode: 'relative', bargap: 0.3 } };
}

function mapaHorarios(r) {
  const matrizes = r._bruto.map((b, k) => b.diaHora.map((linha) => linha.map((n) => (n / r.perfis[k].plays) * 100)));
  const data = matrizes.map((z, k) => ({
    coloraxis: 'coloraxis',
    hovertemplate: '%{y}, %{x}h<br>%{z:.2f}% dos plays<extra></extra>',
    x: Array.from({ length: 24 }, (_, h) => h),
    xgap: 2,
    y: DIAS_SEMANA,
    ygap: 2,
    z,
    type: 'heatmap',
    xaxis: k ? 'x2' : 'x',
    yaxis: k ? 'y2' : 'y',
  }));
  const layout = base(`Horários de escuta · ${texto(r.fuso)}`, 540, [['xaxis', 'yaxis'], ['xaxis2', 'yaxis2']]);
  const titulo = { title: { text: 'Hora local' }, tickvals: [0, 4, 8, 12, 16, 20, 23], showgrid: false };
  Object.assign(layout.xaxis, { anchor: 'y', domain: [0, 0.44], ...titulo });
  Object.assign(layout.xaxis2, { anchor: 'y2', domain: [0.56, 1], ...titulo });
  Object.assign(layout.yaxis, { anchor: 'x', domain: [0, 1], autorange: 'reversed', showgrid: false });
  Object.assign(layout.yaxis2, { anchor: 'x2', domain: [0, 1], autorange: 'reversed', showgrid: false });
  const todos = matrizes.flat(2);
  layout.annotations = r.perfis.map((p, k) => ({
    font: { size: 15, color: SECUNDARIO }, showarrow: false, text: texto(`${k ? 'B' : 'A'} · ${p.nome}`),
    x: k ? 0.78 : 0.22, xanchor: 'center', xref: 'paper', y: 1, yanchor: 'bottom', yref: 'paper',
  }));
  layout.coloraxis = {
    colorbar: { title: { text: '% dos plays' }, outlinewidth: 0, thickness: 14 },
    colorscale: [[0, '#202020'], [0.35, '#1a5c33'], [0.7, VERDE_ESCURO], [1, VERDE]],
    // Escala comum aos dois mapas, do menor ao maior valor observado.
    cmin: Math.min(...todos),
    cmax: Math.max(...todos) || 1,
  };
  return { data, layout };
}

// As três proporções dos arquétipos (perfis.classificar_proporcoes), em %.
function tracos(p, b) {
  const soma = (lista, n) => [...lista].sort((x, y) => y - x).slice(0, n).reduce((s, x) => s + x, 0);
  const madrugada = b.porHora.slice(0, 6).reduce((s, x) => s + x, 0); // 00h a 05h59
  return [soma(b.contagens.values(), 2) / p.plays, soma(b.faixas.values(), 10) / p.plays, madrugada / p.plays];
}

function radarTracos(r) {
  const categorias = ['Top 2 artistas', 'Top 10 faixas', 'Madrugada (00–05h59)'];
  const theta = [...categorias, categorias[0]];
  const data = r.perfis.map((p, k) => {
    const v = tracos(p, r._bruto[k]).map((x) => x * 100);
    return {
      fill: 'toself',
      fillcolor: k ? 'rgba(196,183,255,0.25)' : 'rgba(30,215,96,0.25)',
      hovertemplate: '%{theta}: %{r:.1f}%<extra>%{fullData.name}</extra>',
      line: { color: k ? ROXO : VERDE, width: 3 },
      marker: { size: 9 },
      mode: 'lines+markers',
      name: texto(`${k ? 'B' : 'A'} · ${p.nome}`),
      r: [...v, v[0]],
      theta,
      type: 'scatterpolar',
    };
  });
  data.push({ line: { color: TEXTO, dash: 'dash', width: 2 }, mode: 'lines+markers', name: 'Limiares de classificação', r: [...LIMIARES, LIMIARES[0]], theta, type: 'scatterpolar' });
  const layout = base('Traços de escuta · regras experimentais', 580);
  return {
    data,
    layout: {
      ...layout,
      margin: { l: 90, r: 90, t: 90, b: 90 },
      legend: { ...layout.legend, orientation: 'h', yanchor: 'top', y: -0.06, x: 0.5, xanchor: 'center' },
      polar: {
        radialaxis: { tickfont: { size: 13, color: SECUNDARIO }, range: [0, 100], ticksuffix: '%', gridcolor: '#3a3a3a', linecolor: '#3a3a3a' },
        angularaxis: { tickfont: { size: 15 }, gridcolor: '#3a3a3a', linecolor: '#3a3a3a' },
        bgcolor: FUNDO,
      },
    },
  };
}

function slopeChart(r, limite = 8) {
  const artistas = r.ordem.slice(0, limite);
  const data = artistas.map((artista, i) => ({
    hovertemplate: '%{y:.2f}% dos plays<extra>%{fullData.name}</extra>',
    line: { color: CORES_GRUPO[i % CORES_GRUPO.length], width: 3 },
    marker: { size: 12, symbol: i < 6 ? 'circle' : 'diamond' },
    mode: 'lines+markers',
    name: texto(artista),
    x: [0, 1],
    y: [0, 1].map((k) => participacao(r._bruto[k], r.perfis[k].plays, artista)),
    type: 'scatter',
  }));
  const n = artistas.length;
  const layout = base(`Diferenças de participação · ${n} artista${n !== 1 ? 's' : ''} líder${n !== 1 ? 'es' : ''}`, 600);
  Object.assign(layout.xaxis, { tickvals: [0, 1], ticktext: r.perfis.map((p, k) => texto(`${k ? 'B' : 'A'} · ${p.nome}`)), range: [-0.15, 1.15], showgrid: false, zeroline: false });
  Object.assign(layout.yaxis, { title: { text: 'Participação nos plays (%)' }, ticksuffix: '%' });
  return {
    data,
    layout: { ...layout, legend: { ...layout.legend, orientation: 'v', x: 1.02, y: 0.9, yanchor: 'top' }, margin: { l: 70, r: 190, t: 90, b: 85 } },
  };
}

function evolucaoMensal(r) {
  const data = r.perfis.map((p, k) => {
    const meses = [...r._bruto[k].horasMes].sort(([x], [y]) => x - y);
    return {
      fill: 'tozeroy',
      fillcolor: k ? 'rgba(196,183,255,0.12)' : 'rgba(30,215,96,0.12)',
      hovertemplate: '%{x}: %{y:.1f} h<extra>%{fullData.name}</extra>',
      line: { color: k ? ROXO : VERDE, shape: 'spline', smoothing: 0.6, width: 3 },
      marker: { size: 6 },
      mode: 'lines+markers',
      name: texto(`${k ? 'B' : 'A'} · ${p.nome}`),
      x: meses.map(([m]) => `${Math.floor(m / 100)}-${String(m % 100).padStart(2, '0')}`),
      y: meses.map(([, minutos]) => minutos / 60),
      type: 'scatter',
    };
  });
  const layout = base('Horas ouvidas por mês', 430);
  Object.assign(layout.xaxis, { nticks: 12, showgrid: false });
  Object.assign(layout.yaxis, { title: { text: 'Horas' }, rangemode: 'tozero' });
  return { data, layout: { ...layout, hovermode: 'x unified' } };
}

/** Os 5 gráficos da resposta (`graficos` de ponte.comparar_dupla), a partir de compararDupla. */
export function graficosDupla(r) {
  return { artistas: butterfly(r), horarios: mapaHorarios(r), tracos: radarTracos(r), rankings: slopeChart(r), meses: evolucaoMensal(r) };
}
