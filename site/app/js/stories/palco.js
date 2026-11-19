// Palco dos stories: no computador (≥ 1240 px, ver app.css), três colunas como no Spotify:
// a fila dos stories à esquerda, o player no meio e "Tocando agora" à direita. Abaixo disso, uma coluna só:
// o player e, embaixo, o que vai em `lado` (som e botões de cada tela), como antes.
// `lado` fica sempre montado nos dois tamanhos: redimensionar a janela não reinicia a música nem a trilha.
import { html, useContext, useEffect, useState } from 'preact-htm';
import { definirMudo, ICONE, useSom } from '../som.js';
import { TelaAtiva } from './player.js';

// Títulos curtos da fila. Os slides da Batalha e do Match trazem `titulo` próprio (a rodada, o par).
const TITULOS = {
  abertura: 'Abertura', em_comum: 'O que une vocês', frente: 'Frente a frente', apresentar: 'Quem apresentou o quê',
  relogios: 'Quando cada um ouve', sintonia: 'Em sintonia', sintonia_musica: 'A música em sintonia', poster: 'Pôster',
  intro: 'Sua vida em música', primeira: 'A primeira música', artista: 'Artista do coração', top_artistas: 'Top artistas',
  top_musicas: 'Top músicas', trilha: 'Sua trilha', anos: 'Ano a ano', descobertas: 'Descobertas', recorde: 'O dia recorde',
  relogio: 'Seu relógio', maratona: 'Maratona', fiel: 'Fiel', habitos: 'Hábitos', arquetipo: 'Seu arquétipo', resumo: 'Resumo',
  afinada: 'A dupla mais afinada', medalhas: 'Quadro de medalhas', podio: 'Pódio',
};
export const tituloStory = (s) => s.titulo || TITULOS[s.tipo] || s.tipo;

// Índice do story na tela, lido das classes do player (o mesmo sinal que o som.js usa).
function useAtual(alvo) {
  const [i, setI] = useState(0);
  useEffect(() => {
    const el = alvo.current?.querySelector('.st-player');
    if (!el) return undefined;
    const ler = () => setI(Math.max(0, [...el.querySelectorAll('.st-slot')].findIndex((s) => s.classList.contains('ativo'))));
    const obs = new MutationObserver(ler);
    obs.observe(el, { attributes: true, attributeFilter: ['class'], subtree: true });
    ler();
    return () => obs.disconnect();
  }, [alvo.current]);
  return i;
}

// A capa de 100 px do iTunes vem em tamanho maior trocando o sufixo (mesmo host, já conferido por urlSegura).
const capaGrande = (url) => url?.replace(/\/\d+x\d+bb\./, '/600x600bb.');

function Agora({ titulo, comSom }) {
  const { trecho, tocando, mudo } = useSom();
  const t = comSom ? trecho : null;
  return html`<div class="palco-agora superficie">
    <p class="palco-rotulo">Tocando agora</p>
    ${t ? html`<img class="palco-capa" src=${capaGrande(t.capa)} alt="" width="600" height="600" crossorigin="anonymous" />`
      : html`<div class="palco-capa vazia" aria-hidden="true">${ICONE.nota}</div>`}
    <div class="palco-faixa">
      <b>${t ? t.faixa : titulo}</b>
      <small>${t ? `${t.artista} · trecho de 30 s` : comSom ? 'Preparando o som…' : 'Stories sem som'}</small>
    </div>
    ${t && html`<span key=${t.url} class=${`dock-progresso palco-progresso${tocando ? '' : ' parado'}`} aria-hidden="true"><i></i></span>`}
    ${comSom && html`<button type="button" class="palco-mudo btn btn-borda superficie" aria-pressed=${mudo} onClick=${() => definirMudo(!mudo)}>
      ${mudo ? ICONE.mudo : ICONE.som}${mudo ? 'Ligar o som' : 'Silenciar'}</button>`}
  </div>`;
}

export function Palco({ alvo, slides, comSom = false, lado = null, children }) {
  const atual = useAtual(alvo);
  const ativa = useContext(TelaAtiva);
  const ir = (k) => alvo.current?.querySelector('.st-player')?.dispatchEvent(new CustomEvent('st-ir', { detail: k }));
  return html`<div class="st-palco">
    <nav class="palco-fila" aria-label="Fila dos stories">
      <p class="palco-rotulo">Fila</p>
      <ol>${slides.map((s, k) => html`<li><button type="button" class=${k === atual ? 'atual' : ''} aria-current=${k === atual ? 'step' : null} onClick=${() => ir(k)} tabindex=${ativa ? 0 : -1}>
        <span class="palco-n">${k === atual ? html`<span class="eq tocando" aria-hidden="true"><i></i><i></i><i></i><i></i></span>` : k + 1}</span>
        <span class="palco-titulo">${tituloStory(s)}</span></button></li>`)}</ol>
    </nav>
    <div ref=${alvo} class="nucleo">${children}</div>
    <aside class="palco-lado" aria-label="Som e ações dos stories">
      <${Agora} titulo=${tituloStory(slides[atual] || slides[0])} comSom=${comSom} />
      ${lado}
    </aside>
  </div>`;
}
