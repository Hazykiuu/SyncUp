// Mede o story ativo da Batalha (page.evaluate): termina as animações e devolve { tipo, problemas }.
// Problema: peça fora da moldura (.su-story), peça sob o contador (acima do fim de .st-controles),
// conteúdo que transborda para baixo, número cortado (scrollWidth > clientWidth).
(() => {
  for (const a of document.getAnimations()) { try { a.finish(); } catch { /* animação infinita */ } }
  const slot = document.querySelector('#resultado-batalha .st-slot.ativo');
  const sec = slot.querySelector('.su-story');
  const tipo = [...sec.classList].find((c) => c.startsWith('s-')).slice(2);
  const S = sec.getBoundingClientRect();
  // O pódio é o pôster: o logo divide o topo com o contador, que some em 2 s (player.js, "limpo").
  const topo = sec.classList.contains('s-poster') ? S.top :document.querySelector('#resultado-batalha .st-controles').getBoundingClientRect().bottom;
  const conteudo = sec.querySelector('.st-conteudo');
  const problemas = [];
  const nome = (el) => `${el.tagName.toLowerCase()}.${[...el.classList].join('.')} "${(el.textContent || '').trim().slice(0, 30)}"`;
  for (const el of conteudo.querySelectorAll('*')) {
    if (el.closest('.sr-only') || (el.closest('svg') && el.tagName !== 'svg')) continue;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    if (r.left < S.left - 1 || r.right > S.right + 1 || r.bottom > S.bottom + 1) problemas.push(`fora da moldura: ${nome(el)}`);
    else if (r.top < topo - 1) problemas.push(`sob o contador: ${nome(el)}`);
  }
  if (conteudo.scrollHeight > conteudo.clientHeight + 1) problemas.push(`transborda ${conteudo.scrollHeight - conteudo.clientHeight}px`);
  for (const el of conteudo.querySelectorAll('em, .sb-valor, .sb-med, .sb-bloco span, .st-mega')) {
    if (el.clientWidth && el.scrollWidth > el.clientWidth + 1) problemas.push(`número cortado: ${nome(el)}`);
  }
  return { tipo, problemas };
})()
