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

// Maior cosseno log1p (o mais estável no estudo com históricos reais), em % com 1 casa; empate: mais artistas em comum,
// depois os nomes em ordem. `menosAfinada` é a ponta oposta da mesma ordem (desempates invertidos).
// `artistaComum`: o artista que mais une o par, pelo menor dos dois plays (500 x 1 não une; 80 x 80 une).
export function maisAfinada(contagens, nomes) {
  const pares = [];
  for (let i = 0; i < contagens.length; i++) {
    for (let j = i + 1; j < contagens.length; j++) {
      const valor = arredondar((cosseno(ponderar(contagens[i], 'log1p'), ponderar(contagens[j], 'log1p')) ?? 0) * 100, 1);
      let comuns = 0;
      for (const k of contagens[i].keys()) if (contagens[j].has(k)) comuns++;
      pares.push({ par: [i, j], valor, comuns, nomes: [nomes[i], nomes[j]].sort(compararTexto) });
    }
  }
  pares.sort((a, b) => b.valor - a.valor || b.comuns - a.comuns || compararTexto(a.nomes[0], b.nomes[0]) || compararTexto(a.nomes[1], b.nomes[1]));
  const { par, valor, comuns } = pares[0];
  const [ca, cb] = par.map((i) => contagens[i]);
  let artistaComum = null, melhor = 0;
  for (const [k, n] of ca) {
    const juntos = Math.min(n, cb.get(k) ?? 0);
    if (juntos > melhor || (juntos === melhor && juntos > 0 && compararTexto(k, artistaComum) < 0)) { artistaComum = k; melhor = juntos; }
  }
  const ultimo = pares[pares.length - 1];
  return { par, valor, comuns, artistaComum, menosAfinada: { par: ultimo.par, valor: ultimo.valor, comuns: ultimo.comuns } };
}

/* ---------- Disputa e narrativa (adendo de 16/11) ---------- */
const FOLGA = 1e-9; // 5% "exatos" não podem falhar por ponto flutuante

// 'por-um-triz' (diferença ≤ 5%), 'massacre' (o dobro) ou null. Só com um único 1º e um 2º acima de zero.
export function destaqueRodada(r) {
  const unico = r.posicoes.filter((p) => p === 1).length === 1;
  const primeiro = r.valores[r.posicoes.indexOf(1)];
  const segundos = r.valores.filter((_, i) => r.posicoes[i] === 2);
  if (!unico || !segundos.length || !(segundos[0] > 0)) return null;
  const segundo = segundos[0];
  if (r.menor) {
    if ((segundo - primeiro) / segundo <= 0.05 + FOLGA) return 'por-um-triz';
    return primeiro > 0 && segundo >= primeiro * 2 - FOLGA ? 'massacre' : null;
  }
  if ((primeiro - segundo) / primeiro <= 0.05 + FOLGA) return 'por-um-triz';
  return primeiro >= segundo * 2 - FOLGA ? 'massacre' : null;
}

// Paciência: o último colocado, se for um só e pular mais de 60% das músicas ("Dedinho nervoso").
export function alertaPaciencia(r, nomes) {
  if (r.chave !== 'paciencia') return null;
  const pior = Math.max(...r.valores);
  const quem = r.valores.map((v, i) => (v === pior ? i : -1)).filter((i) => i >= 0);
  return quem.length === 1 && pior > 60 ? { nome: nomes[quem[0]], valor: pior } : null;
}

// Título de classe do campeão único, pela primeira combinação de ouros que bater.
const TITULOS = [
  [['coruja', 'dia'], 'Insone Oficial'],
  [['repeteco', 'fa'], 'Modo Obsessão'],
  [['artistas', 'musicas'], 'Enciclopédia Musical'],
  [['horas', 'plays'], 'Trator de Plays'],
];
export function tituloCampeao(b) {
  if (b.campeoes.length !== 1) return null;
  const c = b.campeoes[0];
  const ouros = new Set(b.rodadas.filter((r) => r.posicoes[c] === 1).map((r) => r.chave));
  return TITULOS.find(([chaves]) => chaves.every((k) => ouros.has(k)))?.[1] ?? 'Dono(a) do Aux';
}

// Campeão único que venceu por 1 ouro, ou empatado em ouros e decidido na prata.
export function decididoNoDetalhe(b) {
  if (b.campeoes.length !== 1) return false;
  const c = b.lutadores[b.campeoes[0]].medalhas;
  const vice = b.lutadores.filter((_, i) => i !== b.campeoes[0]).map((l) => l.medalhas)
    .sort((x, y) => y.ouro - x.ouro || y.prata - x.prata || y.bronze - x.bronze)[0];
  return c.ouro - vice.ouro === 1 || (c.ouro === vice.ouro && c.prata !== vice.prata);
}

const NOME_SELO = { 'por-um-triz': 'por um triz', massacre: 'massacre' };
// Até 3 fatos da partida: o campeão, um selo (massacre antes de por um triz) e a dupla menos afinada.
export function resenha(b, nomes) {
  const e = (lista) => lista.join(lista.length > 2 ? ', ' : ' e ').replace(/, ([^,]*)$/, ' e $1');
  const fatos = [b.campeoes.length === 1
    ? `${nomes[b.campeoes[0]]} levou a batalha como ${b.titulo}.`
    : `Empate no topo entre ${e(b.campeoes.map((i) => nomes[i]))}.`];
  const selo = b.rodadas.find((r) => r.destaque === 'massacre') || b.rodadas.find((r) => r.destaque === 'por-um-triz');
  if (selo) fatos.push(`${selo.titulo} foi ${NOME_SELO[selo.destaque]}: ${nomes[selo.posicoes.indexOf(1)]} venceu.`);
  const [x, y] = b.menosAfinada.par;
  fatos.push(`${nomes[x]} e ${nomes[y]} são os de gosto mais distante (${String(b.menosAfinada.valor).replace('.', ',')}%).`);
  return fatos.join(' ');
}

// `lutadores`: [{ nome, numeros, contagens }] na ordem do formulário. Devolve o JSON da tela.
export function montarBatalha(lutadores) {
  const { dentro, fora } = rodadas(lutadores);
  if (!dentro.length) throw new Error('Não há números suficientes para uma batalha neste período.');
  const nomes = lutadores.map((l) => l.nome);
  const m = medalhas(dentro);
  const { menosAfinada, ...afinada } = maisAfinada(lutadores.map((l) => l.contagens), nomes);
  const b = {
    lutadores: lutadores.map((l, i) => ({ nome: l.nome, cor: CORES[i], medalhas: m[i] })),
    rodadas: dentro.map((r) => ({ ...r, destaque: destaqueRodada(r), alerta: alertaPaciencia(r, nomes) })),
    fora,
    campeoes: campeoes(m),
    afinada,
    menosAfinada,
  };
  b.titulo = tituloCampeao(b);
  b.detalhe = decididoNoDetalhe(b);
  b.resenha = resenha(b, nomes);
  return b;
}
