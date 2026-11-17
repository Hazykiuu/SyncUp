// Tela do Match: ZIPs e convites colados, o Worker e os pares que mais combinam (com os motivos).
import { html, useEffect, useMemo, useRef, useState } from 'preact-htm';
import { CORES } from './batalha.js';
import { chegarPouco, rolarAte } from './chegada.js';
import { Pessoa } from './envio.js';
import { Opcoes, PADRAO } from './opcoes.js';
import { chave, melhorPar, trilhaMatch } from './match.js';
import { compartilhar, desenharPosterMatch } from './poster.js';
import { destravarSom, SomStories } from './som.js';
import { Dock } from './stories/dock.js';
import { slidesDoMatch } from './stories/match.js';
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

// Um cartão por grupo (dupla ou trio), com cara de cartão de namoro: o casal, a nota em corações e o porquê.
const CORACAO = 'M12 21s-7.5-4.6-9.6-9.4C.9 8 3.1 4 6.9 4c2.2 0 3.7 1.2 5.1 3 1.4-1.8 2.9-3 5.1-3 3.8 0 6 4 4.5 7.6C19.5 16.4 12 21 12 21Z';
const Coracao = ({ cheio = true }) => html`<svg viewBox="0 0 24 24" class=${cheio ? 'cheio' : ''} aria-hidden="true"><path d=${CORACAO} /></svg>`;
const inicial = (n) => [...(n.trim() || '?')][0].toUpperCase();
// 25 pontos já é "Sintonia rara" (conciliacao.NIVEIS): cinco corações.
const coracoes = (p) => (p > 0 ? Math.max(1, Math.round(Math.min(1, p / 25) * 5)) : 0);

function Bilhete({ de, para, lista }) {
  return lista.length > 0 && html`<div class="bilhete"><p class="bilhete-de">De ${de} para ${para}</p>
    <ul>${lista.slice(0, 3).map((a) => html`<li>${a}</li>`)}</ul></div>`;
}

function Par({ g, r, cores, n }) {
  const raiz = useRef(null);
  useEffect(() => {
    const el = raiz.current;
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) { el.classList.add('em-cena'); obs.disconnect(); } }, { threshold: 0.2 });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  const pares = g.flatMap((x, a) => g.slice(a + 1).map((y) => [x, y, r.detalhes[chave(x, y)]]));
  const nomes = g.length === 3 ? `${g[0]}, ${g[1]} e ${g[2]}` : `${g[0]} e ${g[1]}`;
  return html`<li ref=${raiz} class="amor" style=${{ '--a': cores[g[0]], '--b': cores[g[1]], '--n': Math.min(n, 3) }}>
    <span class="amor-flutua" aria-hidden="true">${[0, 1, 2, 3, 4, 5].map((k) => html`<i style=${{ '--k': k }}><${Coracao} /></i>`)}</span>
    <div class="amor-topo">
      <div class="amor-casal" aria-hidden="true">${g.map((n, k) => html`${k > 0 && html`<span class="amor-elo"><${Coracao} /></span>`}<span class="amor-avatar" style=${{ '--lut': cores[n], '--lado': k === 0 ? -1 : 1 }}>${inicial(n)}</span>`)}</div>
      <h3 class="amor-nomes">${g.map((n, k) => html`${k > 0 && html`<span class="amor-e">${k === g.length - 1 ? '&' : ','}</span>`}${n}`)}${g.length === 3 && html`<span class="fita fita-trio">Trio</span>`}</h3>
    </div>
    ${pares.map(([x, y, c]) => html`<div class="amor-par">
      ${g.length === 3 && html`<p class="amor-subpar">${x} & ${y}</p>`}
      <p class="amor-nota"><b>${pct(c.pontuacao)}</b><span class="fita">${c.nivel}</span></p>
      <p class="amor-medidor" role="img" aria-label=${`${coracoes(c.pontuacao)} de 5 corações`}>${[1, 2, 3, 4, 5].map((k) => html`<span style=${{ '--j': k }}><${Coracao} cheio=${k <= coracoes(c.pontuacao)} /></span>`)}</p>
      <p class="amor-frase">${c.descricao}</p>
      ${c.artistas_comuns.length > 0 && html`<div class="amor-comum"><p class="amor-rotulo">${g.length === 3 ? `${x} e ${y} amam` : 'Vocês dois amam'}</p>
        <ul class="amor-chips">${c.artistas_comuns.slice(0, 6).map((a, j) => html`<li style=${{ '--j': j }}><${Coracao} />${a}</li>`)}</ul>
        ${c.musicas_comuns > 0 && html`<p class="amor-musicas">e ${c.musicas_comuns === 1 ? 'uma música favorita' : `${c.musicas_comuns} músicas favoritas`} em comum</p>`}</div>`}
      <div class="amor-bilhetes">
        <${Bilhete} de=${y} para=${x} lista=${c.recomendacoes_para_a} />
        <${Bilhete} de=${x} para=${y} lista=${c.recomendacoes_para_b} />
      </div>
    </div>`)}
    <span class="sr-only">${nomes}</span>
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
    <h2 id="titulo-match" class="amor-titulo">Quem combina com quem</h2>
    <div ref=${stories} class="nucleo"><${Player} key=${r} slides=${slides} rotulo=${`Match de ${r.nomes.join(', ')}`} /></div>
    <div class="compartilhar"><div class="acoes">
      <button type="button" class="btn btn-borda vidro" onClick=${() => stories.current?.querySelector('.st-player')?.dispatchEvent(new Event('st-replay'))}>↺ Ver de novo</button>
    </div>${aviso && html`<p ref=${chegarPouco} class="nota" role="status">${aviso}</p>`}
    <${Dock} alvo=${stories} aoPoster=${poster} ocupado=${ocupado} comSom=${!!trilha.fila.length} /></div>
    ${trilha.fila.length > 0 && html`<${SomStories} key=${r} trilha=${trilha} alvo=${stories} nota=${NOTA_SOM} />`}
    <p class="batalha-resumo">Média dos pares: <b>${pct(r.pontuacao_media_pares)}</b>. Os pares somam a maior compatibilidade possível do grupo${r.nomes.length % 2 ? '; com número ímpar, uma pessoa entra no par onde mais combina e vira trio' : ''}.</p>
    <ul class="amores">${r.pares.map((g, n) => html`<${Par} g=${g} r=${r} cores=${cores} n=${n} />`)}</ul>
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
          <${Pessoa} rotulo=${String(i + 1)} cor="lut" exemplo=${EXEMPLOS[i % EXEMPLOS.length]} nome=${nome} aoMudarNome=${(v) => setNomes((n) => mudar(n, i, v))}
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
