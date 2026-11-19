// Tela Wrapped: o histórico de uma pessoa vira stories da vida toda e um PNG.
// O cálculo roda em JavaScript num Worker próprio (wrapped-worker.js): esta aba não baixa o Python.
import { html, useMemo, useRef, useState } from 'preact-htm';
import { AVISO_ARQUETIPOS, formatarValor, REGRAS } from './calculo.js';
import { criarBuscador } from './capas.js';
import { chegar, chegarPouco, mostrarResultado } from './chegada.js';
import { avisoPoster, compartilhar, desenharPoster, segundos } from './poster.js';
import { Pessoa } from './envio.js';
import { armazemLastfm, chave as chaveLastfm } from './lastfm.js';
import { Opcoes, PADRAO } from './opcoes.js';
import { ICONE, SomStories, destravarSom, TRILHA_EXEMPLO } from './som.js';
import { MEDIR_FPS, Player } from './stories/player.js';
import { Dock } from './stories/dock.js';
import { Palco } from './stories/palco.js';
import { capaLocal, CapasCtx, chaveCapa, Icone, NOVOS } from './stories/slides.js';
import { tiposDoWrapped } from './stories/logica.js';
import { rodarNoWorker } from './worker.js';

const DEMO = 'Rafa'; // demo-wrapped.zip: o mesmo histórico de exemplo da Dupla

// Um Worker por montagem: ao terminar, o navegador devolve toda a memória (importa no celular).
const montarNoWorker = (arquivos, nome, opcoes) => rodarNoWorker('wrapped-worker.js', { arquivos, nome, opcoes }, arquivos.map((a) => a.bytes));

// Todas as regras avaliadas, com o valor da pessoa e o limiar (o mesmo de stories.arquetipos_detalhe_html).
function ArquetiposDetalhe({ arquetipos }) {
  const regras = new Map(REGRAS.map((r) => [r.chave, r]));
  return html`<div class="nucleo"><div class="su-arch-detail"><h3>Todos os arquétipos avaliados</h3>
    <p class="su-note">A barra é o seu valor; o traço branco é o limiar da regra. Em verde, as regras atingidas.</p>
    <ol>${arquetipos.avaliados.map((a, i) => {
      const r = regras.get(a.chave), escala = Math.max(r.teto, a.valor) || 1;
      return html`<li class=${a.forca >= 1 ? 'on' : ''} style=${`--i:${i}`}><span class="su-ad-ic"><${Icone} id=${a.chave} /></span>
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

// Last.fm: as músicas não têm o código do Spotify (o oEmbed precisa dele). As que têm capa do álbum no Last.fm
// ganham um código próprio "lastfm:artista|música", e a capa vem do mapa que o download montou.
const LASTFM = 'lastfm:';
function marcarCapasLastfm(d, capas) {
  const marcar = (m) => { const k = m && !m.uri && chaveLastfm(m.artista, m.nome); if (k && capas.has(k)) m.uri = LASTFM + k; };
  [d.primeira_musica, d.repeticao_dia, ...d.top_musicas, ...d.anos.map((a) => a.top_musica)].forEach(marcar);
}

// Criado quando os stories ligam capas e som: antes disso nem o IndexedDB é aberto.
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
  const ligarCapas = (d, exemplo) => {
    if (capas !== null) return; // já ligadas (ex.: tentar o som de novo)
    // Exemplo: capas locais, sem rede (os artistas são inventados; o MusicBrainz poderia achar outra pessoa).
    if (exemplo) { setCapas(new Map(pedidos(d).map(({ item, tipo }) => [chaveCapa(item, tipo), { url: capaLocal(item) }]))); return; }
    const minha = rodada.current;
    buscador ??= criarBuscador();
    setCapas(new Map());
    for (const { item, tipo } of pedidos(d)) {
      (async () => {
        const daFaixa = (uri) => (uri.startsWith(LASTFM) ? { url: d.capasLastfm?.get(uri.slice(LASTFM.length)) } : buscador.faixa(uri));
        let capa = await (tipo === 'faixa' ? daFaixa(item.uri) : buscador.artista(item.nome));
        const dele = tipo === 'artista' && !capa && d.top_musicas.find((m) => m.artista === item.nome && m.uri);
        if (dele) capa = await daFaixa(dele.uri);
        if (capa && minha === rodada.current) setCapas((m) => new Map(m).set(chaveCapa(item, tipo), capa));
      })();
    }
  };

  // `ler` devolve [{ nome, bytes: ArrayBuffer }]; o tempo inclui ler os arquivos (é o que a pessoa espera).
  // Qual foi a última tentativa ("montar" ou "demo"): o "Tentar de novo" chama a função desta renderização,
  // com os arquivos e opções que a tela mostra agora (não os da tentativa que falhou).
  const ultima = useRef(null);
  const rodar = async (ler, nomeUsado, exemplo = false) => {
    setFase({ tipo: 'processando', etapa: 'Lendo o histórico completo e montando os stories…' });
    try {
      const inicio = performance.now();
      const r = await montarNoWorker(await ler(), nomeUsado, opcoes);
      rodada.current++;
      setCapas(null);
      if (exemplo) r.trilha = TRILHA_EXEMPLO;
      else {
        const lastfm = arquivos.find((f) => f.lastfm)?.lastfm;
        r.dados.aproximado = !!lastfm; // Last.fm: minutos pela duração das músicas
        if (lastfm?.capas) { r.dados.capasLastfm = lastfm.capas; marcarCapasLastfm(r.dados, lastfm.capas); }
      }
      mostrarResultado(() => setFase({ tipo: 'resultado', r, ms: performance.now() - inicio, exemplo }), 'resultado-wrapped');
    } catch (e) { if (e.name !== 'AbortError') setFase({ tipo: 'erro', mensagem: e.message }); }
  };
  const montar = () => { ultima.current = 'montar'; destravarSom(); return rodar(() => Promise.all(arquivos.map(async (f) => ({ nome: f.name, bytes: await f.arrayBuffer() }))), nome || 'Você'); };
  const demo = () => {
    ultima.current = 'demo';
    destravarSom();
    setNome(DEMO); setArquivos([]);
    rodar(async () => {
      const resposta = await fetch('demo-wrapped.zip').catch(() => null);
      if (!resposta?.ok) throw new Error('Não deu para baixar o exemplo. Confira a internet e tente de novo.');
      return [{ nome: 'demo-wrapped.zip', bytes: await resposta.arrayBuffer() }];
    }, DEMO, true);
  };
  // Guardado no navegador: endereços das capas e as escutas baixadas do Last.fm. Apaga tudo na hora.
  const apagarCapas = async () => {
    // Ação que não tem volta: confirma antes (a busca refaz tudo, mas leva tempo e usa a rede).
    if (!confirm('Apagar as capas, as fotos e as escutas do Last.fm guardadas neste navegador? Na próxima vez elas serão buscadas de novo.')) return;
    buscador ??= criarBuscador();
    await Promise.all([buscador.apagarTudo(), armazemLastfm().apagarTudo()]);
    setAviso('Dados guardados apagados deste navegador.');
  };

  // Pôster em PNG desenhado no navegador (Canvas): compartilha no celular, baixa no computador.
  const png = async () => {
    setBaixando(true); setAviso('');
    try {
      const inicio = performance.now();
      const blob = await desenharPoster(fase.r.dados, capas);
      const ms = Math.round(performance.now() - inicio);
      const como = await compartilhar(blob);
      setAviso(avisoPoster(como, ms, 'syncup-wrapped.png'));
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
      <button type="button" class="btn btn-borda superficie" onClick=${demo} disabled=${ocupado}>Ver um exemplo</button>
    </div>
    <div aria-live="polite">
      ${ocupado && html`<p ref=${chegarPouco} class="processando superficie"><span class="giro" aria-hidden="true"></span>${fase.etapa}</p>`}
      ${fase.tipo === 'erro' && html`<div ref=${chegarPouco} class="erro superficie" role="alert"><p><b>Não deu certo.</b> ${fase.mensagem}</p>
        ${ultima.current && html`<button type="button" class="btn btn-borda superficie" onClick=${ultima.current === 'demo' ? demo : montar}>Tentar de novo</button>`}</div>`}
      ${fase.tipo === 'resultado' && html`<p class="sr-only">Wrapped de ${fase.r.nome} pronto, logo abaixo.</p>`}
    </div>
    <div id="resultado-wrapped">${fase.tipo === 'resultado' && html`
      <section ref=${chegar} class="resultado" aria-label=${`Wrapped de ${fase.r.nome}`}>
        <${Palco} alvo=${stories} slides=${slides} comSom lado=${html`
        <${SomStories} key=${fase.r} trilha=${fase.r.trilha} alvo=${stories} aoLigar=${() => ligarCapas(fase.r.dados, fase.exemplo)} />
        <div class="compartilhar"><div class="acoes">
          <button type="button" class="btn btn-verde" onClick=${png} disabled=${baixando}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4v11" /><path d="m7 10 5 5 5-5" /><path d="M5 20h14" /></svg>${baixando ? 'Gerando…' : 'Baixar pôster'}</button>
          <button type="button" class="btn btn-borda superficie" onClick=${() => stories.current?.querySelector('.st-player')?.dispatchEvent(new Event('st-replay'))}>${ICONE.repetir}Ver de novo</button>
          <button type="button" class="btn btn-borda superficie" onClick=${apagarCapas}>Apagar dados guardados</button>
        </div>
        ${aviso && html`<p ref=${chegarPouco} class="nota" role="status">${aviso}</p>`}
        ${MEDIR_FPS && html`<p class="nota">Montado em ${segundos(fase.ms)} s.</p>`}
        <${Dock} alvo=${stories} aoPoster=${png} ocupado=${baixando} comSom />
        <p class="nota">Dica: no último story, tire um print para postar nos stories e chamar os amigos para comparar.</p></div>`}>
          <${CapasCtx.Provider} value=${capas}>
            <${Player} key=${`${rodada.current}-${capas !== null}`} slides=${slides} rotulo=${`Wrapped de ${fase.r.nome}`} />
          <//>
          ${fase.r.dados.avisos.map((a) => html`<p class="su-note">${a}</p>`)}
        <//>
        <details class="superficie detalhe"><summary>Como o arquétipo foi calculado</summary><${ArquetiposDetalhe} arquetipos=${fase.r.dados.arquetipos} /></details>
      </section>`}</div>`;
}
