// Roda a comparação da Dupla do app web no Node e escreve o JSON (teste de paridade com o Python).
// Uso: node tests/js/rodar_dupla.mjs '<opções em JSON>' '<nome A>' '<nome B>' a:arquivo1.zip [a:…] b:arquivo2.zip [b:…]
import { readFileSync } from 'node:fs';
import { basename } from 'node:path';

import { compararDupla, identificar, respostaDupla } from '../../site/app/js/dupla.js';
import { lerHistorico } from '../../site/app/js/historico.js';

const [opcoesJson, nomeA, nomeB, ...caminhos] = process.argv.slice(2);
const opcoes = JSON.parse(opcoesJson);
const ler = (lado) => caminhos.filter((c) => c.startsWith(`${lado}:`)).map((c) => c.slice(2))
  .map((c) => ({ nome: basename(c), bytes: new Uint8Array(readFileSync(c)) }));
try {
  const [ca, cb] = [await lerHistorico(ler('a'), opcoes), await lerHistorico(ler('b'), opcoes)];
  const ids = [await identificar(ler('a')), await identificar(ler('b'))];
  const r = compararDupla(ca, cb, nomeA, nomeB, opcoes, ids);
  // opcoes._saida === 'resposta': o JSON que o app recebe; senão, o resultado bruto (sem os auxiliares).
  if (opcoes._saida === 'resposta') process.stdout.write(JSON.stringify(respostaDupla(r)));
  else { delete r._bruto; delete r.fuso; process.stdout.write(JSON.stringify(r)); }
} catch (e) {
  process.stdout.write(JSON.stringify({ erro: e.message }));
}
