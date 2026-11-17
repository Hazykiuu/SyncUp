import assert from 'node:assert/strict';
import test from 'node:test';

import { arredondar1, perfilDeHistorico } from '../../site/app/js/match.js';

test('arredondar1: igual ao round(x, 1) do Python, meio para o par', () => {
  assert.equal(arredondar1(6.25), 6.2);
  assert.equal(arredondar1(6.75), 6.8);
  assert.equal(arredondar1(6.35), 6.3); // 6,35 em binário é 6,3499…
  assert.equal(arredondar1(0.05), 0.1); // 0,05 em binário é 0,05000…3
  assert.equal(arredondar1(99.95), 100);
  assert.equal(arredondar1(0), 0);
  assert.equal(arredondar1(100), 100);
});

test('perfilDeHistorico: aguenta um histórico grande (sem estourar a pilha)', () => {
  const n = 400_000, c = { utc: [], ms: [], artista: [], musica: [] };
  for (let i = 0; i < n; i++) { c.utc.push(i * 60_000); c.ms.push(60_000); c.artista.push(`A${i % 300}`); c.musica.push(`M${i % 900}`); }
  const p = perfilDeHistorico(c, 'Ana');
  assert.equal(p.top_artistas.long_term.length, 50);
});

test('melhorPar e trilhaMatch: o casal do grupo e um artista em comum por par', async () => {
  const { chave, melhorPar, trilhaMatch } = await import('../../site/app/js/match.js');
  const det = (p, comuns) => ({ pontuacao: p, artistas_comuns: comuns });
  const r = {
    pares: [['Ana', 'Bia'], ['Caio', 'Duda', 'Edu']],
    detalhes: {
      [chave('Ana', 'Bia')]: det(9, ['X', 'Y']), [chave('Caio', 'Duda')]: det(20, []),
      [chave('Caio', 'Edu')]: det(31, ['Z']), [chave('Duda', 'Edu')]: det(31, ['W']),
    },
  };
  const [x, y, c] = melhorPar(r);
  assert.deepEqual([x, y, c.pontuacao], ['Caio', 'Edu', 31]); // empate em 31: o primeiro fica
  const t = trilhaMatch(r);
  assert.deepEqual(t.slides['par-0'], [{ artista: 'X' }]);
  assert.equal(t.slides['par-1'], undefined); // Caio e Duda sem artista em comum
  assert.deepEqual(t.slides.poster, [{ artista: 'Z' }]);
  assert.deepEqual(t.fila, [{ artista: 'X' }, { artista: 'Y' }]);
});
