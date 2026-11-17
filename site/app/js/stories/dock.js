// Dock dos stories: uma cápsula de vidro fixa na base enquanto o player está na tela e o modo está ativo.
// Mostra o trecho tocando (capa do iTunes nítida, música e artista, equalizador), o mudo e "Baixar pôster".
// O estado do som vem de som.js (useSom); quem desenha o pôster é a tela de cada modo (aoPoster).
import { html, useContext, useEffect, useState } from 'preact-htm';
import { definirMudo, ICONE, useSom } from '../som.js';
import { luzAmbiente } from './slides.js';
import { TelaAtiva } from './player.js';

// O player está pelo menos 30% visível? Fora disso o dock some (não cobre o resto da página).
function useNaTela(alvo) {
  const [visivel, setVisivel] = useState(false);
  useEffect(() => {
    const el = alvo.current?.querySelector('.st-player');
    if (!el) return undefined;
    const obs = new IntersectionObserver(([e]) => setVisivel(e.isIntersecting), { threshold: 0.3 });
    obs.observe(el);
    return () => obs.disconnect();
  }, [alvo.current]);
  return visivel;
}

export function Dock({ alvo, aoPoster, ocupado = false, comSom = false }) {
  const ativo = useContext(TelaAtiva);
  const naTela = useNaTela(alvo);
  const { trecho, tocando, mudo } = useSom();
  const visivel = ativo && naTela;
  const t = comSom ? trecho : null;
  return html`
    <div class=${`dock vidro${visivel ? ' visivel' : ''}${t ? ' com-trecho' : ''}`} role="region" aria-label="Controles dos stories" inert=${!visivel}>
      ${t && html`
        <img class="dock-capa" src=${t.capa} alt="" width="100" height="100" crossorigin="anonymous" onLoad=${(e) => luzAmbiente(e.target)} />
        <span class="dock-faixa"><b>${t.faixa}</b><small>${t.artista} · trecho de 30 s</small></span>
        <span class=${`eq${tocando && !mudo ? ' tocando' : ''}`} aria-hidden="true"><i></i><i></i><i></i><i></i></span>`}
      ${comSom && html`
        <button type="button" class="dock-mudo" aria-pressed=${mudo} aria-label=${mudo ? 'Ligar o som' : 'Silenciar'}
          onClick=${() => definirMudo(!mudo)}>${mudo ? ICONE.mudo : ICONE.som}</button>`}
      <button type="button" class="btn btn-verde dock-poster" onClick=${aoPoster} disabled=${ocupado}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4v11" /><path d="m7 10 5 5 5-5" /><path d="M5 20h14" /></svg>
        ${ocupado ? 'Gerando…' : 'Baixar pôster'}</button>
    </div>`;
}
