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

test('melhorPar e trilhaMatch: o dueto mais afinado e um artista em comum por par', async () => {
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

test('duetos: os 7 cenários com os números de compararPerfis, sem métrica nova', async () => {
  const { chave, conciliar, duetos } = await import('../../site/app/js/match.js');
  const { GRUPO_1, GRUPO_2 } = await import('./casos_match.mjs');
  for (const grupo of [GRUPO_1, GRUPO_2]) {
    const r = conciliar(grupo);
    const ds = duetos(r);
    assert.equal(ds.length, r.pares.length);
    for (const d of ds) for (const l of d.linhas) {
      const c = r.detalhes[chave(l.x, l.y)];
      assert.equal(l.pontuacao, c.pontuacao);
      assert.equal(l.nivel, c.nivel);
      assert.equal(l.jaccard, c.jaccard_artistas);
      assert.deepEqual(l.refrao, c.artistas_comuns);
    }
  }
  const [alta, trio] = duetos(conciliar(GRUPO_1));
  // 1, 6 e 7: sobreposição alta; Bruno ⊂ Ana, então o Lado B de Ana é vazio e o de Bruno vem cheio (8, na ordem).
  assert.deepEqual(alta.nomes, ['Ana', 'Bruno']);
  assert.ok(alta.linhas[0].pontuacao >= 25);
  assert.deepEqual(alta.ladoB.find((p) => p.para === 'Ana').origens, [{ de: 'Bruno', artistas: [] }]);
  assert.deepEqual(alta.ladoB.find((p) => p.para === 'Bruno').origens[0].artistas, Array.from({ length: 8 }, (_, i) => `Ana Extra ${i + 1}`));
  // 3 e 5: trio com nome longo; três linhas, refrão só com os três, Lado B por origem.
  assert.equal(trio.nomes.length, 3);
  assert.equal(trio.linhas.length, 3);
  assert.deepEqual([...trio.refrao].sort(), ['Arctic Monkeys', 'Tame Impala', 'The Strokes']);
  assert.deepEqual(trio.refrao, trio.linhas[0].refrao.filter((a) => trio.refrao.includes(a))); // ordem do primeiro par
  assert.ok(!trio.refrao.includes('Phoenix')); // Caio e Duda têm, Maria não
  for (const p of trio.ladoB) assert.deepEqual(p.origens.map((o) => o.de).sort(), trio.nomes.filter((n) => n !== p.para).sort());
  const [baixa, nada] = duetos(conciliar(GRUPO_2));
  // 2: baixa sobreposição, um artista só; 4: nenhum artista em comum (jaccard 0, refrão vazio).
  assert.deepEqual(baixa.refrao, ['Björk']);
  assert.ok(baixa.linhas[0].jaccard > 0 && baixa.linhas[0].jaccard < 0.1);
  assert.equal(nada.linhas[0].jaccard, 0);
  assert.deepEqual(nada.refrao, []);
  assert.equal(nada.linhas[0].pontuacao, 0);
});

// R1-01: mesmos casos de tests/test_match.py.
const pessoa = (nome, a) => ({ nome, top_artistas: { short_term: a, medium_term: a, long_term: a }, top_musicas: {} });
const grupo = () => [pessoa('Ana', ['Banda A', 'Banda B', 'Banda C']), pessoa('Bia', ['Banda X', 'Banda Y', 'Banda Z']),
  pessoa('Cris', ['Banda A', 'Banda X', 'Banda Q']), pessoa('Eli', ['Banda B', 'Banda Y', 'Banda R'])];
const duda = () => pessoa('Duda', ['!!!', '🎵']);

test('sem dados comparáveis: o par não vira 0%', async () => {
  const { compararPerfis } = await import('../../site/app/js/match.js');
  const c = compararPerfis(grupo()[0], duda());
  assert.equal(c.pontuacao, null);
  assert.equal(c.nivel, 'Comparação indisponível');
});

test('sem dados comparáveis: sai do Match, em grupo ímpar e par', async () => {
  const { conciliar } = await import('../../site/app/js/match.js');
  for (const quantos of [4, 3]) {
    const sem = conciliar(grupo().slice(0, quantos)), com = conciliar([...grupo().slice(0, quantos), duda()]);
    assert.deepEqual(com.sem_dados, ['Duda']);
    assert.deepEqual(sem.sem_dados, []);
    assert.deepEqual([com.nomes, com.pares, com.pontuacao_media_pares], [sem.nomes, sem.pares, sem.pontuacao_media_pares]);
  }
});

test('sem dados comparáveis: menos de duas pessoas é erro com os nomes', async () => {
  const { conciliar } = await import('../../site/app/js/match.js');
  assert.throws(() => conciliar([grupo()[0], duda()]), /Sem artistas comparáveis: Duda/);
});

test('amostra pequena: abaixo de 30 artistas em um dos lados a faixa não vale', async () => {
  const { compararPerfis } = await import('../../site/app/js/match.js');
  const nomes = (n) => Array.from({ length: n }, (_, i) => `Banda ${i}`);
  for (const [n, pequena] of [[1, true], [29, true], [30, false]]) {
    const c = compararPerfis(pessoa('Ana', nomes(40)), pessoa('Eva', nomes(n)));
    assert.equal(c.amostra_pequena, pequena);
    assert.equal(c.nivel === 'Amostra pequena', pequena);
  }
});
