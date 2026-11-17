// Tela do Match: ZIPs e convites colados, o Worker e os pares que mais combinam (com os motivos).
import { html, useEffect, useMemo, useRef, useState } from 'preact-htm';
import { CORES } from './batalha.js';
import { chegarPouco, rolarAte } from './chegada.js';
import { Pessoa } from './envio.js';
import { Opcoes, PADRAO } from './opcoes.js';
import { duetos, melhorPar, trilhaMatch } from './match.js';
import { compartilhar, desenharPosterMatch } from './poster.js';
import { destravarSom, SomStories } from './som.js';
import { Dock } from './stories/dock.js';
import { Palco } from './stories/palco.js';
import { Faixas, Nomes, slidesDoMatch } from './stories/match.js';
import { Player } from './stories/player.js';
import { fmtNum } from './stories/logica.js';
import { abrirWorker } from './worker.js';

const SEM_RESPOSTA = 'o SyncUp parou de responder, provavelmente por falta de memória. Recarregue a página e tente com menos pessoas.';
const DEMO = [['demo-wrapped.zip', 'Ana'], ['demo-bruno.zip', 'Bruno'], ['demo-carla.zip', 'Carla'], ['demo-davi.zip', 'Davi']];
const NOTA_SOM = 'Para o som, o SyncUp envia à Apple (iTunes) os nomes dos artistas em comum de cada par, além do seu endereço IP. Os históricos e os nomes de vocês não saem do aparelho. Trechos: iTunes.';
const segundos = (ms) => (ms / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 1 });
const AVISO = 'O Match compara só os rankings de artistas e músicas. Não mede afinidade pessoal.';
const EXEMPLOS = ['Ana', 'Bia', 'Caio', 'Duda', 'Edu', 'Fabi'];
const cor = (i) => CORES[i % CORES.length];
const pct = (v) => `${fmtNum(v, 1)}%`;

// Um dueto por grupo (dupla ou trio): linha editorial com os nomes, a nota de cada par, as faixas, o refrão e o Lado B.
const LIMITE_TELA = 5; // sem "+N": as listas já chegam cortadas em 8 pelo cálculo
const lista = (l) => l.slice(0, LIMITE_TELA).join(' · ');

function Dueto({ d, cor }) {
  const trio = d.nomes.length === 3;
  return html`<li class="dueto">
    <${Nomes} nomes=${d.nomes} cor=${cor} />
    ${d.linhas.map((l) => html`<div class="dueto-par">
      ${trio && html`<p class="dueto-subpar">${l.x} × ${l.y}</p>`}
      <p class="dueto-nota"><b>${pct(l.pontuacao)}</b><span>${l.nivel}</span></p>
      <p class="dueto-frase">${l.descricao}</p>
      <${Faixas} l=${l} cor=${cor} />
    </div>`)}
    <dl class="dueto-texto">
      <dt>Refrão em comum${trio ? ' aos três' : ''}</dt>
      <dd>${d.refrao.length ? lista(d.refrao) : 'Nenhum artista em comum nos rankings.'}${!trio && d.linhas[0].musicas_comuns > 0 ? html` <small>(e ${d.linhas[0].musicas_comuns === 1 ? 'uma música favorita' : `${d.linhas[0].musicas_comuns} músicas favoritas`} em comum)</small>` : ''}</dd>
      ${d.ladoB.map((p) => html`<dt>Lado B de ${p.para}</dt>
        ${p.origens.map((o) => html`<dd>${trio && html`<span class="dueto-de">de ${o.de}: </span>`}${o.artistas.length ? lista(o.artistas) : 'Nada de novo para indicar: vocês já ouvem os mesmos artistas.'}</dd>`)}`)}
    </dl>
  </li>`;
}

function ResultadoMatch({ dados: { r, fontes, fora } }) {
  const cores = Object.fromEntries(r.nomes.map((n, i) => [n, cor(i)]));
  const stories = useRef(null);
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState('');
  const slides = useMemo(() => slidesDoMatch(r), [r]);
  const trilha = useMemo(() => trilhaMatch(r), [r]);
  const poster = async () => {
    setOcupado(true); setAviso('');
    try {
      const inicio = performance.now();
      const blob = await desenharPosterMatch(r, ...melhorPar(r), cores);
      const ms = performance.now() - inicio;
      const como = await compartilhar(blob, 'syncup-match.png', 'Match no SyncUp');
      setAviso(como === 'cancelado' ? '' : `Pôster pronto em ${segundos(ms)} s${como === 'baixado' ? ' (baixado como syncup-match.png)' : ''}.`);
    } catch (e) { setAviso(`Não deu certo: ${e.message}`); } finally { setOcupado(false); }
  };
  return html`<section class="resultado" aria-labelledby="titulo-match">
    <h2 id="titulo-match" class="dueto-titulo">Os duetos do grupo</h2>
    <${Palco} alvo=${stories} slides=${slides} comSom=${trilha.fila.length > 0} lado=${html`
    <div class="compartilhar"><div class="acoes">
      <button type="button" class="btn btn-verde" onClick=${poster} disabled=${ocupado}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4v11" /><path d="m7 10 5 5 5-5" /><path d="M5 20h14" /></svg>${ocupado ? 'Gerando…' : 'Baixar pôster'}</button>
      <button type="button" class="btn btn-borda vidro" onClick=${() => stories.current?.querySelector('.st-player')?.dispatchEvent(new Event('st-replay'))}>↺ Ver de novo</button>
    </div>${aviso && html`<p ref=${chegarPouco} class="nota" role="status">${aviso}</p>`}
    <${Dock} alvo=${stories} aoPoster=${poster} ocupado=${ocupado} comSom=${!!trilha.fila.length} /></div>
    ${trilha.fila.length > 0 && html`<${SomStories} key=${r} trilha=${trilha} alvo=${stories} nota=${NOTA_SOM} />`}`}>
      <${Player} key=${r} slides=${slides} rotulo=${`Match de ${r.nomes.join(', ')}`} />
    <//>
    <p class="batalha-resumo">Média dos pares: <b>${pct(r.pontuacao_media_pares)}</b>. Os pares somam a maior compatibilidade possível do grupo${r.nomes.length % 2 ? '; com número ímpar, uma pessoa entra no par onde mais combina e vira trio' : ''}.</p>
    <ul class="duetos">${duetos(r).map((d) => html`<${Dueto} d=${d} cor=${(n) => cores[n]} />`)}</ul>
    <details class="vidro detalhe"><summary>Com quem cada um mais combina</summary>
      <div class="tabela-rolagem" role="region" aria-label="Com quem cada um mais combina" tabindex="0">
        <table class="placar"><thead><tr><th scope="col">Pessoa</th><th scope="col">Fonte</th><th scope="col">1º match</th><th scope="col">2º match</th></tr></thead>
          <tbody>${r.nomes.map((n) => html`<tr><th scope="row"><span class="lut-ponto" style=${{ '--lut': cores[n] }} aria-hidden="true"></span>${n}</th>
            <td>${fontes[n]}</td>${[0, 1].map((k) => html`<td>${r.melhores[n][k] ? `${r.melhores[n][k][0]} (${pct(r.melhores[n][k][1])})` : '—'}</td>`)}</tr>`)}</tbody></table></div></details>
    ${fora.length > 0 && html`<p class="nota">Ficaram de fora: ${fora.join(' · ')}</p>`}
    <p class="nota">${AVISO}</p>
  </section>`;
}

// Gera o código para mandar a um amigo: ZIP + nome → "SYNCUP1.…". Só os rankings viajam.
function MeuConvite({ opcoes, rodar, ocupado }) {
  const [nome, setNome] = useState('');
  const [arquivos, setArquivos] = useState([]);
  const [codigo, setCodigo] = useState('');
  const [aviso, setAviso] = useState('');
  const gerar = async () => {
    setAviso(''); setCodigo('');
    try { setCodigo(await rodar({ tipo: 'convite', arquivos, nome: nome.trim() || 'Eu', opcoes })); } catch (e) { if (e.name !== 'AbortError') setAviso(`Não deu certo: ${e.message}`); }
  };
  const copiar = async () => {
    try { await navigator.clipboard.writeText(codigo); setAviso('Código copiado. Mande para quem vai fazer o Match.'); } catch { setAviso('Não deu para copiar sozinho: selecione o código e copie.'); }
  };
  return html`<details class="vidro detalhe match-convite"><summary>Gerar o meu convite</summary>
    <p class="nota">Quem não está com você manda um código em vez do ZIP. O código leva só os rankings (top artistas e músicas): o histórico, os horários e o resto ficam no seu aparelho.</p>
    <${Pessoa} rotulo="Eu" titulo="Seu histórico" cor="lut" exemplo="Seu nome" nome=${nome} aoMudarNome=${setNome} arquivos=${arquivos} aoMudarArquivos=${setArquivos} desabilitado=${ocupado} />
    <button type="button" class="btn btn-borda vidro" onClick=${gerar} disabled=${ocupado || !arquivos.length}>Gerar o código</button>
    ${codigo && html`<label class="match-codigo"><span>Seu convite</span><textarea readonly rows="3" onFocus=${(e) => e.target.select()}>${codigo}</textarea></label>
      <button type="button" class="btn btn-verde" onClick=${copiar}>Copiar o código</button>`}
    ${aviso && html`<p class="nota" role="status">${aviso}</p>`}
  </details>`;
}

export function Match() {
  const [nomes, setNomes] = useState(['', '']);
  const [arquivos, setArquivos] = useState([[], []]);
  const [convites, setConvites] = useState('');
  const [opcoes, setOpcoes] = useState(PADRAO);
  const [fase, setFase] = useState({ tipo: 'parado' });
  const ocupado = fase.tipo === 'processando';
  const comArquivo = arquivos.filter((a) => a.length).length;
  const pode = !ocupado && (comArquivo + (convites.trim() ? 1 : 0)) >= 2 && arquivos.every((a, i) => a.length || !nomes[i].trim());
  const worker = useRef(null);
  const rodada = useRef(0);
  const ultima = useRef(null);

  const cancelar = () => { worker.current?.cancelar(); worker.current = null; rodada.current++; };
  useEffect(() => {
    const sair = () => {
      if (location.hash === '#match' || !worker.current) return;
      cancelar();
      setFase({ tipo: 'erro', mensagem: 'O Match parou quando você trocou de modo. É só começar de novo.' });
    };
    addEventListener('hashchange', sair);
    return () => { removeEventListener('hashchange', sair); cancelar(); };
  }, []);

  // Uma requisição num Worker só dela (o navegador devolve a memória ao fechar).
  const pedir = async (mensagem, aoEtapa) => {
    cancelar();
    const minha = rodada.current;
    const w = (worker.current = abrirWorker('match-worker.js', { semResposta: SEM_RESPOSTA, aoProgresso: (etapa) => minha === rodada.current && aoEtapa?.(etapa) }));
    try { return (await w.pedir(mensagem)).dados; } finally { if (worker.current === w) { w.cancelar(); worker.current = null; } }
  };

  const rodar = async (ler, nomesUsados, textoConvites) => {
    setFase({ tipo: 'processando', etapa: 'Preparando o Match…' });
    const minha = rodada.current + 1;
    try {
      const lista = await ler();
      const dados = await pedir({ tipo: 'match', arquivos: lista, nomes: nomesUsados, convites: textoConvites, opcoes }, (etapa) => setFase({ tipo: 'processando', etapa }));
      setFase({ tipo: 'resultado', dados });
      requestAnimationFrame(() => rolarAte(document.getElementById('resultado-match')));
    } catch (e) {
      if (e.name === 'AbortError' || minha !== rodada.current) return;
      setFase({ tipo: 'erro', mensagem: e.message });
    }
  };
  const combinar = () => {
    ultima.current = 'combinar';
    destravarSom();
    const usados = arquivos.map((a, i) => [a, (nomes[i] || '').trim() || `Pessoa ${i + 1}`]).filter(([a]) => a.length);
    rodar(async () => usados.map(([a]) => a), usados.map(([, n]) => n), convites);
  };
  const demo = () => {
    ultima.current = 'demo';
    destravarSom();
    setNomes(DEMO.map(([, n]) => n)); setArquivos(DEMO.map(() => [])); setConvites('');
    rodar(() => Promise.all(DEMO.map(async ([arquivo]) => {
      const resposta = await fetch(arquivo).catch(() => null);
      if (!resposta?.ok) throw new Error('Não deu para baixar os históricos fictícios. Confira a internet e tente de novo.');
      return [new File([await resposta.blob()], arquivo)];
    })), DEMO.map(([, n]) => n), '');
  };
  const mudar = (lista, i, v) => lista.map((x, j) => (j === i ? v : x));
  const adicionar = () => { setNomes((n) => [...n, '']); setArquivos((a) => [...a, []]); };
  const tirar = (i) => { setNomes((n) => n.filter((_, j) => j !== i)); setArquivos((a) => a.filter((_, j) => j !== i)); };

  return html`<div class="match-area">
    <div class="pessoas">
      ${nomes.map((nome, i) => html`
        <div class="lutador" style=${{ '--lut': cor(i) }}>
          <${Pessoa} modo="match-" rotulo=${String(i + 1)} cor="lut" exemplo=${EXEMPLOS[i % EXEMPLOS.length]} nome=${nome} aoMudarNome=${(v) => setNomes((n) => mudar(n, i, v))}
            arquivos=${arquivos[i]} aoMudarArquivos=${(v) => setArquivos((a) => mudar(a, i, v))} desabilitado=${ocupado}
            extra=${i >= 1 && html`<button type="button" class="tirar tirar-lutador" aria-label=${`Tirar a pessoa ${i + 1}`} onClick=${() => tirar(i)} disabled=${ocupado}>×</button>`} />
        </div>`)}
    </div>
    ${nomes.length < 16 && html`<button type="button" class="btn btn-borda vidro mais-lutador" onClick=${adicionar} disabled=${ocupado}>+ Adicionar pessoa</button>`}
    <label class="vidro match-colar"><span><b>Convites recebidos</b> <small>(opcional) Cole os códigos que começam com SYNCUP1., um por linha.</small></span>
      <textarea rows="3" value=${convites} onInput=${(e) => setConvites(e.target.value)} disabled=${ocupado} spellcheck="false" autocomplete="off"></textarea></label>
    <${MeuConvite} opcoes=${opcoes} rodar=${(m) => pedir(m)} ocupado=${ocupado} />
    <${Opcoes} valor=${opcoes} aoMudar=${setOpcoes} desabilitado=${ocupado} comPonderacao=${false} />
    <div class="barra-acao">
      <button type="button" class="btn btn-verde" onClick=${combinar} disabled=${!pode} aria-describedby="dica-match">
        ${ocupado ? 'Combinando…' : 'Ver quem combina'}<span class="seta" aria-hidden="true">→</span></button>
      <button type="button" class="btn btn-borda vidro" onClick=${demo} disabled=${ocupado}>Testar com dados fictícios</button>
      <small id="dica-match">${pode || ocupado || fase.tipo === 'resultado' ? '' : 'Junte pelo menos duas pessoas, com ZIP ou convite. Quem tem nome precisa de arquivo.'}</small>
    </div>
    <div aria-live="polite">
      ${fase.tipo === 'processando' && html`<p ref=${chegarPouco} class="processando vidro"><span class="giro" aria-hidden="true"></span>${fase.etapa}</p>`}
      ${fase.tipo === 'erro' && html`<div ref=${chegarPouco} class="erro vidro" role="alert"><p><b>Não deu certo.</b> ${fase.mensagem}</p>
        ${ultima.current && html`<button type="button" class="btn btn-borda vidro" onClick=${ultima.current === 'demo' ? demo : combinar}>Tentar de novo</button>`}</div>`}
      ${fase.tipo === 'resultado' && html`<p class="sr-only">Resultado do Match pronto, logo abaixo.</p>`}
    </div>
    <div id="resultado-match">${fase.tipo === 'resultado' && html`<${ResultadoMatch} dados=${fase.dados} />`}</div></div>`;
}
