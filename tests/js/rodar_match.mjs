// Roda o Match do app web no Node e escreve o JSON (teste de paridade com o Python).
// Uso: node tests/js/rodar_match.mjs '<opções em JSON>' nome1=arquivo1 nome2=arquivo2 [...]
import { readFileSync } from 'node:fs';
import { basename } from 'node:path';

import { lerHistorico } from '../../site/app/js/historico.js';
import { compararPerfis, conciliar, emparelhamentoOtimo, perfilDeHistorico } from '../../site/app/js/match.js';

const [opcoesJson, ...pessoas] = process.argv.slice(2);
const opcoes = JSON.parse(opcoesJson);
try {
  if (opcoes._matrizes) {
    process.stdout.write(JSON.stringify(opcoes._matrizes.map(({ nomes, valores }) => emparelhamentoOtimo(nomes, valores))));
    process.exit(0);
  }
  const perfis = [];
  for (const p of pessoas) {
    const [nome, caminho] = p.split('=');
    const c = await lerHistorico([{ nome: basename(caminho), bytes: new Uint8Array(readFileSync(caminho)) }], opcoes);
    perfis.push(perfilDeHistorico(c, nome));
  }
  const pares = [];
  for (let i = 0; i < perfis.length; i++) for (let j = i + 1; j < perfis.length; j++) pares.push(compararPerfis(perfis[i], perfis[j]));
  const r = perfis.length > 1 ? conciliar(perfis) : null;
  process.stdout.write(JSON.stringify({ perfis, pares, conciliacao: r && { pares: r.pares, melhores: r.melhores, media: r.pontuacao_media_pares } }));
} catch (e) {
  process.stdout.write(JSON.stringify({ erro: e.message }));
}
