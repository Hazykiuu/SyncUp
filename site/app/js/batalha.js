// Batalha (modo Grupo do app web): de 3 a 6 históricos disputam rodadas de números do período.
// Funções puras: o Worker (batalha-worker.js) lê os arquivos e chama numerosDoLutador e montarBatalha.
import { calcularWrapped, compararTexto } from './calculo.js';
import { cosseno, ponderar, TEMPO_MINIMO_PLAY_MS } from './dupla.js';

// Verde e violeta são os da Dupla; texto sobre elas é sempre preto (teste de contraste em batalha.test.mjs).
export const CORES = ['#1ed760', '#c4b7ff', '#f573a0', '#ffa42b', '#5cb8ff', '#f5d547'];

// Valor de tela de cada rodada a partir do Wrapped do recorte. `menor`: menor vence.
// `vazio`: por que a rodada sai quando ninguém pontua (`minimo`: valor que não conta como ponto).
const RODADAS = [
  { chave: 'horas', titulo: 'Maratonista', unidade: 'h', casas: 0, vazio: 'ninguém ouviu' },
  { chave: 'plays', titulo: 'Play infinito', unidade: 'plays', casas: 0, vazio: 'ninguém deu play' },
  { chave: 'artistas', titulo: 'Explorador(a)', unidade: 'artistas', casas: 0, vazio: 'ninguém ouviu' },
  { chave: 'musicas', titulo: 'Colecionador(a)', unidade: 'músicas', casas: 0, vazio: 'ninguém ouviu' },
  { chave: 'sequencia', titulo: 'Sem parar', unidade: 'dias seguidos', casas: 0, vazio: 'ninguém ouviu' },
  { chave: 'dia', titulo: 'Dia mais insano', unidade: 'h num dia', casas: 1, vazio: 'ninguém ouviu' },
  { chave: 'coruja', titulo: 'Coruja', unidade: '% na madrugada', casas: 1, vazio: 'ninguém ouviu de madrugada' },
  { chave: 'repeteco', titulo: 'Repeteco', unidade: 'vezes a mesma música num dia', casas: 0, minimo: 1, vazio: 'ninguém repetiu uma música no mesmo dia' },
  { chave: 'fa', titulo: 'Fã nº 1', unidade: '% no artista favorito', casas: 1, vazio: 'ninguém ouviu' },
  { chave: 'paciencia', titulo: 'Paciência', unidade: '% de músicas puladas', casas: 1, menor: true },
];

// Todas as métricas são ≥ 0: Math.round basta (sem o caso do .5 negativo).
export const arredondar = (v, casas) => Math.round(v * 10 ** casas) / 10 ** casas;

export function validarNomes(nomes) {
  if (nomes.length < 3 || nomes.length > 6) throw new Error('A Batalha precisa de 3 a 6 pessoas.');
  const limpos = nomes.map((n, i) => (n || '').trim() || `Pessoa ${i + 1}`);
  if (new Set(limpos).size !== limpos.length) throw new Error('Use nomes diferentes para identificar cada pessoa da batalha.');
  return limpos;
}

// Recorte comum (analise.comparar_grupo): do maior início ao menor fim, em UTC.
export function janelaComum(faixas) {
  const inicio = Math.max(...faixas.map(([i]) => i)), fim = Math.min(...faixas.map(([, f]) => f));
  if (inicio > fim) throw new Error('Não há período comum a todo o grupo. Desmarque o recorte comum.');
  return [inicio, fim];
}

export function recortar(c, inicio, fim) {
  const dentro = [];
  for (let i = 0; i < c.utc.length; i++) if (c.utc[i] >= inicio && c.utc[i] <= fim) dentro.push(i);
  return Object.fromEntries(Object.entries(c).map(([k, v]) => [k, Array.isArray(v) ? dentro.map((i) => v[i]) : v]));
}

// Os 10 números das rodadas e os plays por artista (para a dupla afinada) de um histórico já recortado.
export function numerosDoLutador(c, nome, fuso) {
  const contagens = new Map();
  for (let i = 0; i < c.ms.length; i++) if (c.ms[i] >= TEMPO_MINIMO_PLAY_MS) contagens.set(c.artista[i], (contagens.get(c.artista[i]) || 0) + 1);
  if (!contagens.size) throw new Error(`Não há plays ≥30s para ${nome} no período escolhido. Tente desmarcar o recorte comum.`);
  const d = calcularWrapped(c, nome, fuso);
  return {
    numeros: {
      horas: d.horas, plays: d.plays, artistas: d.quantidade_artistas, musicas: d.quantidade_musicas,
      sequencia: d.sequencia, dia: d.horas_dia_recorde, coruja: d.periodos.Madrugada * 100,
      repeteco: d.repeticao_dia.plays, fa: d.participacao_artista_vida * 100,
      paciencia: d.habitos.pulos === null ? null : d.habitos.pulos * 100,
    },
    contagens: new Map([...contagens].sort(([a], [b]) => compararTexto(a, b))),
  };
}

// Posição olímpica: 1 + quantos têm valor estritamente melhor (empate divide a posição).
export const posicoes = (valores, menor) => valores.map((v) => 1 + valores.filter((x) => (menor ? x < v : x > v)).length);

export function rodadas(lutadores) {
  const dentro = [], fora = [];
  for (const r of RODADAS) {
    const brutos = lutadores.map((l) => l.numeros[r.chave]);
    if (brutos.some((v) => v === null || v === undefined)) { fora.push({ chave: r.chave, titulo: r.titulo, motivo: 'nem todo histórico informa as músicas puladas' }); continue; }
    const valores = brutos.map((v) => arredondar(v, r.casas));
    if (!r.menor && valores.every((v) => v <= (r.minimo ?? 0))) { fora.push({ chave: r.chave, titulo: r.titulo, motivo: r.vazio }); continue; }
    if (valores.every((v) => v === valores[0])) { fora.push({ chave: r.chave, titulo: r.titulo, motivo: 'todos empataram' }); continue; }
    dentro.push({ chave: r.chave, titulo: r.titulo, unidade: r.unidade, casas: r.casas, menor: !!r.menor, valores, posicoes: posicoes(valores, r.menor) });
  }
  return { dentro, fora };
}

export function medalhas(lista) {
  const m = lista[0].posicoes.map(() => ({ ouro: 0, prata: 0, bronze: 0 }));
  for (const { posicoes: p } of lista) p.forEach((pos, i) => { const tipo = ['ouro', 'prata', 'bronze'][pos - 1]; if (tipo) m[i][tipo]++; });
  return m;
}

const comparar = (a, b) => b.ouro - a.ouro || b.prata - a.prata || b.bronze - a.bronze;
export function campeoes(m) {
  const melhor = [...m].sort(comparar)[0];
  return m.map((x, i) => (comparar(x, melhor) === 0 ? i : -1)).filter((i) => i >= 0);
}

// Maior cosseno (em % com 1 casa); empate: mais artistas em comum, depois os nomes em ordem.
export function maisAfinada(contagens, nomes) {
  const pares = [];
  for (let i = 0; i < contagens.length; i++) {
    for (let j = i + 1; j < contagens.length; j++) {
      const valor = arredondar((cosseno(ponderar(contagens[i]), ponderar(contagens[j])) ?? 0) * 100, 1);
      let comuns = 0;
      for (const k of contagens[i].keys()) if (contagens[j].has(k)) comuns++;
      pares.push({ par: [i, j], valor, comuns, nomes: [nomes[i], nomes[j]].sort(compararTexto) });
    }
  }
  pares.sort((a, b) => b.valor - a.valor || b.comuns - a.comuns || compararTexto(a.nomes[0], b.nomes[0]) || compararTexto(a.nomes[1], b.nomes[1]));
  const { par, valor, comuns } = pares[0];
  return { par, valor, comuns };
}

// `lutadores`: [{ nome, numeros, contagens }] na ordem do formulário. Devolve o JSON da tela.
export function montarBatalha(lutadores) {
  const { dentro, fora } = rodadas(lutadores);
  if (!dentro.length) throw new Error('Não há números suficientes para uma batalha neste período.');
  const m = medalhas(dentro);
  return {
    lutadores: lutadores.map((l, i) => ({ nome: l.nome, cor: CORES[i], medalhas: m[i] })),
    rodadas: dentro,
    fora,
    campeoes: campeoes(m),
    afinada: maisAfinada(lutadores.map((l) => l.contagens), lutadores.map((l) => l.nome)),
  };
}
