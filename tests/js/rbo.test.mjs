// RBO de "Favoritos em comum" (dupla.js): os mesmos casos de tests/test_metricas.py, com os mesmos números.
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { rbo } from '../../site/app/js/dupla.js';

test('rbo: iguais, disjuntos, vazio, topo pesa mais e os mesmos números do Python', () => {
  assert.equal(rbo([...'abcde'], [...'abcde']), 1);
  assert.equal(rbo([...'abc'], [...'xyz']), 0);
  assert.equal(rbo([], [...'abc']), null);
  const topo = rbo([...'abcdefgh'], [...'bacdefgh']), fim = rbo([...'abcdefgh'], [...'abcdefhg']);
  assert.ok(topo < fim && fim < 1);
  assert.equal(rbo([...'abcde'], [...'abc']), 1);
  assert.equal(rbo([...'abcdefg'], [...'bacdegf']), 0.8901585000000001);
  assert.equal(rbo([...'abcde'], [...'xaybz']), 0.37089000000000005);
});
