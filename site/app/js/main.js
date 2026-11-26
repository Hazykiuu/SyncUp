// App do SyncUp no navegador: casca (topo, modos) e a tela Dupla.
import { html, render, useEffect, useRef, useState } from 'preact-htm';
import { chegarPouco, mostrarResultado } from './chegada.js';
import { ligarOndas } from './corrida.js';
import { audioCtx, capasESom, definirCapasESom, destravarSom, pausarSom, silenciado, TRILHA_EXEMPLO } from './som.js';
import { Batalha } from './batalha-tela.js';
import { MAXIMO_PESSOAS } from './match.js';
import { limparLastfmVencido } from './lastfm.js';
import { Match } from './match-tela.js';
import { Pessoa, Processando } from './envio.js';
import { Opcoes, PADRAO } from './opcoes.js';
import { Resultado } from './resultado.js';
import { TelaAtiva } from './stories/player.js';
import { Wrapped } from './wrapped.js';
import { rodarNoWorker } from './worker.js';

// Históricos de exemplo gerados por tools/empacotar_web.py. Nomes curtos: o nome longo quebrava no primeiro story.
const DEMO = [['demo-wrapped.zip', 'Rafa'], ['demo-bruno.zip', 'Lu']];

// A comparação roda em JavaScript num Worker (dupla-worker.js), sem baixar o Python. Um Worker por
// comparação: ao terminar, o navegador devolve toda a memória (importa no celular).
const compararNoWorker = (a, b, nomes, opcoes, sinal) => rodarNoWorker('dupla-worker.js', { a, b, nomes, opcoes }, [...a, ...b].map((x) => x.bytes), sinal);

const lerArquivos = (lista) => Promise.all(lista.map(async (f) => ({ nome: f.name, bytes: await f.arrayBuffer() })));

function Dupla() {
  const [nomes, setNomes] = useState(['', '']);
  const [arquivos, setArquivos] = useState([[], []]);
  const [opcoes, setOpcoes] = useState(PADRAO);
  const [fase, setFase] = useState({ tipo: 'parado' });
  const ocupado = fase.tipo === 'processando';
  const pode = !ocupado && arquivos[0].length > 0 && arquivos[1].length > 0;
  // Qual foi a última tentativa ("comparar" ou "demo"), para o "Tentar de novo" do erro. Guarda o tipo, não a
  // função: o botão chama a da renderização atual, com os arquivos e opções que a tela mostra agora.
  const ultima = useRef(null);
  const controle = useRef(null);
  const cancelar = () => { controle.current?.abort(); setFase({ tipo: 'parado' }); };

  // `ler` devolve os dois lados ([{nome, bytes}]); ler os arquivos conta no tempo (é o que a pessoa espera).
  const rodar = async (ler, nomesUsados, exemplo = false) => {
    const { signal } = (controle.current = new AbortController());
    setFase({ tipo: 'processando', etapa: 'Lendo os históricos e calculando a sintonia…' });
    try {
      const [a, b] = await ler();
      const r = await compararNoWorker(a, b, nomesUsados, opcoes, signal);
      if (exemplo && r.dupla.trilha) r.dupla.trilha = TRILHA_EXEMPLO;
      // Last.fm: minutos pela duração das músicas ("≈" nos stories). A sintonia junta os dois lados.
      if (!exemplo) {
        r.dupla.a.aproximado = arquivos[0].some((f) => f.lastfm);
        r.dupla.b.aproximado = arquivos[1].some((f) => f.lastfm);
        r.dupla.aproximado = r.dupla.a.aproximado || r.dupla.b.aproximado;
      }
      mostrarResultado(() => setFase({ tipo: 'resultado', r }), 'resultado');
    } catch (e) { if (!signal.aborted && e.name !== 'AbortError') setFase({ tipo: 'erro', mensagem: e.message }); }
  };
  const comparar = () => {
    ultima.current = 'comparar';
    destravarSom(); // dentro do clique, antes de qualquer espera: o iPhone só toca som destravado por um toque
    rodar(() => Promise.all(arquivos.map(lerArquivos)), [nomes[0] || 'Pessoa A', nomes[1] || 'Pessoa B']);
  };
  // Dois históricos de exemplo (gerados por tools/empacotar_web.py): nenhum dado real.
  const demo = () => {
    ultima.current = 'demo';
    destravarSom();
    setNomes(DEMO.map(([, nome]) => nome)); setArquivos([[], []]);
    rodar(() => Promise.all(DEMO.map(async ([arquivo]) => {
      const resposta = await fetch(arquivo).catch(() => null);
      if (!resposta?.ok) throw new Error('Não deu para baixar o exemplo. Confira a internet e tente de novo.');
      return [{ nome: arquivo, bytes: await resposta.arrayBuffer() }];
    })), DEMO.map(([, nome]) => nome), true);
  };
  // Atualização por função: duas mudanças no mesmo instante não apagam uma à outra.
  const mudar = (lista, i, v) => lista.map((x, j) => (j === i ? v : x));

  return html`
    <div class="pessoas">
      <${Pessoa} rotulo="A" cor="verde" nome=${nomes[0]} aoMudarNome=${(v) => setNomes((n) => mudar(n, 0, v))} arquivos=${arquivos[0]} aoMudarArquivos=${(v) => setArquivos((a) => mudar(a, 0, v))} desabilitado=${ocupado} />
      <${Pessoa} rotulo="B" cor="roxo" nome=${nomes[1]} aoMudarNome=${(v) => setNomes((n) => mudar(n, 1, v))} arquivos=${arquivos[1]} aoMudarArquivos=${(v) => setArquivos((a) => mudar(a, 1, v))} desabilitado=${ocupado} />
    </div>
    <${Opcoes} valor=${opcoes} aoMudar=${setOpcoes} desabilitado=${ocupado} />
    <div class="barra-acao">
      <button type="button" class="btn btn-verde" onClick=${comparar} disabled=${!pode} aria-describedby="dica-comparar">
        ${ocupado ? 'Comparando…' : 'Comparar históricos'}<span class="seta" aria-hidden="true">→</span></button>
      <button type="button" class="btn btn-borda superficie" onClick=${demo} disabled=${ocupado}>Ver um exemplo</button>
      <small id="dica-comparar">${arquivos[0].length && arquivos[1].length ? '' : 'Envie pelo menos um arquivo para cada pessoa.'}</small>
    </div>
    <div aria-live="polite">
      ${fase.tipo === 'processando' && html`<${Processando} etapa=${fase.etapa} aoCancelar=${cancelar} aoMontar=${chegarPouco} />`}
      ${fase.tipo === 'erro' && html`<div ref=${chegarPouco} class="erro superficie" role="alert"><p><b>Não deu certo.</b> ${fase.mensagem}</p>
        ${ultima.current && html`<button type="button" class="btn btn-borda superficie" onClick=${ultima.current === 'demo' ? demo : comparar}>Tentar de novo</button>`}</div>`}
      ${fase.tipo === 'resultado' && html`<p class="sr-only">Resultado de ${fase.r.nomes[0]} e ${fase.r.nomes[1]} pronto, logo abaixo.</p>`}
    </div>
    <div id="resultado">${fase.tipo === 'resultado' && html`<${Resultado} r=${fase.r} />`}</div>`;
}

// Clique do fader na troca de modo: um toque de 40 ms, bem baixo. Para a direita na barra (Dupla → Wrapped
// → Batalha) sobe (sol, 1568 Hz); para a esquerda desce (ré, 1175 Hz), uma quinta abaixo. Um por troca.
// Usa o mesmo AudioContext dos stories e respeita o "Silenciar" deles.
function cliqueFader(paraDireita) {
  const audio = audioCtx();
  if (!audio || silenciado) return;
  try {
    audio.resume();
    const t = audio.currentTime, o = audio.createOscillator(), g = audio.createGain();
    o.frequency.value = paraDireita ? 1568 : 1175;
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.028, t + 0.004); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.04);
    o.connect(g).connect(audio.destination); o.start(t); o.stop(t + 0.05);
  } catch { /* sem áudio: só a animação */ }
}

const CABECA = {
  dupla: ['Compare dois históricos', 'Envie o Histórico Estendido do Spotify de duas pessoas. O histórico não sai do seu aparelho; com “Capas e som” ligado, nomes de artistas e músicas em comum vão para o iTunes.'],
  wrapped: ['Seu Wrapped da vida toda', 'Envie o seu Histórico Estendido do Spotify e veja a sua vida musical em stories. O histórico não sai do seu aparelho.'],
  match: ['Match do grupo', `Junte históricos e convites de 2 a ${MAXIMO_PESSOAS} pessoas e veja quem combina com quem. O histórico não sai do seu aparelho; com “Capas e som” ligado, nomes de artistas vão para o iTunes.`],
  batalha: ['Batalha de históricos', 'Junte de 3 a 6 históricos do Spotify e veja quem leva cada rodada. O histórico não sai do seu aparelho; com “Capas e som” ligado, nomes de artistas vão para o iTunes.'],
};

function App() {
  const [comCapas, setComCapas] = useState(capasESom);
  // As telas ficam montadas (hidden): trocar de aba não perde o resultado.
  // Só hash conhecido troca de modo: "Pular para o conteúdo" (#principal) fica onde a pessoa está.
  const lerModo = (atual = 'dupla') => ({ '#wrapped': 'wrapped', '#batalha': 'batalha', '#match': 'match', '#dupla': 'dupla', '': 'dupla' })[location.hash] ?? atual;
  const [modo, setModo] = useState(() => lerModo());
  const modoAtual = useRef(modo); // o efeito abaixo roda uma vez só e não enxerga o `modo` novo
  useEffect(() => {
    // Troca de modo como crossfader de DJ (app.css): o conteúdo desliza de um lado para o outro e o
    // destaque da barra corre como o botão do fader. Sem suporte ou com "menos movimento": troca seca.
    const mudar = () => {
      const novo = lerModo(modoAtual.current);
      if (novo === modoAtual.current) return;
      const antigo = modoAtual.current;
      modoAtual.current = novo;
      pausarSom(); // um só <audio> para os dois modos: troca de modo pausa, e quem voltar a andar retoma o seu
      if (!document.startViewTransition || matchMedia('(prefers-reduced-motion: reduce)').matches) { setModo(novo); return; }
      // Na ordem da barra (Dupla, Wrapped, Batalha, Match): para a direita o conteúdo entra pela direita e o clique sobe.
      const ordem = ['dupla', 'wrapped', 'batalha', 'match'], volta = ordem.indexOf(novo) < ordem.indexOf(antigo);
      cliqueFader(!volta);
      const update = async () => { setModo(novo); await new Promise((r) => setTimeout(r)); }; // espera o Preact desenhar
      let vt;
      try { vt = document.startViewTransition({ update, types: ['modo', `para-${novo}`, ...(volta ? ['volta'] : [])] }); } catch { vt = document.startViewTransition(update); } // navegador sem tipos: fade simples
      vt.ready.catch(() => {}); // aba em segundo plano: o navegador pula a animação, a troca acontece igual
    };
    addEventListener('hashchange', mudar);
    return () => removeEventListener('hashchange', mudar);
  }, []);
  const marca = html`<a class="marca vivo" href="../" aria-label="SyncUp, voltar ao site"><span class="logo" aria-hidden="true"><i></i><i></i><i></i><i></i></span>SyncUp</a>`;
  return html`
    <header class="app-topo shell">${marca}</header>
    <nav class="nav-app" aria-label="Modos">
      ${marca}
      <ul>${MODOS.map(([id, rotulo, icone]) => html`<li>
        <a class="nav-item" href=${`#${id}`} aria-current=${modo === id ? 'page' : null}>${icone}<span>${rotulo}</span></a></li>`)}</ul>
      <p class="nav-selo"><span class="ponto" aria-hidden="true"></span>Tudo roda no seu aparelho</p>
      <a class="nav-site" href="../">← Voltar ao site</a>
    </nav>
    <main id="principal" class="app-corpo" data-modo=${modo}>
      <div class="shell">
        <div class="app-cabeca">
          <div class="app-capa" aria-hidden="true">${MODOS.find(([id]) => id === modo)[2]}</div>
          <div class="app-cabeca-texto">
            <span class="app-tipo">Modo · ${MODOS.find(([id]) => id === modo)[1]}</span>
            <h1>${CABECA[modo][0]}</h1>
            <p class="sub">${CABECA[modo][1]}</p>
            <label class="marcar app-capas-som"><input type="checkbox" checked=${comCapas} onChange=${(e) => { definirCapasESom(e.target.checked); setComCapas(e.target.checked); }} />
              <span>Capas e som <small>(busca capas e trechos no Spotify, no MusicBrainz e na Apple)</small></span></label>
            <a class="app-como-pedir" href="../#como-pedir">Ainda não tem o ZIP? Veja como pedir</a>
          </div>
        </div>
        ${[['dupla', Dupla], ['wrapped', Wrapped], ['batalha', Batalha], ['match', Match]].map(([id, Tela]) => html`
          <div key=${id} hidden=${modo !== id}><${TelaAtiva.Provider} value=${modo === id}><${Tela} /><//></div>`)}
      </div>
    </main>`;
}

// Ícones dos modos: traço de 2 px, pontas redondas, como os da página inicial.
const icone = (corpo) => html`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${corpo}</svg>`;
const MODOS = [
  ['dupla', 'Dupla', icone(html`<circle cx="9" cy="12" r="6" /><circle cx="15" cy="12" r="6" />`)],
  ['wrapped', 'Wrapped', icone(html`<rect x="6" y="2.5" width="12" height="19" rx="2.5" /><path d="M9 6h6" />`)],
  ['batalha', 'Batalha', icone(html`<circle cx="12" cy="7.5" r="3.5" /><circle cx="6" cy="16.5" r="3.5" /><circle cx="18" cy="16.5" r="3.5" />`)],
  ['match', 'Match', icone(html`<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10Z" />`)],
];

// O aviso "Carregando o SyncUp…" do index.html sai: o render do Preact não apaga o que ele não criou.
// O Safari do iOS só aplica :active (toque nos botões e na barra) se a página ouvir touchstart.
document.addEventListener('touchstart', () => {}, { passive: true });
const raiz = document.getElementById('app');
raiz.replaceChildren();
ligarOndas();
limparLastfmVencido();
render(html`<${App} />`, raiz);
