// Roda o Wrapped do app web no Node e escreve o JSON (usado pelo teste de paridade com o Python).
// Uso: node tests/js/rodar_wrapped.mjs '<opções em JSON>' '<nome>' arquivo1.zip [arquivo2.json …]
import { readFileSync } from 'node:fs';
import { basename } from 'node:path';

import { calcularWrapped, trilha } from '../../site/app/js/calculo.js';
import { lerHistorico } from '../../site/app/js/historico.js';

const [opcoesJson, nome, ...caminhos] = process.argv.slice(2);
const opcoes = JSON.parse(opcoesJson);
try {
  const colunas = await lerHistorico(caminhos.map((c) => ({ nome: basename(c), bytes: new Uint8Array(readFileSync(c)) })), opcoes);
  const dados = calcularWrapped(colunas, nome, opcoes.fuso || 'America/Sao_Paulo');
  process.stdout.write(JSON.stringify({ nome: dados.nome, dados, trilha: trilha(dados) }));
} catch (e) {
  process.stdout.write(JSON.stringify({ erro: e.message }));
}
