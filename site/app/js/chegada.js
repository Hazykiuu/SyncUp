// Chegadas: o que nasce na tela (resultado, avisos, arquivos) entra uma vez, com a curva do site.
// Por ref estável + WAAPI, e não @starting-style: os modos ficam em <div hidden>, e o CSS animaria
// tudo de novo a cada troca de modo. O Preact só chama o ref quando o elemento nasce.
const SAI = 'cubic-bezier(.22, 1, .36, 1)';
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
