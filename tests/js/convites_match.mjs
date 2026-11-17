// Convites SYNCUP1. dos cenários do dueto, para colar no app e tirar as capturas.
// Uso: node tests/js/convites_match.mjs   (imprime os grupos, os pares formados e os códigos)
import { gerarConvite } from '../../site/app/js/convite.js';
import { chave, conciliar } from '../../site/app/js/match.js';
import { GRUPO_1, GRUPO_2 } from './casos_match.mjs';

for (const [nome, grupo] of [['Grupo 1', GRUPO_1], ['Grupo 2', GRUPO_2]]) {
  const r = conciliar(grupo);
  console.log(`\n== ${nome}: ${r.pares.map((g) => g.join(' × ')).join(' | ')}`);
  for (const g of r.pares) for (let a = 0; a < g.length; a++) for (let b = a + 1; b < g.length; b++) {
    const c = r.detalhes[chave(g[a], g[b])];
    console.log(`   ${g[a]} × ${g[b]}: ${c.pontuacao}% ${c.nivel}, jaccard ${c.jaccard_artistas.toFixed(3)}, comuns ${c.artistas_comuns.length}`);
  }
  console.log('');
  for (const p of grupo) console.log(await gerarConvite(p));
}
