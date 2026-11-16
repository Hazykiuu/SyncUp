// App do SyncUp no navegador: casca (topo, modos) e a tela Dupla.
import { html, render, useEffect, useRef, useState } from 'preact-htm';
import { chegarPouco } from './chegada.js';
import { ligarOndas } from './corrida.js';
import { audioCtx, destravarSom, pausarSom, silenciado } from './som.js';
import { Pessoa } from './envio.js';
import { Opcoes, PADRAO } from './opcoes.js';
import { Resultado } from './resultado.js';
import { Wrapped } from './wrapped.js';

const SEM_RESPOSTA = 'o SyncUp parou de responder, provavelmente por falta de memória. Recarregue a página e tente com menos arquivos.';
const DEMO = [['demo-wrapped.zip', 'Ana (fictícia)'], ['demo-bruno.zip', 'Bruno (fictício)']]; // os mesmos de ponte.arquivos_demo

// A comparação roda em JavaScript num Worker (dupla-worker.js), sem baixar o Python. Um Worker por
// comparação: ao terminar, o navegador devolve toda a memória (importa no celular).
function compararNoWorker(a, b, nomes, opcoes) {
  return new Promise((ok, erro) => {
    const w = new Worker('dupla-worker.js', { type: 'module' });
    w.onmessage = ({ data }) => { w.terminate(); data.ok ? ok(data.dados) : erro(new Error(data.erro)); };
    w.onerror = (e) => { e.preventDefault?.(); w.terminate(); erro(new Error(SEM_RESPOSTA)); };
    w.postMessage({ a, b, nomes, opcoes }, [...a, ...b].map((x) => x.bytes));
  });
}

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

  // `ler` devolve os dois lados ([{nome, bytes}]); ler os arquivos conta no tempo (é o que a pessoa espera).
  const rodar = async (ler, nomesUsados) => {
    setFase({ tipo: 'processando', etapa: 'Lendo os históricos e calculando a sintonia…' });
    try {
      const [a, b] = await ler();
      const r = await compararNoWorker(a, b, nomesUsados, opcoes);
      setFase({ tipo: 'resultado', r });
      requestAnimationFrame(() => document.getElementById('resultado')?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
    } catch (e) { setFase({ tipo: 'erro', mensagem: e.message }); }
  };
  const comparar = () => {
    ultima.current = 'comparar';
    destravarSom(); // dentro do clique, antes de qualquer espera: o iPhone só toca som destravado por um toque
    rodar(() => Promise.all(arquivos.map(lerArquivos)), [nomes[0] || 'Pessoa A', nomes[1] || 'Pessoa B']);
  };
  // Dois históricos fictícios prontos (gerados por tools/empacotar_web.py): nenhum dado real.
  const demo = () => {
    ultima.current = 'demo';
    destravarSom();
    setNomes(DEMO.map(([, nome]) => nome)); setArquivos([[], []]);
    rodar(() => Promise.all(DEMO.map(async ([arquivo]) => {
      const resposta = await fetch(arquivo).catch(() => null);
      if (!resposta?.ok) throw new Error('Não deu para baixar os históricos fictícios. Confira a internet e tente de novo.');
      return [{ nome: arquivo, bytes: await resposta.arrayBuffer() }];
    })), DEMO.map(([, nome]) => nome));
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
      <button type="button" class="btn btn-borda vidro" onClick=${demo} disabled=${ocupado}>Testar com dados fictícios</button>
      <small id="dica-comparar">${arquivos[0].length && arquivos[1].length ? '' : 'Envie pelo menos um arquivo para cada pessoa.'}</small>
    </div>
    <div aria-live="polite">
      ${fase.tipo === 'processando' && html`<p ref=${chegarPouco} class="processando vidro"><span class="giro" aria-hidden="true"></span>${fase.etapa}</p>`}
      ${fase.tipo === 'erro' && html`<div ref=${chegarPouco} class="erro vidro" role="alert"><p><b>Não deu certo.</b> ${fase.mensagem}</p>
        ${ultima.current && html`<button type="button" class="btn btn-borda vidro" onClick=${ultima.current === 'demo' ? demo : comparar}>Tentar de novo</button>`}</div>`}
      ${fase.tipo === 'resultado' && html`<p class="sr-only">Resultado de ${fase.r.nomes[0]} e ${fase.r.nomes[1]} pronto, logo abaixo.</p>`}
    </div>
    <div id="resultado">${fase.tipo === 'resultado' && html`<${Resultado} r=${fase.r} />`}</div>`;
}

// Clique do fader na troca de modo: um toque de 40 ms, bem baixo. Para o Wrapped sobe (sol, 1568 Hz);
// para a Dupla desce (ré, 1175 Hz), uma quinta abaixo: os dois lados do crossfader. Um por troca.
// Usa o mesmo AudioContext dos stories e respeita o "Silenciar" deles.
function cliqueFader(paraWrapped) {
  const audio = audioCtx();
  if (!audio || silenciado) return;
  try {
    audio.resume();
    const t = audio.currentTime, o = audio.createOscillator(), g = audio.createGain();
    o.frequency.value = paraWrapped ? 1568 : 1175;
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.028, t + 0.004); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.04);
    o.connect(g).connect(audio.destination); o.start(t); o.stop(t + 0.05);
  } catch { /* sem áudio: só a animação */ }
}

function App() {
  // As duas telas ficam montadas (hidden): trocar de aba não perde o resultado.
  // Só hash conhecido troca de modo: "Pular para o conteúdo" (#principal) fica onde a pessoa está.
  const lerModo = (atual = 'dupla') => (location.hash === '#wrapped' ? 'wrapped' : location.hash === '#dupla' || location.hash === '' ? 'dupla' : atual);
  const [modo, setModo] = useState(() => lerModo());
  const modoAtual = useRef(modo); // o efeito abaixo roda uma vez só e não enxerga o `modo` novo
  useEffect(() => {
    // Troca de modo como crossfader de DJ (app.css): o conteúdo desliza de um lado para o outro e o
    // destaque da barra corre como o botão do fader. Sem suporte ou com "menos movimento": troca seca.
    const mudar = () => {
      const novo = lerModo(modoAtual.current);
      if (novo === modoAtual.current) return;
      modoAtual.current = novo;
      pausarSom(); // um só <audio> para os dois modos: troca de modo pausa, e quem voltar a andar retoma o seu
      if (!document.startViewTransition || matchMedia('(prefers-reduced-motion: reduce)').matches) { setModo(novo); return; }
      cliqueFader(novo === 'wrapped');
      const update = async () => { setModo(novo); await new Promise((r) => setTimeout(r)); }; // espera o Preact desenhar
      let vt;
      try { vt = document.startViewTransition({ update, types: ['modo', `para-${novo}`] }); } catch { vt = document.startViewTransition(update); } // navegador sem tipos: fade simples
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
      <ul>${MODOS.map(([id, rotulo, icone, breve]) => html`<li>${breve
        ? html`<span class="nav-item" aria-disabled="true">${icone}<span>${rotulo}</span> <small>em breve</small></span>`
        : html`<a class="nav-item" href=${`#${id}`} aria-current=${modo === id ? 'page' : null}>${icone}<span>${rotulo}</span></a>`}</li>`)}</ul>
      <p class="nav-selo"><span class="ponto" aria-hidden="true"></span>Tudo roda no seu aparelho</p>
      <a class="nav-site" href="../">← Voltar ao site</a>
    </nav>
    <main id="principal" class="app-corpo" data-modo=${modo}>
      <div class="shell">
        <div class="app-cabeca">
          <h1>${modo === 'wrapped' ? 'Seu Wrapped da vida toda' : 'Compare dois históricos'}</h1>
          <p class="sub">${modo === 'wrapped' ? 'Envie o seu Histórico Estendido do Spotify e veja a sua vida musical em stories. O histórico não sai do seu aparelho.' : 'Envie o Histórico Estendido do Spotify de duas pessoas. Nada é enviado para nenhum servidor.'}</p>
        </div>
        <div hidden=${modo !== 'dupla'}><${Dupla} /></div>
        <div hidden=${modo !== 'wrapped'}><${Wrapped} /></div>
      </div>
    </main>`;
}

// Ícones dos modos: traço de 2 px, pontas redondas, como os da página inicial.
const icone = (corpo) => html`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${corpo}</svg>`;
const MODOS = [
  ['dupla', 'Dupla', icone(html`<circle cx="9" cy="12" r="6" /><circle cx="15" cy="12" r="6" />`)],
  ['wrapped', 'Wrapped', icone(html`<rect x="6" y="2.5" width="12" height="19" rx="2.5" /><path d="M9 6h6" />`)],
  ['match', 'Match', icone(html`<path d="M4 8h13l-3-3M20 16H7l3 3" />`), true],
  ['grupo', 'Grupo', icone(html`<circle cx="12" cy="7.5" r="3.5" /><circle cx="6" cy="16.5" r="3.5" /><circle cx="18" cy="16.5" r="3.5" />`), true],
];

// O aviso "Carregando o SyncUp…" do index.html sai: o render do Preact não apaga o que ele não criou.
// O Safari do iOS só aplica :active (toque nos botões e na barra) se a página ouvir touchstart.
document.addEventListener('touchstart', () => {}, { passive: true });
const raiz = document.getElementById('app');
raiz.replaceChildren();
ligarOndas();
render(html`<${App} />`, raiz);
