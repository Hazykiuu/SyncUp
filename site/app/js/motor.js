// Cliente do Worker: inicia o Python uma vez e manda ações para a ponte (web/ponte.py).
const worker = new Worker('worker.js', { type: 'module' });
const pendentes = new Map();
let proximoId = 0;
let ouvinteProgresso = () => {};
let prontoResolver, prontoRejeitar;
export const pronto = new Promise((ok, erro) => { prontoResolver = ok; prontoRejeitar = erro; });

worker.onmessage = ({ data }) => {
  if (data.tipo === 'progresso') ouvinteProgresso(data);
  else if (data.tipo === 'pronto') prontoResolver();
  else if (data.tipo === 'falhou') prontoRejeitar(new Error(data.erro));
  else if (data.tipo === 'resposta') {
    const { ok, erro } = pendentes.get(data.id) || {};
    pendentes.delete(data.id);
    data.ok ? ok?.(data.dados) : erro?.(new Error(data.erro));
  }
};

export function aoProgredir(fn) { ouvinteProgresso = fn; }

export function iniciar() { worker.postMessage({ tipo: 'iniciar' }); return pronto; }

/** Lê os File do navegador e manda o ArrayBuffer ao Worker sem copiar (transferência). */
export async function executar(nome, args = [], { arquivos = [], saida = 'json' } = {}) {
  await pronto;
  const lidos = await Promise.all(arquivos.map(async ({ caminho, arquivo }) => ({ caminho, bytes: await arquivo.arrayBuffer() })));
  const id = ++proximoId;
  return new Promise((ok, erro) => {
    pendentes.set(id, { ok, erro });
    worker.postMessage({ tipo: 'acao', id, nome, args, arquivos: lidos, saida }, lidos.map((l) => l.bytes));
  });
}

/** Baixa um arquivo gerado no Worker (PNG ou CSV) sem servidor. */
export function baixar({ nome, bytes }) {
  const tipo = nome.endsWith('.png') ? 'image/png' : 'text/csv';
  const url = URL.createObjectURL(new Blob([bytes], { type: tipo }));
  const a = Object.assign(document.createElement('a'), { href: url, download: nome });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
