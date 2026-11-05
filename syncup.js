() => {
  /* SyncUp · animações da interface (tema Spotify).
     Executado uma vez no carregamento pelo parâmetro js= do gr.Blocks.
     Tudo é progressivo: sem este script, os valores finais já estão no HTML. */
  if (window.__syncup) return;
  window.__syncup = true;

  const reduz = window.matchMedia('(prefers-reduced-motion: reduce)');
  const semMovimento = () => reduz.matches;
  const fmt = (v, casas) =>
    v.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
  const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
  const nomeMes = (iso) => {
    const [a, m] = iso.split('-');
    return `${MESES[Number(m) - 1]}/${a}`;
  };

  /* ---------- Ondas (ripple) em todos os botões ---------- */
  document.addEventListener(
    'pointerdown',
    (ev) => {
      const botao = ev.target.closest('button, .su-race-play');
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
    },
    { passive: true }
  );

  /* ---------- Contagem animada dos números ---------- */
  const contar = (el) => {
    if (el.dataset.suDone === el.dataset.countup) return;
    el.dataset.suDone = el.dataset.countup;
    const alvo = Number(el.dataset.countup);
    const casas = Number(el.dataset.decimals || 0);
    const sufixo = el.dataset.suffix || '';
    if (!Number.isFinite(alvo) || semMovimento()) {
      el.textContent = fmt(alvo, casas) + sufixo;
      return;
    }
    const duracao = 1400;
    const inicio = performance.now();
    const passo = (agora) => {
      const t = Math.min(1, (agora - inicio) / duracao);
      const e = 1 - Math.pow(1 - t, 4);
      el.textContent = fmt(alvo * e, casas) + sufixo;
      if (t < 1) requestAnimationFrame(passo);
    };
    requestAnimationFrame(passo);
  };

  /* ---------- Corrida de artistas (bar chart race) ---------- */
  const montarCorrida = (raiz) => {
    let dados;
    try {
      dados = JSON.parse(raiz.dataset.race);
    } catch (e) {
      return;
    }
    raiz.dataset.suRaceReady = '1';
    const topo = dados.topo || 8;
    const altura = 46;
    raiz.innerHTML = '';
    const pistas = document.createElement('div');
    pistas.className = 'su-race-lanes';
    const estados = dados.perfis.map((perfil) => {
      const pista = document.createElement('div');
      pista.className = 'su-race-lane';
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
      <div class="su-race-progress" role="slider" tabindex="0" aria-label="Mês da corrida"><div class="su-race-fill"></div><div class="su-race-knob"></div></div>
      <span class="su-race-time su-race-end">${nomeMes(dados.meses[dados.meses.length - 1])}</span>`;
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
    progresso.addEventListener('pointerdown', (ev) => {
      parar();
      buscar(ev);
      const mover = (e) => buscar(e);
      window.addEventListener('pointermove', mover);
      window.addEventListener('pointerup', () => window.removeEventListener('pointermove', mover), {
        once: true,
      });
    });
    progresso.addEventListener('keydown', (ev) => {
      if (ev.key === 'ArrowRight') desenhar(quadro + 1);
      if (ev.key === 'ArrowLeft') desenhar(quadro - 1);
    });
    raiz.__suPlay = () => {
      if (semMovimento()) return desenhar(total - 1);
      desenhar(0);
      tocar();
    };
    desenhar(semMovimento() ? total - 1 : 0);
  };


  /* ---------- Stories do Wrapped ---------- */
  const DURACAO_STORY = 7000;
  const montarStories = (raiz) => {
    if (raiz.dataset.suStoriesReady) return;
    raiz.dataset.suStoriesReady = '1';
    const slides = [...raiz.querySelectorAll('.su-story')];
    if (!slides.length) return;
    raiz.classList.add('su-js');
    raiz.style.setProperty('--story-dur', `${DURACAO_STORY}ms`);
    const barra = document.createElement('div');
    barra.className = 'su-stories-bar';
    const segmentos = slides.map(() => {
      const seg = document.createElement('span');
      seg.className = 'su-seg';
      seg.append(document.createElement('i'));
      barra.append(seg);
      return seg;
    });
    const voltar = document.createElement('button');
    voltar.type = 'button';
    voltar.className = 'su-tap prev';
    voltar.setAttribute('aria-label', 'Slide anterior');
    const avancar = document.createElement('button');
    avancar.type = 'button';
    avancar.className = 'su-tap next';
    avancar.setAttribute('aria-label', 'Próximo slide');
    const pausa = document.createElement('button');
    pausa.type = 'button';
    pausa.className = 'su-story-pause';
    pausa.setAttribute('aria-label', 'Pausar');
    const contador = document.createElement('span');
    contador.className = 'su-story-count';
    raiz.append(barra, voltar, avancar, pausa, contador);
    let atual = -1;
    let pausado = semMovimento();
    const marcarPausa = () => {
      raiz.classList.toggle('pausado', pausado);
      pausa.setAttribute('aria-label', pausado ? 'Continuar' : 'Pausar');
    };
    const ir = (i) => {
      const alvo = Math.max(0, Math.min(slides.length - 1, i));
      atual = alvo;
      slides.forEach((s, k) => s.classList.toggle('ativo', k === alvo));
      segmentos.forEach((seg, k) => {
        seg.classList.toggle('feito', k < alvo);
        seg.classList.remove('ativo');
      });
      void barra.offsetWidth; // reinicia a animação do segmento atual
      segmentos[alvo].classList.add('ativo');
      contador.textContent = `${alvo + 1}/${slides.length}`;
      for (const el of slides[alvo].querySelectorAll('[data-countup]')) {
        delete el.dataset.suDone;
        if (semMovimento()) contar(el);
      }
    };
    segmentos.forEach((seg) =>
      seg.querySelector('i').addEventListener('animationend', () => {
        if (seg.classList.contains('ativo') && atual < slides.length - 1) ir(atual + 1);
      })
    );
    voltar.addEventListener('click', () => ir(atual - 1));
    avancar.addEventListener('click', () => ir(atual + 1));
    pausa.addEventListener('click', () => {
      pausado = !pausado;
      marcarPausa();
    });
    raiz.addEventListener('keydown', (ev) => {
      if (ev.key === 'ArrowRight') ir(atual + 1);
      else if (ev.key === 'ArrowLeft') ir(atual - 1);
      else if (ev.key === ' ') {
        ev.preventDefault();
        pausado = !pausado;
        marcarPausa();
      } else return;
      ev.preventDefault();
    });
    const replay = raiz.querySelector('.su-replay');
    if (replay) replay.addEventListener('click', () => ir(0));
    marcarPausa();
    raiz.__suPlay = () => ir(0);
    ir(0);
  };

  /* ---------- Disparo quando o elemento fica visível ---------- */
  const observador = new IntersectionObserver(
    (entradas) => {
      for (const entrada of entradas) {
        if (!entrada.isIntersecting) continue;
        const el = entrada.target;
        if (el.matches('[data-countup]')) contar(el);
        if (el.matches('[data-stories]') && !el.dataset.suPlayed) {
          el.dataset.suPlayed = '1';
          if (el.__suPlay) el.__suPlay();
        }
        if (el.matches('.su-race') && !el.dataset.suPlayed) {
          el.dataset.suPlayed = '1';
          setTimeout(() => el.__suPlay && el.__suPlay(), 350);
        }
      }
    },
    { threshold: 0.25 }
  );

  const registrar = (raiz) => {
    if (!(raiz instanceof Element)) return;
    // O Gradio escreve este rótulo em inglês, sem tradução.
    for (const b of [raiz, ...raiz.querySelectorAll('[aria-label="More tabs"]')]) {
      if (b.getAttribute('aria-label') === 'More tabs') b.setAttribute('aria-label', 'Mais abas');
    }
    const alvos = raiz.matches('[data-countup], .su-race, [data-stories]') ? [raiz] : [];
    alvos.push(...raiz.querySelectorAll('[data-countup], .su-race, [data-stories]'));
    for (const el of alvos) {
      if (el.matches('.su-race') && el.dataset.race && !el.dataset.suRaceReady) montarCorrida(el);
      if (el.matches('[data-stories]')) montarStories(el);
      observador.unobserve(el);
      observador.observe(el);
    }
  };

  new MutationObserver((mudancas) => {
    for (const m of mudancas) for (const n of m.addedNodes) registrar(n);
  }).observe(document.body, { childList: true, subtree: true });
  registrar(document.body);
}
