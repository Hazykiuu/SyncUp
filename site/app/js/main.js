// App do SyncUp no navegador: casca (topo, motor) e a tela Dupla.
import { html, render, useEffect, useRef, useState } from 'preact-htm';
import { chegarPouco, pulsar } from './chegada.js';
import { aoProgredir, executar, iniciar } from './motor.js';
import { Pessoa } from './envio.js';
import { Opcoes, PADRAO } from './opcoes.js';
import { Resultado } from './resultado.js';
import { Wrapped } from './wrapped.js';

// Carregamento como equalizador: 24 barras de alturas fixas que se acendem conforme o progresso.
const ALTURAS = [.35, .6, .45, .8, .55, 1, .7, .5, .85, .4, .65, .9, .5, .75, .45, .95, .6, .4, .7, .85, .5, .65, .35, .55];

// O ponto verde só pulsa quando o motor acabou de ficar pronto, não a cada volta para a Dupla.
let prontoEm = -Infinity;
const pontoPronto = (el) => { if (performance.now() - prontoEm < 1000) pulsar(el); };

function Motor({ estado }) {
  if (estado.pronto) return html`<p class="motor ok" role="status"><span ref=${pontoPronto} class="ponto" aria-hidden="true"></span>Pronto para comparar</p>`;
  if (estado.erro) return html`<p class="motor erro" role="alert">Não foi possível carregar o SyncUp: ${estado.erro} <button type="button" class="btn btn-borda vidro" onClick=${() => location.reload()}>Tentar de novo</button></p>`;
  return html`
    <div class="motor" role="status" aria-live="polite">
      <span>${estado.etapa}</span>
      <div class="eq" role="progressbar" aria-label="Carregando o SyncUp" aria-valuemin="0" aria-valuemax="100" aria-valuenow=${Math.round(estado.fracao * 100)}>
        ${ALTURAS.map((h, k) => html`<i class=${k < Math.round(estado.fracao * ALTURAS.length) ? 'aceso' : ''} style=${{ '--h': h }}></i>`)}
      </div>
      <small>Na primeira visita o navegador baixa o Python (~15 MB) e guarda. Nas próximas ele só carrega, em alguns segundos.</small>
    </div>`;
}

function Dupla({ pronto }) {
  const [nomes, setNomes] = useState(['', '']);
  const [arquivos, setArquivos] = useState([[], []]);
  const [opcoes, setOpcoes] = useState(PADRAO);
  const [fase, setFase] = useState({ tipo: 'parado' });
  const ocupado = fase.tipo === 'processando';
  const pode = pronto && !ocupado && arquivos[0].length > 0 && arquivos[1].length > 0;
  const ultima = useRef(null); // a última tentativa, para o "Tentar de novo" do erro

  const rodar = async (args, envio = []) => {
    setFase({ tipo: 'processando', etapa: 'Lendo os históricos e calculando a sintonia… (na primeira comparação o navegador também baixa os gráficos, ~10 MB)' });
    try {
      const r = await executar('comparar_dupla', args, { arquivos: envio });
      setFase({ tipo: 'resultado', r });
      requestAnimationFrame(() => document.getElementById('resultado')?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
    } catch (e) { setFase({ tipo: 'erro', mensagem: e.message }); }
  };
  const comparar = () => {
    const envio = arquivos.flatMap((lista, p) => lista.map((arquivo, i) => ({ caminho: `/tmp/${p ? 'b' : 'a'}-${i}-${arquivo.name.replace(/[^\w.-]/g, '_')}`, arquivo })));
    const caminhos = [0, 1].map((p) => envio.filter((e) => e.caminho.startsWith(`/tmp/${p ? 'b' : 'a'}-`)).map((e) => e.caminho));
    ultima.current = comparar;
    rodar([caminhos[0], caminhos[1], nomes[0] || 'Pessoa A', nomes[1] || 'Pessoa B', opcoes], envio);
  };
  const demo = async () => {
    ultima.current = demo;
    setFase({ tipo: 'processando', etapa: 'Gerando dois históricos fictícios no seu aparelho…' });
    try {
      const d = await executar('arquivos_demo');
      setNomes([d.nome_a, d.nome_b]); setArquivos([[], []]);
      await rodar([[d.a], [d.b], d.nome_a, d.nome_b, opcoes]);
    } catch (e) { setFase({ tipo: 'erro', mensagem: e.message }); }
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
      <button type="button" class="btn btn-borda vidro" onClick=${demo} disabled=${!pronto || ocupado}>Testar com dados fictícios</button>
      <small id="dica-comparar">${!pronto ? 'Esperando o SyncUp terminar de carregar.' : arquivos[0].length && arquivos[1].length ? '' : 'Envie pelo menos um arquivo para cada pessoa.'}</small>
    </div>
    <div aria-live="polite">
      ${fase.tipo === 'processando' && html`<p ref=${chegarPouco} class="processando vidro"><span class="giro" aria-hidden="true"></span>${fase.etapa}</p>`}
      ${fase.tipo === 'erro' && html`<div ref=${chegarPouco} class="erro vidro" role="alert"><p><b>Não deu certo.</b> ${fase.mensagem}</p>
        ${ultima.current && html`<button type="button" class="btn btn-borda vidro" onClick=${() => ultima.current()}>Tentar de novo</button>`}</div>`}
      ${fase.tipo === 'resultado' && html`<p class="sr-only">Resultado de ${fase.r.nomes[0]} e ${fase.r.nomes[1]} pronto, logo abaixo.</p>`}
    </div>
    <div id="resultado">${fase.tipo === 'resultado' && html`<${Resultado} r=${fase.r} />`}</div>`;
}

function App() {
  const [motor, setMotor] = useState({ etapa: 'Preparando…', fracao: 0, pronto: false, erro: '' });
  // As duas telas ficam montadas (hidden): trocar de aba não perde o resultado.
  const lerModo = () => (location.hash === '#wrapped' ? 'wrapped' : 'dupla');
  const [modo, setModo] = useState(lerModo);
  useEffect(() => {
    const mudar = () => setModo(lerModo());
    addEventListener('hashchange', mudar);
    return () => removeEventListener('hashchange', mudar);
  }, []);
  // O Python (Pyodide) só baixa quando a Dupla abre: o Wrapped roda em JavaScript.
  const iniciado = useRef(false);
  useEffect(() => {
    if (modo !== 'dupla' || iniciado.current) return;
    iniciado.current = true;
    aoProgredir(({ etapa, fracao }) => setMotor((m) => ({ ...m, etapa, fracao })));
    iniciar().then(() => { prontoEm = performance.now(); setMotor((m) => ({ ...m, pronto: true })); }).catch((e) => setMotor((m) => ({ ...m, erro: e.message })));
  }, [modo]);
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
          ${modo === 'dupla' && html`<${Motor} estado=${motor} />`}
        </div>
        <div hidden=${modo !== 'dupla'}><${Dupla} pronto=${motor.pronto} /></div>
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
render(html`<${App} />`, raiz);
