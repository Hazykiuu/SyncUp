// Player dos stories do Wrapped (Preact). A máquina de estados fica em logica.js (testada);
// aqui só entram os gestos: toque (esquerda volta, direita avança), segurar pausa, arrastar troca,
// teclado (← → espaço) e aba oculta. Quem marca o tempo é a animação CSS do segmento ativo.
import { html, useEffect, useReducer, useRef } from 'preact-htm';
import { inicial, pausado, player } from './logica.js';

const SEGURAR_MS = 250;
const ARRASTO_PX = 40;
const reduzido = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

export function Player({ slides, rotulo, aoMudar }) {
  const [estado, despachar] = useReducer(player, slides.length, (n) => inicial(n, { semMovimento: reduzido() }));
  const toque = useRef(null);
  const replay = () => despachar({ tipo: 'REPLAY' });
  // Para slides interativos (anos do story 11): pausar e retomar por um motivo próprio.
  const controle = { pausar: (motivo) => despachar({ tipo: 'PAUSAR', motivo }), retomar: (motivo) => despachar({ tipo: 'RETOMAR', motivo }) };
  const parado = pausado(estado);

  useEffect(() => { aoMudar?.({ i: estado.i, tipo: slides[estado.i].tipo, pausado: parado, volta: estado.volta }); }, [estado.i, parado, estado.volta]);
  const raiz = useRef(null);
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

  // Elementos com data-interativo (ex.: anos do story 11) e botões não contam como navegação.
  const ignorar = (e) => e.target.closest('[data-interativo], button, a');
  const baixo = (e) => {
    if (ignorar(e)) return;
    const t = { x: e.clientX, y: e.clientY, segurou: false };
    t.timer = setTimeout(() => { t.segurou = true; despachar({ tipo: 'PAUSAR', motivo: 'segurar' }); }, SEGURAR_MS);
    toque.current = t;
  };
  const cima = (e) => {
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
    if (e.target.closest('[data-interativo]')) return; // lá dentro as setas são dos chips
    const acao = { ArrowRight: 'AVANCAR', ArrowLeft: 'VOLTAR', ' ': 'ALTERNAR' }[e.key];
    if (acao) { e.preventDefault(); despachar({ tipo: acao }); }
  };

  return html`
    <div ref=${raiz} class=${`su-stories su-js st-player${parado ? ' pausado' : ''}`} tabindex="0" role="region"
      aria-roledescription="stories" aria-label=${rotulo} onKeyDown=${tecla}
      onPointerDown=${baixo} onPointerUp=${cima} onPointerCancel=${cancelar} onPointerLeave=${cancelar}>
      <div class="st-barra vidro-ctrl" aria-hidden="true">
        ${slides.map((_, k) => html`<span class=${`st-seg${k < estado.i || (estado.fim && k === estado.i) ? ' feito' : ''}`}>${k === estado.i && !estado.fim && html`
          <i key=${`${estado.i}-${estado.volta}`} style=${{ animationPlayState: parado ? 'paused' : 'running' }}
            onAnimationEnd=${() => despachar({ tipo: 'TEMPO' })}></i>`}</span>`)}
      </div>
      <div class="st-controles">
        <span class="st-contador" aria-live="polite">${estado.i + 1}/${slides.length}</span>
        <button type="button" class="st-botao vidro-ctrl sr-only-foco" aria-label="Story anterior" onClick=${() => despachar({ tipo: 'VOLTAR' })}>‹</button>
        <button type="button" class="st-botao vidro-ctrl sr-only-foco" aria-label="Próximo story" onClick=${() => despachar({ tipo: 'AVANCAR' })}>›</button>
        <button type="button" class=${`st-botao st-pausa vidro-ctrl${parado ? ' parado' : ''}`} aria-label=${parado ? 'Continuar' : 'Pausar'}
          onClick=${() => despachar({ tipo: estado.fim ? 'REPLAY' : 'ALTERNAR' })}></button>
      </div>
      <div class="su-stories-frame">
        ${slides.map((s, k) => html`<div class=${`st-slot${k === estado.i ? ' ativo' : ''}`} hidden=${k !== estado.i} key=${s.tipo}>${s.render({ ativo: k === estado.i, i: k, replay, controle })}</div>`)}
      </div>
    </div>`;
}
