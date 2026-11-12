// Trilha dos stories do Wrapped: trechos de 30 s do iTunes tocando enquanto os slides passam.
// Um único <audio>, desbloqueado pelo toque em "Começar com som" (validado no iPhone),
// troca de src sozinho. Volume por Web Audio: no iOS o audio.volume é ignorado.
import { html, useEffect, useRef, useState } from 'preact-htm';
import { HOSTS_AUDIO, urlSegura } from './capas.js';
import { normalizar } from './stories/logica.js';

const VOLUME = 0.2;
const ENTRA = 1.2; // segundos de fade in
const SAI = 0.5; // fade out antes de trocar de música (e no fim do trecho)
// Para históricos fictícios (o iTunes não acha "Artista fictício"): trechos de exemplo.
const EXEMPLO = [{ artista: 'Legião Urbana', faixa: 'Tempo Perdido' }, { artista: 'Tim Maia', faixa: 'Azul da Cor do Mar' }, { artista: 'Marisa Monte', faixa: 'Ainda Bem' }];
const cache = new Map();

const chave = (m) => `${normalizar(m.artista)}|${normalizar(m.faixa)}`;

async function itunes(params) {
  const r = await fetch(`https://itunes.apple.com/search?${new URLSearchParams({ entity: 'song', country: 'BR', ...params })}`);
  if (!r.ok) throw new Error(`iTunes ${r.status}`);
  return (await r.json()).results || [];
}
// Trecho = { url, id }; o id (artista|faixa do iTunes) evita tocar a mesma música duas vezes.
const trecho = (x) => ({ url: urlSegura(x.previewUrl, HOSTS_AUDIO), id: `${normalizar(x.artistName)}|${normalizar(x.trackName)}` });
const doArtista = (x, nome) => urlSegura(x.previewUrl, HOSTS_AUDIO) && normalizar(x.artistName).includes(normalizar(nome));

// shortcut: casa só pelo artista; o casamento completo (faixa, remaster, feat.) vem na Fase 3.
async function buscar(m) {
  const k = `m:${chave(m)}`;
  if (!cache.has(k)) {
    const item = (await itunes({ term: `${m.artista} ${m.faixa}`, limit: '5' })).find((x) => doArtista(x, m.artista));
    cache.set(k, item ? [trecho(item)] : []);
  }
  return cache.get(k);
}

// As mais famosas do artista, na ordem de relevância do iTunes, sem repetir a mesma faixa.
async function famosas(nome) {
  const k = `a:${normalizar(nome)}`;
  if (!cache.has(k)) {
    const vistos = new Set();
    const lista = (await itunes({ term: nome, attribute: 'artistTerm', limit: '15' }))
      .filter((x) => doArtista(x, nome)).map(trecho).filter((t) => !vistos.has(t.id) && vistos.add(t.id));
    cache.set(k, lista);
  }
  return cache.get(k);
}
const resolver = (c) => (c.faixa ? buscar(c) : famosas(c.artista)).catch(() => []);

// 0,2 s de silêncio em WAV: o play() dentro do toque desbloqueia o elemento. Criado uma vez só.
let urlSilencio = null;
function silencio() {
  if (urlSilencio) return urlSilencio;
  const n = 1600, b = new DataView(new ArrayBuffer(44 + n));
  const txt = (o, s) => [...s].forEach((c, i) => b.setUint8(o + i, c.charCodeAt(0)));
  txt(0, 'RIFF'); b.setUint32(4, 36 + n, true); txt(8, 'WAVEfmt '); b.setUint32(16, 16, true);
  b.setUint16(20, 1, true); b.setUint16(22, 1, true); b.setUint32(24, 8000, true); b.setUint32(28, 8000, true);
  b.setUint16(32, 1, true); b.setUint16(34, 8, true); txt(36, 'data'); b.setUint32(40, n, true);
  for (let i = 0; i < n; i++) b.setUint8(44 + i, 128);
  return (urlSilencio = URL.createObjectURL(new Blob([b], { type: 'audio/wav' })));
}

// Um só <audio> e um só AudioContext para a página toda: o iOS limita os contextos e
// um elemento novo precisaria de outro toque. Criados no primeiro "Começar com som".
let som = null;
function prepararSom() {
  if (!som) {
    const el = new Audio();
    el.crossOrigin = 'anonymous'; // o iTunes manda CORS *: o Web Audio pode ler o trecho
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const ganho = ctx.createGain(); ganho.gain.value = 0;
    ctx.createMediaElementSource(el).connect(ganho).connect(ctx.destination);
    som = { el, ctx, ganho };
  }
  return som;
}

// Chamado dentro do toque em "Montar meu Wrapped" (antes de qualquer await): o iPhone só deixa tocar
// som que foi destravado por um toque. Depois, os stories começam com capas e som sem pedir outro toque.
export function destravarSom() {
  const { el, ctx, ganho } = prepararSom();
  ganho.gain.cancelScheduledValues(ctx.currentTime); ganho.gain.value = 0;
  el.src = silencio(); el.play().catch(() => { /* bloqueado: a busca segue e o botão "Ligar" aparece se falhar */ });
  ctx.resume();
}

export function SomStories({ trilha, alvo, aoLigar }) {
  const trilhaPronta = useRef(null);
  const [status, setStatus] = useState('');
  const [estado, setEstado] = useState('carregando'); // carregando | tocando | sem (o Wrapped começa sempre com capas e som)
  const [mudo, setMudo] = useState(false);
  const mudoAgora = useRef(false); // lido pelos ouvintes do player, que não re-renderizam
  mudoAgora.current = mudo;
  const raiz = () => alvo.current?.querySelector('.st-player');
  const [aviso, setAviso] = useState('');

  const rampa = (valor, segundos = ENTRA) => {
    const m = som; if (!m) return;
    const t = m.ctx.currentTime;
    m.ganho.gain.cancelScheduledValues(t); m.ganho.gain.setValueAtTime(m.ganho.gain.value, t);
    m.ganho.gain.linearRampToValueAtTime(valor, t + segundos);
  };
  // play() rejeita com AbortError quando o slide troca rápido: não é falha de som.
  // Bloqueado: volta para "sem", cujo botão "Ligar capas e som" destrava de novo dentro de um toque.
  const tocar = (el) => el.play().catch((e) => { if (e.name !== 'AbortError') { setEstado('sem'); setAviso('O navegador bloqueou o som. Toque em “Ligar capas e som” para tentar de novo.'); } });

  // Qualquer erro na busca vira "sem som", nunca um "Buscando…" eterno.
  // Um toque só: liga as capas (opt-in) e desbloqueia o áudio.
  const comecar = () => { aoLigar?.(); return iniciarSom().catch(() => { setEstado('sem'); setAviso('Não deu para preparar o som. Os stories seguem sem som.'); }); };
  useEffect(() => { comecar(); }, []); // começa sozinho: o áudio já foi destravado no toque em "Montar"
  const iniciarSom = async () => {
    destravarSom(); // no botão "Ligar", dentro do toque e antes de qualquer await
    setEstado('carregando'); setAviso('');
    const porSlide = Object.fromEntries(await Promise.all(Object.entries(trilha.slides).map(
      async ([tipo, candidatas]) => [tipo, (await Promise.all(candidatas.map(resolver))).flat()])));
    // Intercala: a 1ª de cada candidata, depois a 2ª… (não esgota um artista antes do próximo).
    const listas = await Promise.all(trilha.fila.map(resolver));
    let fila = Array.from({ length: Math.max(0, ...listas.map((l) => l.length)) }, (_, i) => listas.map((l) => l[i])).flat().filter(Boolean);
    if (!fila.length && !Object.values(porSlide).some((l) => l.length)) {
      fila = (await Promise.all(EXEMPLO.map(resolver))).flat();
      if (fila.length) setAviso('Não achamos estas músicas no iTunes (histórico fictício?). Tocando trechos de exemplo.');
    }
    if (!fila.length && !Object.values(porSlide).some((l) => l.length)) { setEstado('sem'); setAviso('Não deu para buscar os trechos (sem internet?). Os stories seguem sem som.'); return; }
    trilhaPronta.current = { fila, porSlide };
    setEstado('tocando');
    raiz()?.dispatchEvent(new Event('st-replay')); // recomeça do primeiro slide, já com som
    raiz()?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  // Uma música por story: cada slide tem a sua (a própria do slide ou a próxima das mais ouvidas).
  // Troca com fade out → novo trecho do início → fade in. Pausar os stories pausa o som.
  useEffect(() => {
    const stories = raiz();
    if (estado !== 'tocando' || !stories) return undefined;
    const { el } = som;
    const { fila, porSlide } = trilhaPronta.current;
    const slides = [...stories.querySelectorAll('.st-slot .su-story')];
    const slots = [...stories.querySelectorAll('.st-slot')];
    // Cada story: a 1ª candidata do seu dado que ainda não tocou; senão, a próxima das mais ouvidas.
    const tocadas = new Set();
    const livre = (lista) => lista.find((t) => !tocadas.has(t.id));
    const musicas = slides.map((slide) => {
      const tipo = [...slide.classList].find((c) => c.startsWith('s-'))?.slice(2);
      const t = livre(porSlide[tipo] || []) || livre(fila) || fila[tocadas.size % (fila.length || 1)];
      if (!t) return null; // sem trecho: este story fica em silêncio
      tocadas.add(t.id);
      slide.dataset.trecho = t.id; // qual música tocou neste story (conferível no DOM)
      return t.url;
    });
    const volume = () => (mudoAgora.current ? 0 : VOLUME);
    let atual = -1, troca = 0, tentou = false;
    const trocar = (url) => {
      const minha = ++troca; // um toque rápido em vários slides cancela as trocas antigas
      const comecarNova = () => { if (minha !== troca) return; tentou = false; el.src = url; tocar(el); rampa(volume()); };
      if (!url) { rampa(0, SAI); return; }
      if (el.paused || el.src.startsWith('blob:')) comecarNova();
      else { rampa(0, SAI); setTimeout(comecarNova, SAI * 1000); }
    };
    const aoMudar = () => {
      if (stories.classList.contains('pausado')) { el.pause(); return; }
      const i = slots.findIndex((sl) => sl.classList.contains('ativo'));
      if (i < 0) return;
      if (i !== atual) { atual = i; trocar(musicas[i]); } else if (el.paused && !el.src.startsWith('blob:')) { tocar(el); rampa(volume()); }
    };
    // Fade out no fim do trecho de 30 s, em vez de cortar seco.
    const fim = () => { if (el.duration && el.duration - el.currentTime < SAI + 0.3) rampa(0, SAI); };
    // Linha de status (diagnóstico no celular) e uma nova tentativa se o trecho falhar ao carregar.
    const tocando = () => setStatus(`♪ Story ${atual + 1} de ${slides.length}: tocando`);
    const erro = () => {
      if (!tentou && musicas[atual]) { tentou = true; el.src = musicas[atual]; tocar(el); setStatus(`Story ${atual + 1}: tentando de novo…`); }
      else setStatus(`Story ${atual + 1}: este trecho não carregou`);
    };
    const obs = new MutationObserver(aoMudar);
    obs.observe(stories, { attributes: true, attributeFilter: ['class'], subtree: true });
    el.addEventListener('timeupdate', fim);
    el.addEventListener('playing', tocando);
    el.addEventListener('error', erro);
    aoMudar();
    return () => {
      troca++; obs.disconnect(); el.pause();
      el.removeEventListener('timeupdate', fim); el.removeEventListener('playing', tocando); el.removeEventListener('error', erro);
    };
  }, [estado]);

  useEffect(() => { if (estado === 'tocando') rampa(mudo ? 0 : VOLUME); }, [mudo]);

  return html`
    <div class="som-stories vidro">
      <div class="acoes">${estado === 'sem'
        ? html`<button type="button" class="btn btn-verde" onClick=${comecar}>♪ Ligar capas e som</button>`
        : html`<button type="button" class="btn btn-borda vidro" aria-pressed=${mudo} disabled=${estado !== 'tocando'} onClick=${() => setMudo((m) => !m)}>
            ${estado === 'carregando' ? 'Buscando capas e trechos…' : mudo ? '🔇 Ligar som' : '🔊 Silenciar'}</button>`}
      </div>
      <p class="nota">Para as capas e o som, o SyncUp envia os códigos das suas músicas mais ouvidas para o Spotify, o nome dos seus artistas para o MusicBrainz e os nomes das músicas para a Apple (iTunes), além do seu endereço IP. O histórico e o seu nome não saem do aparelho. Capas e fotos: Spotify · Trechos: iTunes.</p>
      ${aviso && html`<p class="nota" role="status">${aviso}</p>`}
      ${estado === 'tocando' && status && html`<p class="nota">${status}</p>`}
    </div>`;
}
