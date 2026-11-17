// Leitura antecipada do cartão de upload: lê os arquivos de uma pessoa e devolve só o resumo (período e plays).
// Mensagem: {arquivos: [File, ...]}. Resposta: {ok: true, dados: {inicio, fim, plays}} ou {ok: false, erro}.
// Os File chegam por referência (como na Batalha): os bytes só existem aqui, e o Worker é encerrado no fim.
import { lerHistorico, resumo } from './js/historico.js';

self.onmessage = async ({ data: { arquivos } }) => {
  try {
    const partes = [];
    for (const f of arquivos) partes.push({ nome: f.name, bytes: new Uint8Array(await f.arrayBuffer()) });
    const dados = resumo(await lerHistorico(partes));
    if (!dados) throw new Error('Este histórico não tem músicas válidas.');
    self.postMessage({ ok: true, dados });
  } catch (e) {
    // Nossas mensagens são Error em português; TypeError, RangeError (memória) e afins viram texto genérico.
    const nosso = e?.constructor === Error && e.message;
    self.postMessage({ ok: false, erro: nosso || 'Não deu para ler este arquivo. Confira se é o ZIP do Histórico Estendido.' });
  }
};
