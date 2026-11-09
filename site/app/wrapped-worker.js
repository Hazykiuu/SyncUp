// Motor do Wrapped no navegador: lê o histórico e calcula em JavaScript, numa thread separada (sem Pyodide).
// Mensagem: {arquivos: [{nome, bytes: ArrayBuffer}], nome, opcoes}.
// Resposta: {ok: true, dados: {nome, dados, trilha}} ou {ok: false, erro}. Um Worker por montagem.
import { calcularWrapped, trilha } from './js/calculo.js';
import { lerHistorico } from './js/historico.js';

self.onmessage = async ({ data: { arquivos, nome, opcoes } }) => {
  try {
    const colunas = await lerHistorico(arquivos.map((a) => ({ nome: a.nome, bytes: new Uint8Array(a.bytes) })), opcoes);
    const dados = calcularWrapped(colunas, nome, opcoes.fuso || 'America/Sao_Paulo');
    self.postMessage({ ok: true, dados: { nome: dados.nome, dados, trilha: trilha(dados) } });
  } catch (e) {
    // Nossas mensagens são Error em português; TypeError, RangeError (memória) e afins viram texto genérico.
    const nosso = e?.constructor === Error && e.message;
    self.postMessage({ ok: false, erro: nosso || 'Algo deu errado ao processar os arquivos. Confira se são ZIPs do Histórico Estendido.' });
  }
};
