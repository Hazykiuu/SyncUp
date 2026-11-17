// Conversa com os Workers do app (Dupla, Wrapped e Batalha). Uma requisição por vez; mensagens
// {etapa} são progresso e não encerram a requisição; {ok} encerra. Usado também no Node pelos testes.
export const SEM_RESPOSTA = 'o SyncUp parou de responder, provavelmente por falta de memória. Recarregue a página e tente com menos arquivos.';
const SEM_LEITURA = 'não deu para receber o resultado do processamento. Recarregue a página e tente de novo.';
const abortado = () => new DOMException('Processamento cancelado.', 'AbortError');

// terminate() não gera evento: quem cancela é que rejeita a requisição pendente (AbortError).
// Se o navegador matar o Worker por fora sem avisar, não há como saber: nada de prazo fixo, que
// cancelaria históricos grandes legítimos.
export function abrirWorker(url, { aoProgresso, semResposta = SEM_RESPOSTA } = {}) {
  const w = new Worker(url, { type: 'module' });
  let pendente = null, fechado = false;
  const terminar = (erro) => {
    if (fechado) return;
    fechado = true;
    w.terminate();
    const p = pendente; pendente = null;
    p?.erro(erro);
  };
  w.onmessage = ({ data }) => {
    if (!pendente) return;
    if (data?.etapa) { aoProgresso?.(data.etapa); return; }
    const p = pendente; pendente = null;
    data?.ok ? p.ok(data) : p.erro(new Error(data?.erro || semResposta));
  };
  w.onerror = (e) => { e.preventDefault?.(); terminar(new Error(semResposta)); };
  w.onmessageerror = () => terminar(new Error(SEM_LEITURA));
  return {
    pedir(mensagem, transferiveis = []) {
      if (fechado) return Promise.reject(abortado());
      if (pendente) throw new Error('abrirWorker: já há uma requisição em andamento.');
      return new Promise((ok, erro) => { pendente = { ok, erro }; w.postMessage(mensagem, transferiveis); });
    },
    cancelar: () => terminar(abortado()),
  };
}

// Uma requisição num Worker só dela (Dupla e Wrapped): ao terminar, o navegador devolve toda a memória.
export async function rodarNoWorker(url, mensagem, transferiveis) {
  const w = abrirWorker(url);
  try { return (await w.pedir(mensagem, transferiveis)).dados; } finally { w.cancelar(); }
}
