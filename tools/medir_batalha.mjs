// Medição da Batalha v2 (passo 4 do PLANO-BATALHA-V2): por tema, quantas vezes fica elegível, sai (dado, vazio,
// empate geral) ou empata no 1º; por par de temas, quantas vezes o mesmo lutador vence os dois; e, com o sorteio,
// a frequência de cada título do campeão. Imprime só números agregados (nenhum nome de artista ou de pessoa).
// Feito para dados fictícios (tools/gerar_dados_falsos.py e as demos): históricos reais só com autorização do dono.
// Uso: node tools/medir_batalha.mjs [--grupos 60] [--sorteios 20] [--json saida.json] arquivo1.zip arquivo2.zip …
import { readFileSync, writeFileSync } from 'node:fs';
import { basename } from 'node:path';

import { campeoes, janelaComum, medalhas, numerosDoLutador, rodadas, sortear, tituloCampeao } from '../site/app/js/batalha.js';
import { numerosDoGrupo } from '../site/app/js/batalha-medidas.js';
import { TEMA, TEMAS } from '../site/app/js/batalha-temas.js';
import { lerHistorico } from '../site/app/js/historico.js';

// As opções padrão da tela (opcoes.js, que importa o Preact e não roda no Node).
const PADRAO = { fuso: 'America/Sao_Paulo', musicas: '', artistas: '', varios: 'manter', deduplicar: false };

const args = process.argv.slice(2);
const opcao = (nome, padrao) => { const i = args.indexOf(nome); return i < 0 ? padrao : args.splice(i, 2)[1]; };
const GRUPOS = Number(opcao('--grupos', 60)), SORTEIOS = Number(opcao('--sorteios', 20)), SAIDA = opcao('--json', null);
const arquivos = args;
if (arquivos.length < 3) throw new Error('Passe pelo menos 3 históricos.');

// mulberry32, para os grupos saírem iguais a cada execução.
function gerador(semente) {
  let a = semente >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), a | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const colunas = [];
for (const c of arquivos) colunas.push(await lerHistorico([{ nome: basename(c), bytes: new Uint8Array(readFileSync(c)) }], PADRAO));
const faixas = colunas.map((c) => [Math.min(...c.utc), Math.max(...c.utc)]);
const inteiros = colunas.map((c, i) => numerosDoLutador(c, `P${i + 1}`, PADRAO.fuso));

// Grupos: as demos juntas (se vierem primeiro, os 4 primeiros arquivos) e sorteios de 3 a 6, com e sem recorte comum.
const sorte = gerador(2026);
const grupos = [{ membros: [0, 1, 2, 3].filter((i) => i < arquivos.length), comum: true }, { membros: [0, 1, 2, 3].filter((i) => i < arquivos.length), comum: false }];
while (grupos.length < GRUPOS) {
  const n = 3 + Math.floor(sorte() * 4), lista = [...arquivos.keys()];
  for (let i = lista.length - 1; i > 0; i--) { const j = Math.floor(sorte() * (i + 1)); [lista[i], lista[j]] = [lista[j], lista[i]]; }
  grupos.push({ membros: lista.slice(0, Math.min(n, lista.length)), comum: grupos.length % 2 === 0 });
}

const porTema = Object.fromEntries(TEMAS.map((t) => [t.chave, { elegivel: 0, dado: 0, vazio: 0, empate: 0, empateNo1: 0 }]));
const pares = new Map(); // "a|b" → { juntos, mesmo }
const titulos = new Map();
let semJanela = 0, campeoesUnicos = 0, batalhas = 0;
for (const g of grupos) {
  let lutadores;
  if (g.comum) {
    let janela;
    try { janela = janelaComum(g.membros.map((i) => faixas[i])); } catch { semJanela++; continue; }
    try {
      lutadores = g.membros.map((i) => ({ nome: `P${i + 1}`, ...numerosDoLutador(colunas[i], `P${i + 1}`, PADRAO.fuso, janela) }));
    } catch { semJanela++; continue; }
  } else lutadores = g.membros.map((i) => ({ nome: `P${i + 1}`, ...inteiros[i] }));
  const grupo = numerosDoGrupo(lutadores);
  lutadores = lutadores.map((l, i) => ({ ...l, numeros: { ...l.numeros, ...grupo[i] } }));
  const { dentro, fora } = rodadas(lutadores);
  for (const f of fora) porTema[f.chave][f.tipo]++;
  const vencedor = new Map();
  for (const r of dentro) {
    porTema[r.chave].elegivel++;
    const primeiros = r.posicoes.filter((p) => p === 1).length;
    if (primeiros > 1) porTema[r.chave].empateNo1++;
    vencedor.set(r.chave, primeiros === 1 ? r.posicoes.indexOf(1) : -1);
  }
  const chaves = [...vencedor.keys()];
  for (let i = 0; i < chaves.length; i++) {
    for (let j = i + 1; j < chaves.length; j++) {
      const k = `${chaves[i]}|${chaves[j]}`, p = pares.get(k) || { juntos: 0, mesmo: 0, tamanho: 0 };
      p.juntos++; p.tamanho += lutadores.length;
      if (vencedor.get(chaves[i]) >= 0 && vencedor.get(chaves[i]) === vencedor.get(chaves[j])) p.mesmo++;
      pares.set(k, p);
    }
  }
  for (let s = 1; s <= SORTEIOS; s++) {
    const sorteadas = sortear(dentro, { semente: s * 7919 + batalhas });
    const b = { rodadas: sorteadas, campeoes: campeoes(medalhas(sorteadas)) };
    const t = tituloCampeao(b);
    batalhas++;
    if (t === null) continue;
    campeoesUnicos++;
    titulos.set(t, (titulos.get(t) || 0) + 1);
  }
}

const medidos = grupos.length - semJanela;
const pct = (a, b) => (b ? `${((a * 100) / b).toFixed(0)}%` : '-');
console.log(`Grupos medidos: ${medidos} (${semJanela} sem período comum ou sem plays). Arquivos: ${arquivos.length}.`);
console.log('\nPor tema (de quantos grupos): elegível | fora por dado | vazio | empate geral | empate no 1º (dos elegíveis)');
for (const t of TEMAS) {
  const x = porTema[t.chave];
  console.log(`${t.chave.padEnd(12)} ${t.familia.padEnd(10)} ${String(x.elegivel).padStart(3)} | ${String(x.dado).padStart(3)} | ${String(x.vazio).padStart(3)} | ${String(x.empate).padStart(3)} | ${String(x.empateNo1).padStart(3)} (${pct(x.empateNo1, x.elegivel)})`);
}
const lista = [...pares].map(([k, p]) => ({ par: k, ...p, taxa: p.mesmo / p.juntos, acaso: p.juntos / p.tamanho }))
  .filter((p) => p.juntos >= 10).sort((a, b) => b.taxa - a.taxa || b.juntos - a.juntos);
console.log('\nPares com o mesmo vencedor único (juntos ≥ 10 grupos), os 25 maiores. "acaso" ≈ 1 / tamanho médio do grupo:');
for (const p of lista.slice(0, 25)) console.log(`${p.par.padEnd(24)} ${String(p.mesmo).padStart(3)}/${String(p.juntos).padEnd(3)} ${pct(p.mesmo, p.juntos).padStart(4)}  acaso ${pct(p.acaso * p.juntos, p.juntos)}  ${TEMA[p.par.split('|')[0]].familia} x ${TEMA[p.par.split('|')[1]].familia}`);
const sempre = lista.filter((p) => p.mesmo === p.juntos);
console.log(`\nPares em que o mesmo venceu sempre: ${sempre.length}`);
console.log(`\nTítulos (${SORTEIOS} sorteios por grupo, ${batalhas} batalhas, ${campeoesUnicos} com campeão único):`);
for (const [t, n] of [...titulos].sort((a, b) => b[1] - a[1])) console.log(`${t.padEnd(24)} ${String(n).padStart(4)} ${pct(n, campeoesUnicos)}`);
if (SAIDA) writeFileSync(SAIDA, JSON.stringify({ medidos, porTema, pares: lista, titulos: Object.fromEntries(titulos), batalhas, campeoesUnicos }, null, 1));
