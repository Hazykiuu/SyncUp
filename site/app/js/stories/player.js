// Player dos stories (Wrapped, Dupla e Batalha), em Preact. A máquina de estados e o relógio ficam em
// logica.js (testados); aqui entram os gestos: toque (esquerda volta, direita avança), segurar pausa,
// arrastar troca, teclado (← → Home End espaço), aba oculta e modo escondido. O tempo é do relógio em JS:
// a barra só o mostra, então "menos movimento" (sem animação) não trava o avanço.
import { createContext, html, useContext, useEffect, useReducer, useRef, useState } from 'preact-htm';
import { correr, duracaoMs, inicial, parar, pausado, player, relogio, restanteEm } from './logica.js';
import { luzAmbiente } from './slides.js';

// Os modos ficam montados e escondidos (main.js): cada um diz ao seu player se está na tela.
export const TelaAtiva = createContext(true);

const SEGURAR_MS = 250;
const ARRASTO_PX = 40;
const reduzido = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

// ?fps=1: quadros por segundo no canto da tela, para medir o player em celulares (só desenvolvimento).
const MEDIR_FPS = new URLSearchParams(location.search).get('fps') === '1';
const ESTILO_FPS = { position: 'fixed', left: '8px', bottom: '8px', zIndex: 50, margin: 0, padding: '4px 8px', borderRadius: '6px', background: 'rgba(0,0,0,.8)', color: '#1ed760', font: '700 12px/1 monospace' };
function Fps() {
  const [fps, setFps] = useState(0);
  useEffect(() => {
    let quadro, n = 0, inicio = performance.now();
    const passo = (t) => {
      n++;
      if (t - inicio >= 1000) { setFps(Math.round((n * 1000) / (t - inicio))); n = 0; inicio = t; }
      quadro = requestAnimationFrame(passo);
    };
    quadro = requestAnimationFrame(passo);
    return () => cancelAnimationFrame(quadro);
  }, []);
  return html`<p aria-hidden="true" style=${ESTILO_FPS}>${fps} fps</p>`;
}

export function Player({ slides, rotulo, aoMudar }) {
  const [estado, despachar] = useReducer(player, slides.length, (n) => inicial(n, { semMovimento: reduzido() }));
  const toque = useRef(null);
  const replay = () => despachar({ tipo: 'REPLAY' });
  // Para slides interativos (anos do story 11): pausar e retomar por um motivo próprio.
  const controle = { pausar: (motivo) => despachar({ tipo: 'PAUSAR', motivo }), retomar: (motivo) => despachar({ tipo: 'RETOMAR', motivo }) };
  const parado = pausado(estado);
  // A classe .pausado (que o som.js observa) ignora o modo escondido: ao voltar para o modo, o som
  // só retoma no próximo movimento do story, como antes. O relógio usa `parado`, que conta tudo.
  const paradoVisivel = estado.fim || estado.motivos.some((m) => m !== 'escondido');

  useEffect(() => { aoMudar?.({ i: estado.i, tipo: slides[estado.i].tipo, pausado: parado, volta: estado.volta }); }, [estado.i, parado, estado.volta]);
  const raiz = useRef(null);
  const barra = useRef(null); // o <i> do segmento atual
  const anim = useRef(null);
  const tempo = useRef(null); // { chave, r }: o relógio do segmento atual
  const ativo = useContext(TelaAtiva);
  const saiu = useRef(false);

  // Modo escondido pausa; ao voltar, o segmento recomeça do zero (como a animação CSS fazia antes).
  useEffect(() => {
    if (!ativo) { saiu.current = true; despachar({ tipo: 'PAUSAR', motivo: 'escondido' }); return; }
    if (saiu.current) { saiu.current = false; tempo.current = null; despachar({ tipo: 'RETOMAR', motivo: 'escondido' }); }
  }, [ativo]);

  // Relógio: recomeça a cada slide (ou replay), corre ou para com o estado e avança sozinho no fim.
  // A barra (WAAPI) recebe o mesmo tempo restante a cada mudança; sem animação com "menos movimento".
  useEffect(() => {
    const agora = performance.now(), chave = `${estado.i}-${estado.volta}`;
    if (tempo.current?.chave !== chave) tempo.current = { chave, r: relogio(duracaoMs(getComputedStyle(raiz.current).getPropertyValue('--dur-story'))) };
    const t = tempo.current;
    t.r = parado ? parar(t.r, agora) : correr(t.r, agora);
    const el = barra.current;
    if (el && !reduzido()) {
      if (anim.current?.effect?.target !== el) {
        anim.current?.cancel();
        anim.current = el.animate([{ transform: 'scaleX(0)' }, { transform: 'scaleX(1)' }], { duration: t.r.dur, fill: 'forwards' });
      }
      anim.current.currentTime = t.r.dur - restanteEm(t.r, agora);
      parado ? anim.current.pause() : anim.current.play();
    }
    if (parado) return undefined;
    const timer = setTimeout(() => despachar({ tipo: 'TEMPO' }), restanteEm(t.r, agora));
    return () => clearTimeout(timer);
  }, [estado.i, estado.volta, parado]);
  useEffect(() => () => anim.current?.cancel(), []);
  // Luz ambiente: ao trocar de story, a capa já carregada do novo story acende o fundo (as que ainda
  // carregam acendem sozinhas, no onLoad do Slide).
  useEffect(() => {
    const img = raiz.current?.querySelector('.st-slot.ativo .st-fundo img');
    if (img?.complete && img.naturalWidth) luzAmbiente(img);
  }, [estado.i]);

  // O som recomeça os stories do primeiro slide quando a trilha fica pronta.
  useEffect(() => {
    const el = raiz.current, replay = () => despachar({ tipo: 'REPLAY' });
    el.addEventListener('st-replay', replay);
    return () => el.removeEventListener('st-replay', replay);
  }, []);
  useEffect(() => {
    const aba = () => despachar({ tipo: document.hidden ? 'PAUSAR' : 'RETOMAR', motivo: 'oculta' });
    document.addEventListener('visibilitychange', aba);
    return () => document.removeEventListener('visibilitychange', aba);
  }, []);

  // Último story = pôster: barra e pausa somem depois de 2 s para o print sair limpo; um toque traz de volta.
  const [limpo, setLimpo] = useState(false);
  const [mexeu, setMexeu] = useState(0);
  const ultimo = estado.i === slides.length - 1;
  useEffect(() => {
    setLimpo(false);
    if (!ultimo) return undefined;
    const t = setTimeout(() => setLimpo(true), 2000);
    return () => clearTimeout(t);
  }, [ultimo, mexeu]);
  const acordar = () => setMexeu((n) => n + 1);

  // Elementos com data-interativo (ex.: anos do story 11) e botões não contam como navegação.
  const ignorar = (e) => e.target.closest('[data-interativo], button, a');
  const baixo = (e) => {
    if (ultimo && limpo) { acordar(); return; } // toque no pôster limpo só mostra os controles
    if (ignorar(e)) return;
    const t = { x: e.clientX, y: e.clientY, segurou: false };
    t.timer = setTimeout(() => { t.segurou = true; despachar({ tipo: 'PAUSAR', motivo: 'segurar' }); }, SEGURAR_MS);
    toque.current = t;
  };
  const cima = (e) => {
    acordar();
    const t = toque.current; toque.current = null;
    if (!t) return;
    clearTimeout(t.timer);
    if (t.segurou) { despachar({ tipo: 'RETOMAR', motivo: 'segurar' }); return; }
    const dx = e.clientX - t.x;
    if (Math.abs(dx) > ARRASTO_PX && Math.abs(dx) > Math.abs(e.clientY - t.y)) despachar({ tipo: dx < 0 ? 'AVANCAR' : 'VOLTAR' });
    else {
      const caixa = e.currentTarget.getBoundingClientRect();
      despachar({ tipo: e.clientX - caixa.left < caixa.width * 0.3 ? 'VOLTAR' : 'AVANCAR' });
    }
  };
  const cancelar = () => { const t = toque.current; toque.current = null; if (t) { clearTimeout(t.timer); if (t.segurou) despachar({ tipo: 'RETOMAR', motivo: 'segurar' }); } };
  const tecla = (e) => {
    acordar();
    if (e.target.closest('[data-interativo]')) return; // lá dentro as setas são dos chips
    if ((e.key === ' ' || e.key === 'Enter') && e.target.closest('button, a')) return; // o botão faz a ação dele
    const acao = { ArrowRight: { tipo: 'AVANCAR' }, ArrowLeft: { tipo: 'VOLTAR' }, ' ': { tipo: 'ALTERNAR' },
      Home: { tipo: 'IR', i: 0 }, End: { tipo: 'IR', i: slides.length - 1 } }[e.key];
    if (acao) { e.preventDefault(); despachar(acao); }
  };

  return html`
    ${MEDIR_FPS && html`<${Fps} />`}
    <div ref=${raiz} class=${`su-stories su-js st-player${paradoVisivel ? ' pausado' : ''}${limpo ? ' limpo' : ''}`} onFocusIn=${acordar} tabindex="0" role="region"
      aria-roledescription="stories" aria-label=${rotulo} onKeyDown=${tecla}
      onPointerDown=${baixo} onPointerUp=${cima} onPointerCancel=${cancelar} onPointerLeave=${cancelar}>
      <div class="st-barra vidro-ctrl" aria-hidden="true">
        ${slides.map((_, k) => html`<span class=${`st-seg${k < estado.i || (estado.fim && k === estado.i) ? ' feito' : ''}`}>${k === estado.i && !estado.fim && html`
          <i key=${`${estado.i}-${estado.volta}`} ref=${barra}></i>`}</span>`)}
      </div>
      <div class="st-controles">
        <span class="st-contador" aria-live="polite">${estado.i + 1}/${slides.length}</span>
        <button type="button" class="st-botao vidro-ctrl sr-only-foco" aria-label="Story anterior" onClick=${() => despachar({ tipo: 'VOLTAR' })}>‹</button>
        <button type="button" class="st-botao vidro-ctrl sr-only-foco" aria-label="Próximo story" onClick=${() => despachar({ tipo: 'AVANCAR' })}>›</button>
        <button type="button" class=${`st-botao st-pausa vidro-ctrl${paradoVisivel ? ' parado' : ''}`} aria-label=${paradoVisivel ? 'Continuar' : 'Pausar'}
          onClick=${() => despachar({ tipo: estado.fim ? 'REPLAY' : 'ALTERNAR' })}></button>
      </div>
      <div class="su-stories-frame">
        ${slides.map((s, k) => html`<div class=${`st-slot${k === estado.i ? ' ativo' : ''}`} hidden=${k !== estado.i} key=${s.tipo}>${s.render({ ativo: k === estado.i, i: k, replay, controle })}</div>`)}
      </div>
    </div>`;
}
