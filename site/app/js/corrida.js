// Corrida dos artistas e onda nos botões: o mesmo do syncup.js (app para PC), como módulo do app web.
// Sem MutationObserver: quem a desenha liga ao montar e desliga ao desmontar (ligarCorrida).
import { MESES } from './stories/logica.js';

const reduz = matchMedia('(prefers-reduced-motion: reduce)');
const semMovimento = () => reduz.matches;
const fmt = (v, casas) => v.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
const nomeMes = (iso) => {
  const [a, m] = iso.split('-');
  return `${MESES[Number(m) - 1]}/${a}`;
};

// Onda ao tocar em qualquer botão. Chamar uma vez.
export function ligarOndas() {
  document.addEventListener('pointerdown', (ev) => {
    const botao = ev.target.closest?.('button, .su-race-play');
    if (!botao || semMovimento()) return;
    const caixa = botao.getBoundingClientRect();
    const tamanho = Math.max(caixa.width, caixa.height) * 2;
    const onda = document.createElement('span');
    onda.className = 'su-ripple';
    onda.style.width = onda.style.height = `${tamanho}px`;
    onda.style.left = `${ev.clientX - caixa.left - tamanho / 2}px`;
    onda.style.top = `${ev.clientY - caixa.top - tamanho / 2}px`;
    botao.classList.add('su-has-ripple');
    botao.appendChild(onda);
    onda.addEventListener('animationend', () => onda.remove(), { once: true });
  }, { passive: true });
}

function montarCorrida(raiz) {
  let dados;
  try {
    dados = JSON.parse(raiz.dataset.race);
  } catch {
    return null;
  }
  raiz.dataset.suRaceReady = '1';
  const topo = dados.topo || 8;
  const altura = 46;
  raiz.innerHTML = '';
  const pistas = document.createElement('div');
  pistas.className = 'su-race-lanes';
  const estados = dados.perfis.map((perfil) => {
    const pista = document.createElement('div');
    pista.style.setProperty('--accent', perfil.cor);
    const titulo = document.createElement('div');
    titulo.className = 'su-race-title';
    titulo.innerHTML = '<span class="su-dot"></span>';
    titulo.append(`${perfil.rotulo} · ${perfil.nome}`);
    const area = document.createElement('div');
    area.className = 'su-race-area';
    area.style.height = `${topo * altura}px`;
    const linhas = perfil.artistas.map((nome) => {
      const linha = document.createElement('div');
      linha.className = 'su-race-row';
      linha.style.height = `${altura - 8}px`;
      const posicao = document.createElement('span');
      posicao.className = 'su-race-rank';
      const barra = document.createElement('div');
      barra.className = 'su-race-bar';
      const rotulo = document.createElement('span');
      rotulo.className = 'su-race-name';
      rotulo.textContent = nome;
      const valor = document.createElement('span');
      valor.className = 'su-race-value';
      const trilho = document.createElement('div');
      trilho.className = 'su-race-trackbar';
      trilho.append(barra, valor);
      linha.append(posicao, rotulo, trilho);
      area.append(linha);
      return { linha, barra, valor, posicao };
    });
    pista.append(titulo, area);
    pistas.append(pista);
    return { perfil, linhas };
  });

  const player = document.createElement('div');
  player.className = 'su-race-player';
  player.innerHTML = `
    <button type="button" class="su-race-play" aria-label="Reproduzir corrida"><span class="su-icon-play"></span></button>
    <span class="su-race-time su-race-now"></span>
    <div class="su-race-progress" role="slider" tabindex="0" aria-label="Mês da corrida" aria-valuemin="0" aria-valuemax="${dados.meses.length - 1}"><div class="su-race-fill"></div><div class="su-race-knob"></div></div>
    <span class="su-race-time">${nomeMes(dados.meses[dados.meses.length - 1])}</span>`;
  const mesGrande = document.createElement('div');
  mesGrande.className = 'su-race-month';
  raiz.append(mesGrande, pistas, player);

  const botao = player.querySelector('.su-race-play');
  const icone = botao.querySelector('span');
  const progresso = player.querySelector('.su-race-progress');
  const preenchimento = player.querySelector('.su-race-fill');
  const pino = player.querySelector('.su-race-knob');
  const agora = player.querySelector('.su-race-now');
  const total = dados.meses.length;
  let quadro = 0;
  let timer = null;

  const desenhar = (i) => {
    quadro = Math.max(0, Math.min(total - 1, i));
    const pct = total > 1 ? (quadro / (total - 1)) * 100 : 100;
    preenchimento.style.width = `${pct}%`;
    pino.style.left = `${pct}%`;
    agora.textContent = nomeMes(dados.meses[quadro]);
    mesGrande.textContent = nomeMes(dados.meses[quadro]);
    progresso.setAttribute('aria-valuenow', String(quadro));
    progresso.setAttribute('aria-valuetext', nomeMes(dados.meses[quadro]));
    for (const { perfil, linhas } of estados) {
      const valores = perfil.valores.map((serie) => serie[quadro]);
      const ordem = valores
        .map((v, idx) => [v, idx])
        .filter(([v]) => v > 0)
        .sort((x, y) => y[0] - x[0] || perfil.artistas[x[1]].localeCompare(perfil.artistas[y[1]]));
      const maximo = ordem.length ? ordem[0][0] : 1;
      const posicoes = new Map(ordem.slice(0, topo).map(([, idx], r) => [idx, r]));
      linhas.forEach((l, idx) => {
        const r = posicoes.get(idx);
        const visivel = r !== undefined;
        l.linha.style.transform = `translateY(${(visivel ? r : topo) * altura}px)`;
        l.linha.style.opacity = visivel ? '1' : '0';
        l.barra.style.width = `${Math.max(1.5, (valores[idx] / maximo) * 86)}%`;
        l.valor.textContent = fmt(valores[idx], 0);
        l.posicao.textContent = visivel ? String(r + 1) : '';
      });
    }
  };
  const parar = () => {
    clearInterval(timer);
    timer = null;
    raiz.classList.remove('playing');
    icone.className = 'su-icon-play';
    botao.setAttribute('aria-label', 'Reproduzir corrida');
  };
  const tocar = () => {
    if (quadro >= total - 1) desenhar(0);
    raiz.classList.add('playing');
    icone.className = 'su-icon-pause';
    botao.setAttribute('aria-label', 'Pausar corrida');
    const intervalo = Math.max(140, Math.min(650, 16000 / total));
    raiz.style.setProperty('--race-step', `${intervalo}ms`);
    timer = setInterval(() => {
      if (quadro >= total - 1) return parar();
      desenhar(quadro + 1);
    }, intervalo);
  };
  botao.addEventListener('click', () => (timer ? parar() : tocar()));
  const buscar = (ev) => {
    const caixa = progresso.getBoundingClientRect();
    const t = Math.min(1, Math.max(0, (ev.clientX - caixa.left) / caixa.width));
    desenhar(Math.round(t * (total - 1)));
  };
  // Arraste com captura: pointermove fica no próprio trilho e qualquer fim (soltar, cancelar, perder a captura) encerra.
  progresso.addEventListener('pointerdown', (ev) => {
    parar();
    buscar(ev);
    progresso.setPointerCapture?.(ev.pointerId);
    progresso.addEventListener('pointermove', buscar);
  });
  const soltar = () => progresso.removeEventListener('pointermove', buscar);
  for (const fim of ['pointerup', 'pointercancel', 'lostpointercapture']) progresso.addEventListener(fim, soltar);
  // Teclas do padrão ARIA de slider; mexer pelo teclado pausa, como arrastar.
  const PASSOS = { ArrowRight: 1, ArrowUp: 1, ArrowLeft: -1, ArrowDown: -1, PageUp: 12, PageDown: -12 };
  progresso.addEventListener('keydown', (ev) => {
    const alvo = ev.key === 'Home' ? 0 : ev.key === 'End' ? total - 1 : ev.key in PASSOS ? quadro + PASSOS[ev.key] : null;
    if (alvo === null) return;
    ev.preventDefault();
    parar();
    desenhar(alvo);
  });
  raiz.__suPlay = () => {
    if (semMovimento()) return desenhar(total - 1);
    desenhar(0);
    tocar();
  };
  desenhar(semMovimento() ? total - 1 : 0);
  // Para de vez (sair da aba Gráficos ou trocar de resultado). Chamar de novo não faz nada.
  let desligada = false;
  return () => {
    if (desligada) return;
    desligada = true;
    raiz.__suPlay = null; // um início agendado pelo observador não toca mais
    parar();
    soltar();
    observador.unobserve(raiz); // o observador é de todas as corridas: só esta raiz sai
  };
}

// Começa sozinha quando um quarto dela aparece na tela, uma vez.
const observador = new IntersectionObserver((entradas) => {
  for (const { isIntersecting, target } of entradas) {
    if (!isIntersecting) continue;
    observador.unobserve(target);
    setTimeout(() => target.__suPlay?.(), 350);
  }
}, { threshold: 0.25 });

// Liga a corrida dentro de `el` (quem a desenha chama ao montar) e devolve como desligá-la (ao desmontar).
export function ligarCorrida(el) {
  const raiz = el?.querySelector('.su-race[data-race]');
  if (!raiz || raiz.dataset.suRaceReady) return undefined;
  const desligar = montarCorrida(raiz);
  if (desligar) observador.observe(raiz);
  return desligar;
}
