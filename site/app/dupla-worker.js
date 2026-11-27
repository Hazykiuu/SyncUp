// Motor da Dupla no navegador: lê os dois históricos e compara em JavaScript, numa thread separada (sem Pyodide).
// Mensagem: {a: [{nome, bytes: ArrayBuffer}], b: [...], nomes: [A, B], opcoes}.
// Resposta: {ok: true, dados} (o JSON de ponte.comparar_dupla + `csv` da playlist comum) ou {ok: false, erro}.
// Um Worker por comparação: ao terminar, o navegador devolve toda a memória (importa no celular).
import { compararDupla, csvPlaylist, identificar, respostaDupla } from './js/dupla.js';
import { graficosDupla } from './js/graficos-dupla.js';
import { lerHistorico } from './js/historico.js';
import { mensagemDeErro } from './js/worker.js';

self.onmessage = async ({ data: { a, b, nomes, opcoes } }) => {
  try {
    const lados = [a, b].map((lista) => lista.map((x) => ({ nome: x.nome, bytes: new Uint8Array(x.bytes) })));
    const ids = await Promise.all(lados.map(identificar));
    const [ca, cb] = [await lerHistorico(lados[0], opcoes), await lerHistorico(lados[1], opcoes)];
    const r = compararDupla(ca, cb, nomes[0], nomes[1], opcoes, ids);
    self.postMessage({ ok: true, dados: { ...respostaDupla(r), graficos: graficosDupla(r), csv: csvPlaylist(r) } });
  } catch (e) {
    console.error(e);
    self.postMessage({ ok: false, erro: mensagemDeErro(e) });
  }
};
