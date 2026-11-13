// Tela Wrapped: o histórico de uma pessoa vira stories da vida toda e um PNG.
// O cálculo roda em JavaScript num Worker próprio (wrapped-worker.js): esta aba não baixa o Python.
import { html, useMemo, useRef, useState } from 'preact-htm';
import { AVISO_ARQUETIPOS, formatarValor, REGRAS } from './calculo.js';
import { criarBuscador } from './capas.js';
import { chegar, chegarPouco } from './chegada.js';
import { compartilhar, desenharPoster } from './poster.js';
import { Pessoa } from './envio.js';
import { Opcoes, PADRAO } from './opcoes.js';
import { SomStories, destravarSom } from './som.js';
import { Player } from './stories/player.js';
import { CapasCtx, chaveCapa, NOVOS } from './stories/slides.js';
import { tiposDoWrapped } from './stories/logica.js';

const DEMO = 'Ana (fictícia)'; // demo-wrapped.zip: o mesmo histórico fictício da demo da Dupla
const SEM_RESPOSTA = 'o SyncUp parou de responder, provavelmente por falta de memória. Recarregue a página e tente com menos arquivos.';
const segundos = (ms) => (ms / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 1 });

// Um Worker por montagem: ao terminar, o navegador devolve toda a memória (importa no celular).
function montarNoWorker(arquivos, nome, opcoes) {
  return new Promise((ok, erro) => {
    const w = new Worker('wrapped-worker.js', { type: 'module' });
    w.onmessage = ({ data }) => { w.terminate(); data.ok ? ok(data.dados) : erro(new Error(data.erro)); };
    w.onerror = (e) => { e.preventDefault?.(); w.terminate(); erro(new Error(SEM_RESPOSTA)); };
    w.postMessage({ arquivos, nome, opcoes }, arquivos.map((a) => a.bytes));
  });
}

// Todas as regras avaliadas, com o valor da pessoa e o limiar (o mesmo de stories.arquetipos_detalhe_html).
function ArquetiposDetalhe({ arquetipos }) {
  const regras = new Map(REGRAS.map((r) => [r.chave, r]));
  return html`<div class="nucleo"><div class="su-arch-detail"><h3>Todos os arquétipos avaliados</h3>
    <p class="su-note">A barra é o seu valor; o traço branco é o limiar da regra. Em verde, as regras atingidas.</p>
    <ol>${arquetipos.avaliados.map((a, i) => {
      const r = regras.get(a.chave), escala = Math.max(r.teto, a.valor) || 1;
      return html`<li class=${a.forca >= 1 ? 'on' : ''} style=${`--i:${i}`}><span class="su-ad-ic">${a.icone}</span>
        <span class="su-ad-name"><b>${a.nome}</b><small>${a.explicacao}</small></span>
        <span class="su-ad-bar"><i style=${`--value:${(Math.min(a.valor / escala, 1) * 100).toFixed(1)}%`}></i><u style=${`left:${((r.limiar / escala) * 100).toFixed(1)}%`} title="limiar"></u></span>
        <em>${formatarValor(a.valor, r.formato)}<small>limiar ${formatarValor(r.limiar, r.formato)}</small></em></li>`;
    })}</ol>
    <p class="su-note">${AVISO_ARQUETIPOS}</p></div></div>`;
}

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

export function Wrapped() {
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

  // `ler` devolve [{ nome, bytes: ArrayBuffer }]; o tempo inclui ler os arquivos (é o que a pessoa espera).
  const ultima = useRef(null); // a última tentativa, para o "Tentar de novo" do erro
  const rodar = async (ler, nomeUsado) => {
    ultima.current = () => rodar(ler, nomeUsado);
    setFase({ tipo: 'processando', etapa: 'Lendo o histórico completo e montando os stories…' });
    try {
      const inicio = performance.now();
      const r = await montarNoWorker(await ler(), nomeUsado, opcoes);
      rodada.current++;
      setCapas(null);
      setFase({ tipo: 'resultado', r, ms: performance.now() - inicio });
      requestAnimationFrame(() => document.getElementById('resultado-wrapped')?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
    } catch (e) { setFase({ tipo: 'erro', mensagem: e.message }); }
  };
  const montar = () => { destravarSom(); return rodar(() => Promise.all(arquivos.map(async (f) => ({ nome: f.name, bytes: await f.arrayBuffer() }))), nome || 'Você'); };
  const demo = () => {
    destravarSom();
    setNome(DEMO); setArquivos([]);
    rodar(async () => {
      const resposta = await fetch('demo-wrapped.zip').catch(() => null);
      if (!resposta?.ok) throw new Error('Não deu para baixar o histórico fictício. Confira a internet e tente de novo.');
      return [{ nome: 'demo-wrapped.zip', bytes: await resposta.arrayBuffer() }];
    }, DEMO);
  };
  // Capas guardadas no navegador (só endereços): apaga tudo na hora.
  const apagarCapas = async () => {
    // Ação que não tem volta: confirma antes (a busca refaz as capas, mas leva tempo e usa a rede).
    if (!confirm('Apagar as capas e fotos guardadas neste navegador? Na próxima vez elas serão buscadas de novo.')) return;
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
      setAviso(como === 'cancelado' ? '' : `Pôster pronto em ${segundos(ms)} s${como === 'baixado' ? ' (baixado como syncup-wrapped.png)' : ''}.`);
    } catch (e) { setAviso(`Não deu para gerar o pôster: ${e.message}`); } finally { setBaixando(false); }
  };

  return html`
    <div class="pessoas uma">
      <${Pessoa} rotulo="♪" titulo="Seu histórico" cor="verde" nome=${nome} aoMudarNome=${setNome} arquivos=${arquivos} aoMudarArquivos=${setArquivos} desabilitado=${ocupado} />
    </div>
    <${Opcoes} valor=${opcoes} aoMudar=${setOpcoes} desabilitado=${ocupado} comPeriodo=${false} />
    <div class="barra-acao">
      <button type="button" class="btn btn-verde" onClick=${montar} disabled=${ocupado || !arquivos.length}>
        ${ocupado ? 'Montando…' : 'Montar meu Wrapped'}<span class="seta" aria-hidden="true">→</span></button>
      <button type="button" class="btn btn-borda vidro" onClick=${demo} disabled=${ocupado}>Testar com dados fictícios</button>
    </div>
    <div aria-live="polite">
      ${ocupado && html`<p ref=${chegarPouco} class="processando vidro"><span class="giro" aria-hidden="true"></span>${fase.etapa}</p>`}
      ${fase.tipo === 'erro' && html`<div ref=${chegarPouco} class="erro vidro" role="alert"><p><b>Não deu certo.</b> ${fase.mensagem}</p>
        ${ultima.current && html`<button type="button" class="btn btn-borda vidro" onClick=${() => ultima.current()}>Tentar de novo</button>`}</div>`}
      ${fase.tipo === 'resultado' && html`<p class="sr-only">Wrapped de ${fase.r.nome} pronto, logo abaixo.</p>`}
    </div>
    <div id="resultado-wrapped">${fase.tipo === 'resultado' && html`
      <section ref=${chegar} class="resultado" aria-label=${`Wrapped de ${fase.r.nome}`}>
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
        ${aviso && html`<p ref=${chegarPouco} class="nota" role="status">${aviso}</p>`}
        <p class="nota">Montado em ${segundos(fase.ms)} s, no seu aparelho.</p>
        <p class="nota">Dica: no último story, tire um print para postar nos stories e chamar os amigos para comparar.</p></div>
        <details class="vidro detalhe"><summary>Como o arquétipo foi calculado</summary><${ArquetiposDetalhe} arquetipos=${fase.r.dados.arquetipos} /></details>
      </section>`}</div>`;
}
