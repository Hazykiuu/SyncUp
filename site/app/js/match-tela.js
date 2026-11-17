// Tela do Match: ZIPs e convites colados, o Worker e os pares que mais combinam (com os motivos).
import { html, useEffect, useRef, useState } from 'preact-htm';
import { CORES } from './batalha.js';
import { chegarPouco, rolarAte } from './chegada.js';
import { Pessoa } from './envio.js';
import { Opcoes, PADRAO } from './opcoes.js';
import { chave } from './match.js';
import { fmtNum } from './stories/logica.js';
import { abrirWorker } from './worker.js';

const SEM_RESPOSTA = 'o SyncUp parou de responder, provavelmente por falta de memória. Recarregue a página e tente com menos pessoas.';
const DEMO = [['demo-wrapped.zip', 'Ana'], ['demo-bruno.zip', 'Bruno'], ['demo-carla.zip', 'Carla'], ['demo-davi.zip', 'Davi']];
const AVISO = 'O Match compara só os rankings de artistas e músicas. Não mede afinidade pessoal.';
const EXEMPLOS = ['Ana', 'Bia', 'Caio', 'Duda', 'Edu', 'Fabi'];
const cor = (i) => CORES[i % CORES.length];
const pct = (v) => `${fmtNum(v, 1)}%`;

// Um cartão por grupo (dupla ou trio): a nota de cada par, o nível e o porquê.
function Par({ g, r, cores }) {
  const pares = g.flatMap((x, a) => g.slice(a + 1).map((y) => [x, y, r.detalhes[chave(x, y)]]));
  return html`<li class="rodada vidro match-par">
    <h3>${g.map((n, k) => html`${k > 0 && html`<span class="match-x" aria-hidden="true"> × </span>`}<span class="lut-ponto" style=${{ '--lut': cores[n] }} aria-hidden="true"></span>${n}`)}${g.length === 3 && html` <span class="selo">Trio</span>`}</h3>
    ${pares.map(([x, y, c]) => html`<div class="match-detalhe">
      <p class="rodada-vence">${g.length === 3 ? `${x} e ${y}: ` : ''}<b>${pct(c.pontuacao)}</b> <small>${c.nivel}</small></p>
      <p class="nota">${c.descricao}</p>
      ${c.artistas_comuns.length > 0 && html`<p><small>Em comum</small> ${c.artistas_comuns.slice(0, 5).join(', ')}${c.musicas_comuns ? ` · ${c.musicas_comuns} ${c.musicas_comuns === 1 ? 'música favorita' : 'músicas favoritas'} em comum` : ''}</p>`}
      ${c.recomendacoes_para_a.length > 0 && html`<p><small>Para ${x} ouvir</small> ${c.recomendacoes_para_a.slice(0, 3).join(', ')}</p>`}
      ${c.recomendacoes_para_b.length > 0 && html`<p><small>Para ${y} ouvir</small> ${c.recomendacoes_para_b.slice(0, 3).join(', ')}</p>`}
    </div>`)}</li>`;
}

function ResultadoMatch({ dados: { r, fontes, fora } }) {
  const cores = Object.fromEntries(r.nomes.map((n, i) => [n, cor(i)]));
  return html`<section class="resultado" aria-labelledby="titulo-match">
    <h2 id="titulo-match">Os pares que mais combinam</h2>
    <p class="batalha-resumo">Média dos pares: <b>${pct(r.pontuacao_media_pares)}</b>. Os pares somam a maior compatibilidade possível do grupo${r.nomes.length % 2 ? '; com número ímpar, uma pessoa entra no par onde mais combina e vira trio' : ''}.</p>
    <ul class="rodadas">${r.pares.map((g) => html`<${Par} g=${g} r=${r} cores=${cores} />`)}</ul>
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
    const usados = arquivos.map((a, i) => [a, (nomes[i] || '').trim() || `Pessoa ${i + 1}`]).filter(([a]) => a.length);
    rodar(async () => usados.map(([a]) => a), usados.map(([, n]) => n), convites);
  };
  const demo = () => {
    ultima.current = 'demo';
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

  return html`
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
    <div id="resultado-match">${fase.tipo === 'resultado' && html`<${ResultadoMatch} dados=${fase.dados} />`}</div>`;
}
