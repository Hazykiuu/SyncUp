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
