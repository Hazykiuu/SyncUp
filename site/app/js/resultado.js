// Resultado da Dupla em abas. O HTML vem pronto do núcleo (textos externos já escapados lá).
import { html, useEffect, useRef, useState } from 'preact-htm';
import { baixar, executar } from './motor.js';

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

function Lista({ titulo, itens }) {
  return html`<div class="conexao vidro"><h3>${titulo}</h3>${itens.length ? html`<p>${itens.join(' · ')}</p>` : html`<p class="nota">Nenhum neste recorte.</p>`}</div>`;
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

const ABAS = ['Resumo', 'Em sintonia', 'Rankings', 'Gráficos', 'Compartilhar', 'Detalhes técnicos'];

export function Resultado({ r }) {
  const [aba, setAba] = useState(0);
  const botoes = useRef([]);
  const teclar = (e) => {
    const passo = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
    if (passo) { const n = (aba + passo + ABAS.length) % ABAS.length; setAba(n); botoes.current[n]?.focus(); e.preventDefault(); }
  };
  const [a, b] = r.nomes;
  const g = r.graficos, t = r.tabelas, h = r.html;
  const paineis = [
    () => html`<${Html} conteudo=${h.resumo} /><div class="grade-2">${h.perfis.map((p) => html`<${Html} conteudo=${p} />`)}</div><${Html} conteudo=${h.corrida} />`,
    () => html`<${Html} conteudo=${h.sintonia} />
      <p class="nota">Quase juntos (até 1 h de distância): <b>${r.quase.artistas.toLocaleString('pt-BR')}</b> pares com o mesmo artista e <b>${r.quase.musicas.toLocaleString('pt-BR')}</b> com a mesma música.</p>
      <details class="vidro detalhe"><summary>Exemplos de quase juntos</summary><${Tabela} titulo="Mesmo artista" tabela=${t.quase_artistas} /><${Tabela} titulo="Mesma música" tabela=${t.quase_musicas} /></details>`,
    () => html`<div class="grade-2">${h.listas.map((l) => html`<${Html} conteudo=${l} />`)}</div>
      <div class="grade-3"><${Lista} titulo="Artistas em comum" itens=${r.conexoes.comuns} /><${Lista} titulo=${`Só ${a}`} itens=${r.conexoes.so_a} /><${Lista} titulo=${`Só ${b}`} itens=${r.conexoes.so_b} /></div>
      ${r.ponte.length > 0 && html`<div class="vidro conexao"><h3>Ponte musical</h3><p class="nota">Sugestões de artistas ausentes no recorte do outro. Não são descobertas comprovadas.</p>
        <ul class="ponte">${r.ponte.map((p) => html`<li>${p.de} → ${p.para}: <a href=${p.link} target="_blank" rel="noopener">${p.artista}</a> · ${p.plays.toLocaleString('pt-BR')} plays</li>`)}</ul></div>`}`,
    () => html`<div class="graficos">
      <${Grafico} figura=${g.artistas} titulo="Artistas mais ouvidos, lado a lado" /><${Grafico} figura=${g.horarios} titulo="Quando cada um ouve" />
      <${Grafico} figura=${g.tracos} titulo="Traços de escuta" /><${Grafico} figura=${g.rankings} titulo="Rankings comparados" /><${Grafico} figura=${g.meses} titulo="Horas por mês" /></div>`,
    () => html`<${Compartilhar} />`,
    () => html`<p class="nota">${r.aviso}</p>
      <${Tabela} titulo="Contribuição de cada artista ao cosseno" tabela=${t.contribuicoes} /><${Tabela} titulo="Diversidade" tabela=${t.diversidade} />
      <${Tabela} titulo="Minutos por execução" tabela=${t.estatisticas} /><${Tabela} titulo="Diagnóstico dos arquivos" tabela=${t.diagnostico} /><${Tabela} titulo="Playlist comum" tabela=${t.playlist} />`,
  ];
  return html`
    <section class="resultado" aria-labelledby="titulo-resultado">
      <h2 id="titulo-resultado" class="sr-only">Resultado de ${a} e ${b}</h2>
      <p class="periodo">${r.periodo}</p>
      <div class="sub-abas" role="tablist" aria-label="Partes do resultado" onKeyDown=${teclar}>
        ${ABAS.map((rotulo, i) => html`<button ref=${(el) => (botoes.current[i] = el)} role="tab" id=${`aba-${i}`} aria-selected=${aba === i} aria-controls=${`painel-${i}`} tabindex=${aba === i ? 0 : -1} onClick=${() => setAba(i)}>${rotulo}</button>`)}
      </div>
      <div class="painel-aba" role="tabpanel" id=${`painel-${aba}`} aria-labelledby=${`aba-${aba}`} tabindex="0">${paineis[aba]()}</div>
    </section>`;
}
