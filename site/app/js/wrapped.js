// Tela Wrapped: o histórico de uma pessoa vira stories da vida toda e um PNG.
import { html, useMemo, useRef, useState } from 'preact-htm';
import { criarBuscador } from './capas.js';
import { compartilhar, desenharPoster } from './poster.js';
import { executar } from './motor.js';
import { Pessoa } from './envio.js';
import { Opcoes, PADRAO } from './opcoes.js';
import { SomStories } from './som.js';
import { Player } from './stories/player.js';
import { CapasCtx, chaveCapa, NOVOS } from './stories/slides.js';
import { tiposDoWrapped } from './stories/logica.js';

const Html = ({ conteudo }) => html`<div class="nucleo" dangerouslySetInnerHTML=${{ __html: conteudo }} />`;

// Slides a partir de `dados` (JSON da ponte), com as mesmas regras de quais entram do núcleo.
function montarSlides(r, capas) {
  return tiposDoWrapped(r.dados, { capas }).map((tipo) => {
    const Slide = NOVOS[tipo];
    return { tipo, render: (p) => html`<${Slide} d=${r.dados} ...${p} />` };
  });
}

// O que buscar, na ordem dos slides (o primeiro fica pronto antes). Sem repetir.
function pedidos(d) {
  const faixa = (m) => m?.uri && { item: m, tipo: 'faixa' };
  const artista = (a) => a?.nome && { item: a, tipo: 'artista' };
  const topo = d.anos.length ? d.anos.reduce((a, b) => (b.horas > a.horas ? b : a)) : null;
  const lista = [
    faixa(d.top_musicas[0]), faixa(d.primeira_musica), artista(d.artista_vida),
    ...d.top_artistas.slice(0, 5).map(artista), ...d.top_musicas.slice(0, 9).map(faixa),
    faixa(topo?.top_musica), artista(d.anos.at(-1)?.top_artistas[0]), faixa(d.repeticao_dia), artista(d.fiel),
  ].filter(Boolean);
  return [...new Map(lista.map((p) => [chaveCapa(p.item, p.tipo), p])).values()];
}

// Criado só no opt-in: antes disso nem o IndexedDB é aberto.
let buscador = null;

export function Wrapped({ pronto }) {
  const [nome, setNome] = useState('');
  const [arquivos, setArquivos] = useState([]);
  const [opcoes, setOpcoes] = useState(PADRAO);
  const [fase, setFase] = useState({ tipo: 'parado' });
  const [baixando, setBaixando] = useState(false);
  const [aviso, setAviso] = useState('');
  const [capas, setCapas] = useState(null); // null = desligadas; Map chave → { url, link }
  const stories = useRef(null);
  const rodada = useRef(0); // resultados de uma rodada antiga não entram na nova
  const ocupado = fase.tipo === 'processando';
  const slides = useMemo(() => (fase.tipo === 'resultado' ? montarSlides(fase.r, capas !== null) : []), [fase, capas !== null]);

  // Uma capa por vez, conforme chega. Artista sem foto: capa da música mais ouvida dele no top.
  const ligarCapas = (d) => {
    if (capas !== null) return; // já ligadas (ex.: tentar o som de novo)
    const minha = rodada.current;
    buscador ??= criarBuscador();
    setCapas(new Map());
    for (const { item, tipo } of pedidos(d)) {
      (async () => {
        let capa = await (tipo === 'faixa' ? buscador.faixa(item.uri) : buscador.artista(item.nome));
        const dele = tipo === 'artista' && !capa && d.top_musicas.find((m) => m.artista === item.nome && m.uri);
        if (dele) capa = await buscador.faixa(dele.uri);
        if (capa && minha === rodada.current) setCapas((m) => new Map(m).set(chaveCapa(item, tipo), capa));
      })();
    }
  };

  const rodar = async (args, envio = []) => {
    setFase({ tipo: 'processando', etapa: 'Lendo o histórico completo e montando os stories…' });
    try {
      const r = await executar('wrapped', args, { arquivos: envio });
      rodada.current++;
      setCapas(null);
      setFase({ tipo: 'resultado', r });
      requestAnimationFrame(() => document.getElementById('resultado-wrapped')?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
    } catch (e) { setFase({ tipo: 'erro', mensagem: e.message }); }
  };
  const montar = () => {
    const envio = arquivos.map((arquivo, i) => ({ caminho: `/tmp/w-${i}-${arquivo.name.replace(/[^\w.-]/g, '_')}`, arquivo }));
    rodar([envio.map((e) => e.caminho), nome || 'Você', opcoes], envio);
  };
  const demo = async () => {
    setFase({ tipo: 'processando', etapa: 'Gerando um histórico fictício no seu aparelho…' });
    try {
      const d = await executar('arquivos_demo');
      setNome(d.nome_a); setArquivos([]);
      await rodar([[d.a], d.nome_a, opcoes]);
    } catch (e) { setFase({ tipo: 'erro', mensagem: e.message }); }
  };
  // Capas guardadas no navegador (só endereços): apaga tudo na hora.
  const apagarCapas = async () => {
    buscador ??= criarBuscador();
    await buscador.apagarTudo();
    setAviso('Capas guardadas apagadas deste navegador.');
  };

  // Pôster em PNG desenhado no navegador (Canvas): compartilha no celular, baixa no computador.
  const png = async () => {
    setBaixando(true); setAviso('');
    try {
      const inicio = performance.now();
      const blob = await desenharPoster(fase.r.dados, capas);
      const ms = Math.round(performance.now() - inicio);
      const como = await compartilhar(blob);
      setAviso(como === 'cancelado' ? '' : `Pôster pronto em ${(ms / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} s${como === 'baixado' ? ' (baixado como syncup-wrapped.png)' : ''}.`);
    } catch (e) { setAviso(`Não deu para gerar o pôster: ${e.message}`); } finally { setBaixando(false); }
  };

  return html`
    <div class="pessoas uma">
      <${Pessoa} rotulo="♪" titulo="Seu histórico" cor="verde" nome=${nome} aoMudarNome=${setNome} arquivos=${arquivos} aoMudarArquivos=${setArquivos} desabilitado=${ocupado} />
    </div>
    <${Opcoes} valor=${opcoes} aoMudar=${setOpcoes} desabilitado=${ocupado} comPeriodo=${false} />
    <div class="barra-acao">
      <button type="button" class="btn btn-verde" onClick=${montar} disabled=${!pronto || ocupado || !arquivos.length}>
        ${ocupado ? 'Montando…' : 'Montar meu Wrapped'}<span class="seta" aria-hidden="true">→</span></button>
      <button type="button" class="btn btn-borda vidro" onClick=${demo} disabled=${!pronto || ocupado}>Testar com dados fictícios</button>
    </div>
    <div aria-live="polite">
      ${ocupado && html`<p class="processando vidro"><span class="giro" aria-hidden="true"></span>${fase.etapa}</p>`}
      ${fase.tipo === 'erro' && html`<p class="erro vidro" role="alert"><b>Não deu certo.</b> ${fase.mensagem}</p>`}
    </div>
    <div id="resultado-wrapped">${fase.tipo === 'resultado' && html`
      <section class="resultado" aria-label=${`Wrapped de ${fase.r.nome}`}>
        <${SomStories} key=${fase.r} trilha=${fase.r.trilha} alvo=${stories} aoLigar=${() => ligarCapas(fase.r.dados)} />
        <div ref=${stories} class="nucleo">
          <${CapasCtx.Provider} value=${capas}>
            <${Player} key=${`${rodada.current}-${capas !== null}`} slides=${slides} rotulo=${`Wrapped de ${fase.r.nome}`} />
          <//>
          ${fase.r.dados.avisos.map((a) => html`<p class="su-note">${a}</p>`)}
        </div>
        <div class="compartilhar"><div class="acoes">
          <button type="button" class="btn btn-verde" onClick=${png} disabled=${baixando}>${baixando ? 'Gerando…' : 'Compartilhar pôster'}</button>
          <button type="button" class="btn btn-borda vidro" onClick=${() => stories.current?.querySelector('.st-player')?.dispatchEvent(new Event('st-replay'))}>↺ Ver de novo</button>
          <button type="button" class="btn btn-borda vidro" onClick=${apagarCapas}>Apagar capas guardadas</button>
        </div>
        ${aviso && html`<p class="nota" role="status">${aviso}</p>`}
        <p class="nota">Dica: no último story, tire um print para postar nos stories e chamar os amigos para comparar.</p></div>
        <details class="vidro detalhe"><summary>Como o arquétipo foi calculado</summary><${Html} conteudo=${fase.r.arquetipos} /></details>
      </section>`}</div>`;
}
