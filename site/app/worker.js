// Motor do SyncUp no navegador: Pyodide (Python em WebAssembly) numa thread separada.
// Mensagens: {tipo: 'iniciar'} e {tipo: 'acao', id, nome, args, arquivos, saida}.
// Respostas: {tipo: 'progresso', etapa, fracao}, {tipo: 'pronto'}, {tipo: 'resposta', id, ok, dados|erro}.
const PYODIDE = 'https://cdn.jsdelivr.net/pyodide/v0.29.0/full/';
const PLOTLY = 'plotly==6.9.0'; // o mesmo do app local; desenha com o plotly.js 3.7.0
let py = null;

const progresso = (etapa, fracao) => self.postMessage({ tipo: 'progresso', etapa, fracao });

async function iniciar() {
  progresso('Baixando o Python (só na primeira vez)', 0.05);
  const { loadPyodide } = await import(PYODIDE + 'pyodide.mjs');
  py = await loadPyodide({ indexURL: PYODIDE });
  progresso('Baixando pandas e Pillow', 0.35);
  await py.loadPackage(['pandas', 'pillow', 'tzdata', 'micropip']);
  progresso('Baixando os gráficos', 0.7);
  await py.pyimport('micropip').install(PLOTLY);
  progresso('Preparando o SyncUp', 0.9);
  const nucleo = await (await fetch('syncup-core.zip', { cache: 'no-cache' })).arrayBuffer();
  py.unpackArchive(nucleo, 'zip', { extractDir: '/home/pyodide/syncup' });
  py.runPython("import sys; sys.path.insert(0, '/home/pyodide/syncup'); from web import ponte");
  progresso('Pronto', 1);
}

// Mensagem de erro do Python sem o traceback: a última linha "ValueError: ..." vira só o texto.
function mensagem(erro) {
  const texto = String(erro && erro.message || erro);
  const linhas = texto.trim().split('\n');
  const ultima = linhas[linhas.length - 1] || texto;
  const m = ultima.match(/^(?:ValueError|KeyError|RuntimeError|OSError): (.*)$/);
  return m ? m[1] : 'Algo deu errado ao processar os arquivos. Confira se são ZIPs do Histórico Estendido.';
}

async function acao({ id, nome, args = [], arquivos = [], saida = 'json' }) {
  // Cada arquivo vai direto para o sistema de arquivos virtual, sem cópia extra.
  for (const { caminho, bytes } of arquivos) py.FS.writeFile(caminho, new Uint8Array(bytes));
  const ponte = py.pyimport('web.ponte');
  const resultado = ponte[nome](...args.map((a) => py.toPy(a)));
  try {
    if (saida === 'arquivo') {
      const conteudo = py.FS.readFile(resultado);
      self.postMessage({ tipo: 'resposta', id, ok: true, dados: { nome: resultado.split('/').pop(), bytes: conteudo.buffer } }, [conteudo.buffer]);
    } else {
      const json = py.pyimport('json').dumps(resultado);
      self.postMessage({ tipo: 'resposta', id, ok: true, dados: JSON.parse(json) });
    }
  } finally {
    if (resultado && resultado.destroy) resultado.destroy();
    // Os históricos já foram lidos: sai do sistema virtual para não pesar na memória.
    for (const { caminho } of arquivos) { try { py.FS.unlink(caminho); } catch { /* já saiu */ } }
  }
}

self.onmessage = async ({ data }) => {
  try {
    if (data.tipo === 'iniciar') { await iniciar(); self.postMessage({ tipo: 'pronto' }); }
    else if (data.tipo === 'acao') await acao(data);
  } catch (erro) {
    self.postMessage({ tipo: data.tipo === 'iniciar' ? 'falhou' : 'resposta', id: data.id, ok: false, erro: mensagem(erro) });
  }
};
