// Tela da Batalha: de 3 a 6 pessoas, o Worker em duas fases e o placar (os stories entram por cima dele).
import { html, useEffect, useMemo, useRef, useState } from 'preact-htm';
import { CORES, janelaComum, validarNomes } from './batalha.js';
import { chegarPouco, rolarAte } from './chegada.js';
import { Pessoa } from './envio.js';
import { compartilhar, desenharPosterBatalha } from './poster.js';
import { Opcoes, PADRAO } from './opcoes.js';
import { destravarSom, SomStories } from './som.js';
import { slidesDaBatalha } from './stories/batalha.js';
import { fmtNum } from './stories/logica.js';
import { Player } from './stories/player.js';
import { abrirWorker } from './worker.js';
import { Dock } from './stories/dock.js';

const SEM_RESPOSTA = 'o SyncUp parou de responder, provavelmente por falta de memória. Recarregue a página e tente com menos pessoas.';
const DEMO = [['demo-wrapped.zip', 'Ana'], ['demo-bruno.zip', 'Bruno'], ['demo-carla.zip', 'Carla'], ['demo-davi.zip', 'Davi']];
const NOTA_SOM = 'Para o som, o SyncUp envia à Apple (iTunes) o nome do artista favorito de cada pessoa da batalha, além do seu endereço IP. Os históricos e os nomes de vocês não saem do aparelho. Trechos: iTunes.';
const AVISO = 'É uma brincadeira com os números do período: não mede gosto nem personalidade.';
const plural = (n, um, varios) => `${n} ${n === 1 ? um : varios}`;
const EXEMPLOS = ['Ana', 'Bia', 'Caio', 'Duda', 'Edu', 'Fabi'];
const inicial = (nome) => [...(nome.trim() || '?')][0].toUpperCase();
const porMedalhas = (b) => (i, j) => {
  const x = b.lutadores[i].medalhas, y = b.lutadores[j].medalhas;
  return y.ouro - x.ouro || y.prata - x.prata || y.bronze - x.bronze || i - j;
};
const mesmoPlacar = (x, y) => x.ouro === y.ouro && x.prata === y.prata && x.bronze === y.bronze;

// Medalhas desenhadas, com o texto para o leitor de tela. `escrito`: o texto também na tela (placar),
// para o tipo de medalha não depender só da cor.
const Medalhas = ({ m, escrito = false }) => html`<span class="medalhas"><span class=${escrito ? 'medalhas-texto' : 'sr-only'}>${textoMedalhas(m)}</span>
  ${['ouro', 'prata', 'bronze'].map((t) => m[t] > 0 && html`<span class=${`med ${t}`} aria-hidden="true"><i></i>${m[t]}</span>`)}</span>`;

// Os selos de disputa, na tipografia do Kicker dos stories (etiqueta em caixa alta, sem brilho).
const SELOS = { 'por-um-triz': 'Por um triz', massacre: 'Massacre' };

// Pódio: 2º, 1º, 3º da esquerda para a direita; quem empata no placar sobe à mesma altura.
// É o fim da tela: anima só quando aparece (classe em-cena, uma vez).
function Podio({ b, nomes, ordem }) {
  const raiz = useRef(null);
  useEffect(() => {
    const el = raiz.current;
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) { el.classList.add('em-cena'); obs.disconnect(); } }, { threshold: 0.35 });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  const top = ordem.slice(0, 3);
  const pos = top.map((i, k) => 1 + top.slice(0, k).filter((j) => !mesmoPlacar(b.lutadores[j].medalhas, b.lutadores[i].medalhas)).length);
  const lugares = [1, 0, 2].filter((k) => k < top.length);
  return html`<ol ref=${raiz} class="podio" aria-label="Pódio">${lugares.map((k) => {
    const i = top[k], l = b.lutadores[i];
    return html`<li class=${`degrau p${pos[k]}`} style=${{ '--lut': l.cor, '--k': 2 - k }}>
      <span class="avatar lut" aria-hidden="true">${inicial(nomes[i])}</span>
      <b class="podio-nome">${nomes[i]}</b>${pos[k] === 1 && b.titulo && html`<small class="podio-titulo">${b.titulo}</small>`}<${Medalhas} m=${l.medalhas} />
      <span class="bloco"><span class="lugar">${pos[k]}º</span></span></li>`;
  })}</ol>`;
}

// Um cartão por rodada: vencedor em destaque e uma barra por pessoa (piso de 4 px quando o valor é maior que 0).
function Rodadas({ b, nomes }) {
  return html`<ul class="rodadas">${b.rodadas.map((r, n) => {
    const maior = Math.max(...r.valores) || 1;
    const venc = r.posicoes.map((p, i) => (p === 1 ? i : -1)).filter((i) => i >= 0);
    return html`<li class="rodada vidro" style=${{ '--i': Math.min(n, 8) }}>
      <h3>${r.titulo}${r.destaque && html` <span class="selo">${SELOS[r.destaque]}</span>`}</h3>
      <p class="rodada-vence"><span class="lut-ponto" style=${{ '--lut': b.lutadores[venc[0]].cor }} aria-hidden="true"></span>${venc.map((i) => nomes[i]).join(' e ')}
        <b>${fmtNum(r.valores[venc[0]], r.casas)}</b> <small>${r.unidade}${r.menor ? ' (menos vence)' : ''}</small></p>
      <ul class="barras" aria-label=${`${r.titulo}: todos`}>${r.valores.map((v, i) => html`
        <li style=${{ '--lut': b.lutadores[i].cor, '--j': i }}><span class="barra-nome">${nomes[i]}</span>
          <span class="trilho"><i class=${r.posicoes[i] === 1 ? 'lider' : ''} style=${{ width: v > 0 ? `max(4px, ${(v / maior) * 100}%)` : '0' }}></i></span>
          <span class="barra-valor">${fmtNum(v, r.casas)}</span></li>`)}</ul>
      ${r.alerta && html`<p class="selo-rodape"><span class="selo">Dedinho nervoso</span> ${r.alerta.nome} pulou ${fmtNum(r.alerta.valor, 1)}% das músicas</p>`}</li>`;
  })}</ul>`;
}
const textoMedalhas = (m) => [m.ouro && plural(m.ouro, 'ouro', 'ouros'), m.prata && plural(m.prata, 'prata', 'pratas'), m.bronze && plural(m.bronze, 'bronze', 'bronzes')].filter(Boolean).join(', ') || 'sem medalha';

// Um Worker por batalha. Os File vão em cada fase (o Worker nunca relê o que guardou da anterior).
async function batalharNoWorker(w, arquivos, nomes, opcoes) {
  const janela = opcoes.comum ? janelaComum((await w.pedir({ fase: 1, arquivos, opcoes })).faixas) : null;
  return (await w.pedir({ fase: 2, arquivos, nomes, opcoes, janela })).dados;
}

function Placar({ b, nomes }) {
  const ordem = b.lutadores.map((l, i) => i).sort(porMedalhas(b));
  return html`
    <div class="tabela-rolagem" role="region" aria-label="Placar da batalha" tabindex="0">
      <table class="placar"><caption class="sr-only">Placar</caption>
        <thead><tr><th scope="col">Pessoa</th><th scope="col">Medalhas</th>
          ${b.rodadas.map((r) => html`<th scope="col">${r.titulo} <small>${r.unidade}</small></th>`)}</tr></thead>
        <tbody>${ordem.map((i) => html`<tr>
          <th scope="row"><span class="lut-ponto" style=${{ '--lut': b.lutadores[i].cor }} aria-hidden="true"></span>${nomes[i]}</th>
          <td><${Medalhas} m=${b.lutadores[i].medalhas} escrito /></td>
          ${b.rodadas.map((r) => html`<td class=${r.posicoes[i] === 1 ? 'venceu' : ''}>${fmtNum(r.valores[i], r.casas)}${r.posicoes[i] === 1 ? html` <small>1º</small>` : ''}</td>`)}
        </tr>`)}</tbody>
      </table>
    </div>`;
}

const segundos = (ms) => (ms / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 1 });
function ResultadoBatalha({ b, nomes, comum }) {
  const stories = useRef(null);
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState('');
  const poster = async () => {
    setOcupado(true); setAviso('');
    try {
      const inicio = performance.now();
      const blob = await desenharPosterBatalha(b);
      const ms = performance.now() - inicio;
      const como = await compartilhar(blob, 'syncup-batalha.png', 'Batalha no SyncUp');
      setAviso(como === 'cancelado' ? '' : `Pôster pronto em ${segundos(ms)} s${como === 'baixado' ? ' (baixado como syncup-batalha.png)' : ''}.`);
    } catch (e) { setAviso(`Não deu certo: ${e.message}`); } finally { setOcupado(false); }
  };
  const slides = useMemo(() => slidesDaBatalha(b), [b]);
  return html`
    <section class="resultado batalha-res" aria-labelledby="titulo-batalha">
      <h2 id="titulo-batalha" class="sr-only">Resultado da batalha</h2>
      <div ref=${stories} class="nucleo"><${Player} key=${b} slides=${slides} rotulo=${`Batalha de ${nomes.join(', ')}`} /></div>
      <div class="compartilhar"><div class="acoes">
        <button type="button" class="btn btn-borda vidro" onClick=${() => stories.current?.querySelector('.st-player')?.dispatchEvent(new Event('st-replay'))}>↺ Ver de novo</button>
      </div>${aviso && html`<p ref=${chegarPouco} class="nota" role="status">${aviso}</p>`}
      <${Dock} alvo=${stories} aoPoster=${poster} ocupado=${ocupado} comSom=${!!b.trilha} /></div>
      ${b.trilha && html`<${SomStories} key=${b} trilha=${b.trilha} alvo=${stories} nota=${NOTA_SOM} />`}
      <p class="batalha-resumo">${b.resenha}</p>
      <${Rodadas} b=${b} nomes=${nomes} />
      <${Podio} b=${b} nomes=${nomes} ordem=${b.lutadores.map((l, i) => i).sort(porMedalhas(b))} />
      <details class="vidro detalhe"><summary>Ver todos os números</summary><${Placar} b=${b} nomes=${nomes} /></details>
      ${b.fora.length > 0 && html`<p class="nota">Ficaram de fora: ${b.fora.map((f) => `${f.titulo} (${f.motivo})`).join('; ')}.</p>`}
      ${!comum && html`<p class="nota">Históricos inteiros: quem tem mais tempo de histórico leva vantagem.</p>`}
      <p class="nota">${AVISO}</p>
    </section>`;
}

export function Batalha() {
  const [nomes, setNomes] = useState(['', '', '']);
  const [arquivos, setArquivos] = useState([[], [], []]);
  const [opcoes, setOpcoes] = useState(PADRAO);
  const [fase, setFase] = useState({ tipo: 'parado' });
  const ocupado = fase.tipo === 'processando';
  const pode = !ocupado && arquivos.every((a) => a.length > 0);
  const ultima = useRef(null); // "batalhar" ou "demo", para o "Tentar de novo"
  const worker = useRef(null);
  const rodada = useRef(0); // resposta de uma batalha já cancelada é ignorada

  const cancelar = () => { worker.current?.cancelar(); worker.current = null; rodada.current++; };
  // Saiu do modo Batalha (ou da página) no meio da leitura: nada fica lendo em segundo plano.
  useEffect(() => {
    const sair = () => {
      if (location.hash === '#batalha' || !worker.current) return;
      cancelar();
      setFase({ tipo: 'erro', mensagem: 'A batalha parou quando você trocou de modo. É só começar de novo.' });
    };
    addEventListener('hashchange', sair);
    return () => { removeEventListener('hashchange', sair); cancelar(); };
  }, []);

  const rodar = async (ler, nomesUsados) => {
    cancelar();
    const minha = rodada.current;
    setFase({ tipo: 'processando', etapa: 'Preparando a batalha…' });
    try {
      const lista = await ler();
      if (minha !== rodada.current) return;
      const w = (worker.current = abrirWorker('batalha-worker.js', { semResposta: SEM_RESPOSTA, aoProgresso: (etapa) => minha === rodada.current && setFase({ tipo: 'processando', etapa }) }));
      const b = await batalharNoWorker(w, lista, nomesUsados, opcoes);
      if (minha !== rodada.current) return;
      cancelar();
      setFase({ tipo: 'resultado', b, nomes: nomesUsados, comum: opcoes.comum });
      requestAnimationFrame(() => rolarAte(document.getElementById('resultado-batalha')));
    } catch (e) {
      if (e.name === 'AbortError' || minha !== rodada.current) return; // cancelada: nada a mostrar
      cancelar();
      setFase({ tipo: 'erro', mensagem: e.message });
    }
  };
  const batalhar = () => {
    ultima.current = 'batalhar';
    destravarSom();
    let finais;
    try { finais = validarNomes(nomes); } catch (e) { setFase({ tipo: 'erro', mensagem: e.message }); return; }
    rodar(async () => arquivos, finais);
  };
  // Quatro históricos fictícios prontos (gerados por tools/empacotar_web.py): nenhum dado real.
  const demo = () => {
    ultima.current = 'demo';
    destravarSom();
    setNomes(DEMO.map(([, n]) => n)); setArquivos(DEMO.map(() => []));
    rodar(() => Promise.all(DEMO.map(async ([arquivo]) => {
      const resposta = await fetch(arquivo).catch(() => null);
      if (!resposta?.ok) throw new Error('Não deu para baixar os históricos fictícios. Confira a internet e tente de novo.');
      return [new File([await resposta.blob()], arquivo)];
    })), DEMO.map(([, n]) => n));
  };
  const mudar = (lista, i, v) => lista.map((x, j) => (j === i ? v : x));
  const adicionar = () => { setNomes((n) => [...n, '']); setArquivos((a) => [...a, []]); };
  const tirar = (i) => { setNomes((n) => n.filter((_, j) => j !== i)); setArquivos((a) => a.filter((_, j) => j !== i)); };

  return html`
    <div class="arena vidro" aria-label=${`Na batalha: ${nomes.length} de 6 pessoas`}>
      <ol class="arena-lista">${nomes.map((nome, i) => html`${i > 0 && html`<li class="vs" aria-hidden="true">vs</li>`}
        <li style=${{ '--lut': CORES[i] }}><span class="avatar lut" aria-hidden="true">${nome.trim() ? inicial(nome) : i + 1}</span><span class="sr-only">${nome.trim() || `Pessoa ${i + 1}`}</span></li>`)}</ol>
      <small>${nomes.length} de 6</small>
    </div>
    <div class="pessoas">
      ${nomes.map((nome, i) => html`
        <div class="lutador" style=${{ '--lut': CORES[i] }}>
          <${Pessoa} rotulo=${String(i + 1)} cor="lut" exemplo=${EXEMPLOS[i]} nome=${nome} aoMudarNome=${(v) => setNomes((n) => mudar(n, i, v))}
            arquivos=${arquivos[i]} aoMudarArquivos=${(v) => setArquivos((a) => mudar(a, i, v))} desabilitado=${ocupado}
            extra=${i >= 3 && html`<button type="button" class="tirar tirar-lutador" aria-label=${`Tirar a pessoa ${i + 1}`} onClick=${() => tirar(i)} disabled=${ocupado}>×</button>`} />
        </div>`)}
    </div>
    ${nomes.length < 6 && html`<button type="button" class="btn btn-borda vidro mais-lutador" onClick=${adicionar} disabled=${ocupado}>+ Adicionar pessoa</button>`}
    <${Opcoes} valor=${opcoes} aoMudar=${setOpcoes} desabilitado=${ocupado} comPonderacao=${false} />
    <div class="barra-acao">
      <button type="button" class="btn btn-verde" onClick=${batalhar} disabled=${!pode} aria-describedby="dica-batalhar">
        ${ocupado ? 'Batalhando…' : 'Começar a batalha'}<span class="seta" aria-hidden="true">→</span></button>
      <button type="button" class="btn btn-borda vidro" onClick=${demo} disabled=${ocupado}>Testar com dados fictícios</button>
      <small id="dica-batalhar">${pode || ocupado || fase.tipo === 'resultado' ? '' : 'Envie pelo menos um arquivo para cada pessoa.'}</small>
    </div>
    <div aria-live="polite">
      ${fase.tipo === 'processando' && html`<p ref=${chegarPouco} class="processando vidro"><span class="giro" aria-hidden="true"></span>${fase.etapa}</p>`}
      ${fase.tipo === 'erro' && html`<div ref=${chegarPouco} class="erro vidro" role="alert"><p><b>Não deu certo.</b> ${fase.mensagem}</p>
        ${ultima.current && html`<button type="button" class="btn btn-borda vidro" onClick=${ultima.current === 'demo' ? demo : batalhar}>Tentar de novo</button>`}</div>`}
      ${fase.tipo === 'resultado' && html`<p class="sr-only">Resultado da batalha pronto, logo abaixo.</p>`}
    </div>
    <div id="resultado-batalha">${fase.tipo === 'resultado' && html`<${ResultadoBatalha} b=${fase.b} nomes=${fase.nomes} comum=${fase.comum} />`}</div>`;
}
