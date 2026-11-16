// Títulos, escalas e eixos dos gráficos da Dupla (graficos-dupla.js). Rodar: node --test tests/js
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { destaques, escalaArtistas, escalaHoras, gradeHoras, mesCurto, mesLongo, rotulosMeses } from '../../site/app/js/graficos-dupla.js';

const NOMES = ['Ana', 'Bia'];
const plano = Array(24).fill(100 / 24);
const comPico = (h) => plano.map((v, i) => (i === h ? v * 3 : v));
const g = (extra = {}) => ({
  artistas: [{ nome: 'X', a: 10, b: 10 }],
  horas: [plano, plano],
  dias: [[1, 2, 3, 4, 5, 6, 7], [7, 6, 5, 4, 3, 2, 1]],
  tracos: { a: [10, 10, 10], b: [10, 10, 10], limiares: [60, 40, 40] },
  meses: [{ mes: '2026-08', a: 10, b: 20 }],
  fuso: 'UTC',
  ...extra,
});
const d = (extra) => destaques(g(extra), NOMES);

test('hora do dia: pico, sem pico, mesmo pico e sem plays', () => {
  assert.equal(d({ horas: [comPico(18), comPico(12)] }).horas, 'Ana ouve mais às 18h; Bia, às 12h');
  assert.equal(d().horas, 'Os dois ouvem o dia todo, sem hora de pico');
  assert.equal(d({ horas: [comPico(7), comPico(7)] }).horas, 'Os dois ouvem mais às 7h');
  assert.equal(d({ horas: [comPico(7), plano] }).horas, 'Ana ouve mais às 7h; Bia ouve o dia todo, sem hora de pico');
  // Perfil zerado: nada de "pico às 0h".
  assert.equal(d({ horas: [comPico(7), Array(24).fill(0)] }).horas, 'Ana ouve mais às 7h; Bia não tem plays neste período');
  assert.equal(d({ horas: [comPico(7), Array(24).fill(0)] }).dias, 'Dia com mais plays: Ana, domingo. Horário de UTC.');
  assert.equal(d({ dias: [[1, 9, 1, 1, 1, 1, 1], [1, 9, 1, 1, 1, 1, 1]] }).dias, 'Dia com mais plays: terça para os dois. Horário de UTC.');
});

test('quem puxa: maior diferença só entre os 8 visíveis, e o que conta como quase igual', () => {
  const artistas = [...Array(8)].map((_, i) => ({ nome: `V${i}`, a: 5, b: 5 + i * 0.1 }));
  artistas[3] = { nome: 'Rui', a: 1.8, b: 0 };
  // Uma diferença enorme no 9º não vira título: ele está escondido atrás do "Ver mais".
  assert.equal(d({ artistas: [...artistas, { nome: 'Oculto', a: 90, b: 0 }] }).artistas, 'Rui pesa mais para Ana: 1,8% dos plays, contra 0,0% de Bia');
  assert.equal(d({ artistas: [{ nome: 'X', a: 10, b: 11 }] }).artistas, 'Os dois puxam os favoritos quase igual');
  assert.equal(d({ artistas: [{ nome: 'X', a: 30, b: 36 }] }).artistas, 'Os dois puxam os favoritos quase igual'); // 36 ÷ 30 < 1,25
  assert.equal(d({ artistas: [{ nome: 'X', a: 2, b: 20.5 }] }).artistas, 'X pesa mais para Bia: 20,5% dos plays, contra 2,0% de Ana');
  // 30% x 36% é quase igual, mas 0% x 5% não: o título fala do que não é.
  assert.equal(d({ artistas: [{ nome: 'X', a: 30, b: 36 }, { nome: 'Y', a: 0, b: 5 }] }).artistas, 'Y pesa mais para Bia: 5,0% dos plays, contra 0,0% de Ana');
});

test('traços: plural, nenhum e empate', () => {
  assert.equal(d().tracos, 'Nenhum dos dois atingiu os limiares de traço');
  assert.equal(d({ tracos: { a: [60, 10, 10], b: [10, 50, 50], limiares: [60, 40, 40] } }).tracos, 'Ana tem 1 traço; Bia, 2 traços');
  assert.equal(d({ tracos: { a: [60, 10, 10], b: [10, 10, 10], limiares: [60, 40, 40] } }).tracos, 'Ana tem 1 traço; Bia, nenhum');
  assert.equal(d({ tracos: { a: [60, 10, 10], b: [10, 40, 10], limiares: [60, 40, 40] } }).tracos, 'Os dois têm 1 traço');
});

test('meses: formato, mês de pico e um lado sem horas', () => {
  assert.equal(mesLongo('2026-08'), 'ago/2026');
  assert.equal(mesCurto('2026-08'), 'ago/26');
  const meses = [{ mes: '2025-12', a: 5, b: 0 }, { mes: '2026-01', a: 9, b: 0 }];
  assert.equal(d({ meses }).meses, 'Ana ouviu mais em jan/2026 (9 h); Bia não ouviu nada neste período');
  assert.equal(d().meses, 'Os dois ouviram mais em ago/2026 (10 h e 20 h)');
  assert.equal(d({ meses: [{ mes: '2026-01', a: 0, b: 0 }] }).meses, 'Nenhuma hora ouvida neste período');
});

test('escalas: artistas pelo maior dos 8 com trava em 1; horas pelo pico de cada um', () => {
  const artistas = [...Array(8)].map((_, i) => ({ nome: `V${i}`, a: i === 0 ? 20 : 1, b: 2 }));
  const escala = escalaArtistas([...artistas, { nome: 'Extra', a: 40, b: 0 }]);
  assert.equal(escala(20), 1);
  assert.equal(escala(10), 0.5);
  assert.equal(escala(40), 1); // o extra maior não encolhe os 8
  assert.deepEqual(escalaHoras([1, 2, 4]), [0.25, 0.5, 1]);
  assert.deepEqual(escalaHoras([0, 0]), [0, 0]);
});

test('eixo dos meses: grade sem NaN, um mês só e rótulos que colidem', () => {
  assert.deepEqual(gradeHoras([{ a: 0, b: 0 }]), { topo: 2, linhas: [0, 1, 2] });
  assert.deepEqual(gradeHoras([{ a: 199, b: 150 }]), { topo: 200, linhas: [0, 100, 200] });
  assert.deepEqual(rotulosMeses([{ mes: '2026-01' }]), [{ i: 0, x: 50 }]);
  // nov/25 a fev/26: a virada de ano (jan, a 66%) fica a mais de 15% das pontas e entra.
  const curtos = ['2025-11', '2025-12', '2026-01', '2026-02'].map((mes) => ({ mes }));
  assert.deepEqual(rotulosMeses(curtos).map((r) => r.i), [0, 2, 3]);
  // dez/25 a dez/26: jan/26 fica colado no primeiro rótulo e some.
  const ano = [...Array(13)].map((_, i) => ({ mes: i === 0 ? '2025-12' : `2026-${String(i).padStart(2, '0')}` }));
  assert.deepEqual(rotulosMeses(ano).map((r) => r.i), [0, 12]);
});
