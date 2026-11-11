// Resultado da Dupla: os stories no topo (dados de `r.dupla`) e os detalhes em abas embaixo.
// Nas abas, o HTML ainda vem pronto do núcleo (textos externos já escapados lá).
import { html, useEffect, useMemo, useRef, useState } from 'preact-htm';
import { baixar, executar } from './motor.js';
import { SLIDES_DUPLA } from './stories/dupla.js';
import { tiposDaDupla } from './stories/logica.js';
import { Player } from './stories/player.js';

const Html = ({ conteudo, classe = '' }) => html`<div class=${`nucleo ${classe}`} dangerouslySetInnerHTML=${{ __html: conteudo }} />`;

function Tabela({ titulo, tabela }) {
  if (!tabela || !tabela.linhas.length) return null;
  return html`
    <div class="tabela-rolagem vidro" role="region" aria-label=${titulo} tabindex="0">
      <table><caption>${titulo}</caption>
        <thead><tr>${tabela.colunas.map((c) => html`<th scope="col">${c}</th>`)}</tr></thead>
        <tbody>${tabela.linhas.map((l) => html`<tr>${l.map((v) => html`<td>${v}</td>`)}</tr>`)}</tbody>
      </table>
    </div>`;
}

// plotly.js só baixa quando a aba Gráficos abre (~5 MB).
let plotly = null;
const carregarPlotly = () => plotly ??= new Promise((ok, erro) => {
  const s = Object.assign(document.createElement('script'), { src: 'https://cdn.jsdelivr.net/npm/plotly.js-dist-min@3.7.0/plotly.min.js', onload: () => ok(window.Plotly), onerror: () => { s.remove(); plotly = null; erro(); } });
  document.head.append(s);
});

function Grafico({ figura, titulo }) {
  const alvo = useRef(null);
  const [falhou, setFalhou] = useState(false);
  useEffect(() => {
    let vivo = true;
    carregarPlotly().then((P) => vivo && P.newPlot(alvo.current, figura.data, { ...figura.layout, autosize: true }, { responsive: true, displaylogo: false }))
      .catch(() => vivo && setFalhou(true));
    return () => { vivo = false; window.Plotly?.purge(alvo.current); };
  }, [figura]);
  return html`<figure class="grafico vidro"><figcaption>${titulo}</figcaption>
    ${falhou && html`<p class="erro" role="alert">Não deu para baixar os gráficos. Confira a internet e abra esta aba de novo.</p>`}
    <div ref=${alvo} class="grafico-area" role="img" aria-label=${titulo}></div></figure>`;
}

// Nomes como etiquetas: as 12 primeiras à vista, o resto atrás de "ver mais".
const VISIVEIS = 12;
function Lista({ titulo, itens }) {
  const etiquetas = (nomes) => html`<ul class="dp-etiquetas">${nomes.map((n) => html`<li>${n}</li>`)}</ul>`;
  return html`<div class="conexao vidro"><h3>${titulo}</h3>
    ${itens.length ? etiquetas(itens.slice(0, VISIVEIS)) : html`<p class="nota">Nenhum neste período.</p>`}
    ${itens.length > VISIVEIS && html`<details class="dp-mais"><summary>Ver mais ${itens.length - VISIVEIS}</summary>${etiquetas(itens.slice(VISIVEIS))}</details>`}
  </div>`;
}

// Rankings: no celular, uma pessoa por vez (eram 4 listas empilhadas); no computador, lado a lado.
function Rankings({ nomes, listas }) {
  const [quem, setQuem] = useState(0);
  return html`<div class="dp-ranks" data-quem=${quem}>
    <div class="dp-alternador" role="group" aria-label="De quem são os rankings">
      ${nomes.map((n, i) => html`<button type="button" class=${i ? 'b' : 'a'} aria-pressed=${quem === i} onClick=${() => setQuem(i)}>${n}</button>`)}
    </div>
    <div class="grade-2">${listas.map((l, i) => html`<${Html} conteudo=${l} classe=${`dp-lado-${i % 2}`} />`)}</div>
  </div>`;
}

// As 4 medidas da comparação, cada uma com o que mede em uma frase (o jargão fica aqui, não nos stories).
const MEDIDAS = [
  ['cosseno', 'Escuta em comum', 'Cosseno', 'Compara quanto cada um ouviu de cada artista. É o número da abertura dos stories.'],
  ['jaccard', 'Artistas em comum', 'Jaccard', 'De todos os artistas que aparecem nos dois históricos, quantos os dois ouviram.'],
  ['jaccard_top20', 'Favoritos em comum', 'Jaccard do top 20', 'A mesma conta, só com os 20 artistas mais ouvidos de cada um.'],
  ['ruzicka', 'Plays em comum', 'Ruzicka', 'Como o de artistas em comum, mas pesando pela quantidade de plays.'],
];
function Medidas({ metricas }) {
  return html`<dl class="dp-medidas">${MEDIDAS.map(([chave, titulo, tecnico, frase]) => html`
    <div class="vidro"><dt>${titulo} <small>${tecnico}</small></dt>
      <dd><b>${(metricas[chave] * 100).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%</b><span>${frase}</span></dd></div>`)}</dl>`;
}

function Compartilhar() {
  const [ocupado, setOcupado] = useState('');
  const [erro, setErro] = useState('');
  const gerar = async (acao, rotulo) => {
    setOcupado(rotulo); setErro('');
    try { baixar(await executar(acao, [], { saida: 'arquivo' })); } catch (e) { setErro(e.message); } finally { setOcupado(''); }
  };
  const botao = (acao, rotulo) => html`<button type="button" class="btn btn-borda vidro" disabled=${!!ocupado} onClick=${() => gerar(acao, rotulo)}>${ocupado === rotulo ? 'Gerando…' : rotulo}</button>`;
  return html`
    <div class="compartilhar">
      <p>Tudo é gerado aqui no seu aparelho.</p>
      <div class="acoes">${botao('cartao_dupla', 'Cartão da dupla · PNG')}${botao('cartao_sintonia', 'Story da sintonia · PNG')}${botao('playlist_dupla', 'Playlist comum · CSV')}</div>
      ${erro && html`<p class="erro" role="alert">${erro}</p>`}
    </div>`;
}

const ABAS = ['Rankings', 'Gráficos', 'Compartilhar', 'Detalhes técnicos'];

export function Resultado({ r }) {
  const [aba, setAba] = useState(0);
  const botoes = useRef([]);
  // A barra não mostra rolagem: a aba escolhida vem para a vista sozinha (sem mexer na página).
  const primeira = useRef(true);
  useEffect(() => {
    if (primeira.current) { primeira.current = false; return; }
    botoes.current[aba]?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  }, [aba]);
  const teclar = (e) => {
    const passo = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
    if (passo) { const n = (aba + passo + ABAS.length) % ABAS.length; setAba(n); botoes.current[n]?.focus(); e.preventDefault(); }
  };
  const [a, b] = r.nomes;
  const g = r.graficos, t = r.tabelas, h = r.html;
  const stories = useRef(null);
  const slides = useMemo(() => tiposDaDupla(r.dupla).map((tipo) => {
    const Slide = SLIDES_DUPLA[tipo];
    return { tipo, render: (p) => html`<${Slide} d=${r.dupla} ...${p} />` };
  }), [r]);
  const paineis = [
    () => html`<${Rankings} nomes=${r.nomes} listas=${h.listas} />
      <div class="grade-3"><${Lista} titulo="Artistas em comum" itens=${r.conexoes.comuns} /><${Lista} titulo=${`Só ${a}`} itens=${r.conexoes.so_a} /><${Lista} titulo=${`Só ${b}`} itens=${r.conexoes.so_b} /></div>
      ${r.ponte.length > 0 && html`<div class="vidro conexao"><h3>Ponte musical</h3><p class="nota">Sugestões de artistas ausentes no recorte do outro. Não são descobertas comprovadas.</p>
        <ul class="ponte">${r.ponte.map((p) => html`<li>${p.de} → ${p.para}: <a href=${p.link} target="_blank" rel="noopener">${p.artista}</a> · ${p.plays.toLocaleString('pt-BR')} plays</li>`)}</ul></div>`}`,
    () => html`<div class="graficos">
      <${Grafico} figura=${g.artistas} titulo="Artistas mais ouvidos, lado a lado" /><${Grafico} figura=${g.horarios} titulo="Quando cada um ouve" />
      <${Grafico} figura=${g.tracos} titulo="Traços de escuta" /><${Grafico} figura=${g.rankings} titulo="Rankings comparados" /><${Grafico} figura=${g.meses} titulo="Horas por mês" /></div>
      <${Html} conteudo=${h.corrida} />`,
    () => html`<${Compartilhar} />`,
    () => html`<${Medidas} metricas=${r.metricas} />
      <p class="nota">${r.aviso}</p>
      <p class="nota">Quase juntos (até 1 h de distância): <b>${r.quase.artistas.toLocaleString('pt-BR')}</b> pares com o mesmo artista e <b>${r.quase.musicas.toLocaleString('pt-BR')}</b> com a mesma música.</p>
      <details class="vidro detalhe"><summary>Exemplos de quase juntos</summary><${Tabela} titulo="Mesmo artista" tabela=${t.quase_artistas} /><${Tabela} titulo="Mesma música" tabela=${t.quase_musicas} /></details>
      <${Tabela} titulo="Contribuição de cada artista ao cosseno" tabela=${t.contribuicoes} /><${Tabela} titulo="Diversidade" tabela=${t.diversidade} />
      <${Tabela} titulo="Minutos por execução" tabela=${t.estatisticas} /><${Tabela} titulo="Diagnóstico dos arquivos" tabela=${t.diagnostico} /><${Tabela} titulo="Playlist comum" tabela=${t.playlist} />
      <p class="nota">As tabelas mostram as 20 primeiras linhas. A playlist inteira está em Compartilhar, no CSV.</p>`,
  ];
  return html`
    <section class="resultado" aria-labelledby="titulo-resultado">
      <h2 id="titulo-resultado" class="sr-only">Resultado de ${a} e ${b}</h2>
      <p class="periodo">${r.periodo}</p>
      <div ref=${stories} class="nucleo">
        <${Player} key=${r} slides=${slides} rotulo=${`Dupla de ${a} e ${b}`} />
      </div>
      <div class="compartilhar"><div class="acoes">
        <button type="button" class="btn btn-borda vidro" onClick=${() => stories.current?.querySelector('.st-player')?.dispatchEvent(new Event('st-replay'))}>↺ Ver de novo</button>
      </div></div>
      <div class="sub-abas" role="tablist" aria-label="Partes do resultado" onKeyDown=${teclar}>
        ${ABAS.map((rotulo, i) => html`<button ref=${(el) => (botoes.current[i] = el)} role="tab" id=${`aba-${i}`} aria-selected=${aba === i} aria-controls=${`painel-${i}`} tabindex=${aba === i ? 0 : -1} onClick=${() => setAba(i)}>${rotulo}</button>`)}
      </div>
      <div class="painel-aba" role="tabpanel" id=${`painel-${aba}`} aria-labelledby=${`aba-${aba}`} tabindex="0">${paineis[aba]()}</div>
    </section>`;
}
