// Motor da Batalha no navegador: lê de 3 a 6 históricos, uma pessoa por vez, e devolve só os números.
// Uma mensagem por fase, sempre com os File de novo (nunca relê uma referência guardada da fase anterior):
//   {fase: 1, arquivos: [[File, ...], ...], opcoes} → {ok: true, faixas: [[minUtc, maxUtc], ...]}
//   {fase: 2, arquivos, nomes, opcoes, janela: [inicio, fim] | null, semente, evitar} → {ok: true, dados} (montarBatalha)
// `semente` e `evitar` (temas da batalha anterior) ficam na tela: este Worker é recriado a cada batalha.
// Durante a leitura: {etapa: 'Lendo Ana (2 de 4)…'}. Erro: {ok: false, erro}.
// Memória: só os bytes e as colunas de uma pessoa por vez, mais os números já guardados.
import { montarBatalha, numerosDoLutador } from './js/batalha.js';
import { lerHistorico } from './js/historico.js';
import { mensagemDeErro } from './js/worker.js';

async function ler(lista, opcoes) {
  const partes = [];
  for (const f of lista) partes.push({ nome: f.name, bytes: new Uint8Array(await f.arrayBuffer()) });
  return lerHistorico(partes, opcoes);
}

self.onmessage = async ({ data: { fase, arquivos, nomes, opcoes, janela, semente, evitar } }) => {
  try {
    const rotulo = (i) => (nomes?.[i] ? `${nomes[i]} (${i + 1} de ${arquivos.length})` : `${i + 1} de ${arquivos.length}`);
    if (fase === 1) {
      const faixas = [];
      for (let i = 0; i < arquivos.length; i++) {
        self.postMessage({ etapa: `Achando o período de cada um: ${i + 1} de ${arquivos.length}…` });
        const c = await ler(arquivos[i], opcoes);
        if (!c.utc.length) throw new Error('Um dos históricos não contém registros de músicas válidos.');
        let min = Infinity, max = -Infinity;
        for (const t of c.utc) { if (t < min) min = t; if (t > max) max = t; }
        faixas.push([min, max]);
      }
      self.postMessage({ ok: true, faixas });
      return;
    }
    const lutadores = [];
    for (let i = 0; i < arquivos.length; i++) {
      self.postMessage({ etapa: `Lendo ${rotulo(i)}…` });
      const c = await ler(arquivos[i], opcoes);
      lutadores.push({ nome: nomes[i], ...numerosDoLutador(c, nomes[i], opcoes.fuso || 'America/Sao_Paulo', janela) });
    }
    self.postMessage({ ok: true, dados: montarBatalha(lutadores, { semente, evitar }) });
  } catch (e) {
    console.error(e);
    self.postMessage({ ok: false, erro: mensagemDeErro(e) });
  }
};
