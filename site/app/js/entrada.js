// Entrada no app vindo de "Abrir o app" (1.25): a logo entra em sintonia e pousa no lugar dela.
//   1. Fora de sintonia (CSS, app.css): a logo grande no centro, cada barra no seu ritmo, enquanto o app carrega.
//   2. Em sintonia: com o app pronto, as 4 barras param juntas, do ponto em que estavam, no formato da logo.
//   3. Pouso: a logo voa até a logo do app (FLIP) e o app aparece em volta durante o voo; no pouso ela vira a de verdade.
// Uma coisa principal por vez, sempre na curva do projeto (--sai). Só transform e opacity (WAAPI).
// Se este script falhar, o CSS mostra o app e some com a logo sozinho em 3,2 s.
const MINIMO_MS = 450; // o "fora de sintonia" precisa ser visto
const LIMITE_MS = 3000; // antes do resgate do CSS (3,2 s)
const SINTONIA_MS = 260;
const VOO_MS = 520; // raro (uma vez por visita) e cruza a tela: pode passar dos 300 ms de UI
const APP_MS = 320;
const SAI = 'cubic-bezier(.16, 1, .3, 1)'; // = --sai (estilo.css)
// ?lento=1: tudo 4x mais devagar, para conferir quadro a quadro (só desenvolvimento, como o ?fps=1).
const LENTO = new URLSearchParams(location.search).get('lento') === '1' ? 4 : 1;
const ms = (n) => n * LENTO;


// A logo do app que está na tela: a da lateral (computador) ou a do topo (celular).
// Não vale a do esqueleto de carregamento (ela some quando o app desenha).
const logoDoApp = () => [...document.querySelectorAll('#app .nav-app .marca .logo, #app .app-topo .marca .logo')].find((l) => l.getClientRects().length);

function pronto() {
  return new Promise((ok) => {
    if (logoDoApp()) return ok(logoDoApp());
    const obs = new MutationObserver(() => { const l = logoDoApp(); if (l) { obs.disconnect(); ok(l); } });
    obs.observe(document.getElementById('app'), { childList: true, subtree: true });
    setTimeout(() => { obs.disconnect(); ok(logoDoApp()); }, LIMITE_MS);
  });
}

// O app aparece e sobe 8 px. `backwards` segura a opacidade 0 até a hora; no fim não sobra transform no #app
// (prenderia os elementos fixed dos stories). .chegou faz o CSS deixar de esconder o app.
function mostrarApp(atraso) {
  document.getElementById('app').animate([{ opacity: 0, translate: '0 8px' }, { opacity: 1, translate: '0 0' }],
    { duration: ms(APP_MS), delay: atraso, easing: SAI, fill: 'backwards' });
  document.body.classList.add('chegou');
}

function terminar(raiz) {
  raiz.remove();
  document.body.classList.add('sintonizado'); // a logo do app passa a pulsar com as barras juntas
  document.body.classList.remove('entrando', 'chegou');
}

async function entrar(raiz) {
  // O script assumiu: desliga o resgate do CSS (3,2 s), que cortaria a logo no meio do voo com rede lenta.
  raiz.style.animation = 'none';
  document.getElementById('app').style.animation = 'none';
  if (LENTO > 1) for (const i of raiz.querySelectorAll('i')) i.style.animationDuration = `${parseFloat(getComputedStyle(i).getPropertyValue('--ritmo')) * LENTO}s`;
  const [alvo] = await Promise.all([pronto(), new Promise((ok) => setTimeout(ok, ms(MINIMO_MS)))]);
  const marca = raiz.querySelector('.pouso-marca');
  if (!alvo || document.hidden) {
    mostrarApp(0);
    await marca.animate([{ opacity: 1 }, { opacity: 0 }], { duration: ms(200), fill: 'forwards' }).finished;
    return terminar(raiz);
  }

  // 2. Em sintonia: cada barra sai da altura em que está (sem salto) e todas chegam juntas ao formato da logo.
  for (const barra of marca.querySelectorAll('i')) {
    const agora = getComputedStyle(barra).transform;
    barra.style.animation = 'none';
    barra.animate([{ transform: agora === 'none' ? 'scaleY(1)' : agora }, { transform: 'scaleY(1)' }], { duration: ms(SINTONIA_MS), easing: SAI, fill: 'forwards' });
  }

  // 3. Pouso: começa um pouco antes da sintonia terminar (um gesto só, não uma fila). O voo é medido na hora,
  // porque a logo do app fica na lateral no computador e no topo no celular.
  // Move as barras (.logo), não o contêiner: o centro medido é o mesmo que o centro da escala.
  const logo = marca.querySelector('.logo');
  // A logo do app é buscada de novo: o Preact pode ter redesenhado o topo e trocado o elemento (o antigo mede 0×0).
  const destino = logoDoApp() ?? alvo;
  const de = logo.getBoundingClientRect(), para = destino.getBoundingClientRect();
  if (!para.height) { mostrarApp(0); return terminar(raiz); }
  const dx = para.left + para.width / 2 - (de.left + de.width / 2);
  const dy = para.top + para.height / 2 - (de.top + de.height / 2);
  const voo = logo.animate([{ transform: 'none' }, { transform: `translate(${dx}px, ${dy}px) scale(${para.height / de.height})` }],
    { duration: ms(VOO_MS), delay: ms(SINTONIA_MS - 60), easing: SAI, fill: 'forwards' });
  mostrarApp(ms(SINTONIA_MS + 120)); // o app aparece em volta enquanto a logo ainda voa
  await voo.finished;
  terminar(raiz);
}

// Dispara no fim do arquivo: as funções acima já existem (const não é içada).
const raiz = document.querySelector('.pouso');
if (raiz && document.body.classList.contains('entrando') && !matchMedia('(prefers-reduced-motion: reduce)').matches) entrar(raiz);
else { raiz?.remove(); setTimeout(() => document.body.classList.remove('entrando'), 300); }
