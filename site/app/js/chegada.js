// Chegadas: o que nasce na tela (resultado, avisos, arquivos) entra uma vez, com a curva do site.
// Por ref estável + WAAPI, e não @starting-style: os modos ficam em <div hidden>, e o CSS animaria
// tudo de novo a cada troca de modo. O Preact só chama o ref quando o elemento nasce.
const SAI = 'cubic-bezier(.16, 1, .3, 1)'; // o mesmo --sai do estilo.css
const entra = (de, duration, easing = SAI) => (el) => {
  // A WAAPI não obedece o "menos movimento" do CSS (estilo.css): a checagem fica aqui.
  if (!el || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  el.animate([de, {}], { duration, easing });
};
export const chegar = entra({ opacity: 0.6, translate: '0 12px' }, 400); // resultado
export const chegarPouco = entra({ opacity: 0, translate: '0 4px' }, 200); // avisos e erros
export const chegarLista = entra({ opacity: 0, scale: 0.97 }, 200); // arquivo aceito

// Rolagem até o resultado: o behavior 'smooth' do JS não obedece ao scroll-behavior do CSS.
export const rolarAte = (el, block = 'start') => el?.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block });

// Processando → resultado: o cartão "Lendo…" cresce até virar o player dos stories e os controles de vidro entram
// em cascata (tipo "resultado", app.css). A rolagem é seca dentro da troca: o quadro velho fica onde estava e o
// novo já no lugar, então o cartão "voa" até o palco. Sem suporte ou com "menos movimento": troca seca e rolagem.
// No fim, o foco vai para o player (o botão que a pessoa apertou ficou desabilitado durante a conta).
export function mostrarResultado(mudar, id) {
  const rolar = (behavior) => document.getElementById(id)?.scrollIntoView({ behavior, block: 'start' });
  const focar = () => document.getElementById(id)?.querySelector('.st-player')?.focus({ preventScroll: true });
  if (!document.startViewTransition || matchMedia('(prefers-reduced-motion: reduce)').matches) {
    mudar();
    setTimeout(() => { rolarAte(document.getElementById(id)); focar(); }); // como no update: espera o Preact desenhar
    return;
  }
  const update = async () => { mudar(); await new Promise((r) => setTimeout(r)); rolar('instant'); }; // espera o Preact desenhar
  let vt;
  try { vt = document.startViewTransition({ update, types: ['resultado'] }); } catch { vt = document.startViewTransition(update); }
  vt.ready.catch(() => {}); // aba em segundo plano: a troca acontece igual, sem animação
  vt.finished.finally(focar);
}
