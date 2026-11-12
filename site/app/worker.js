// Motor do SyncUp no navegador: Pyodide (Python em WebAssembly) numa thread separada.
// Mensagens: {tipo: 'iniciar'} e {tipo: 'acao', id, nome, args, arquivos, saida}.
// Respostas: {tipo: 'progresso', etapa, fracao}, {tipo: 'pronto'}, {tipo: 'resposta', id, ok, dados|erro}.
const PYODIDE = 'https://cdn.jsdelivr.net/pyodide/v0.29.0/full/';
const PLOTLY = 'plotly==6.9.0'; // o mesmo do app local; desenha com o plotly.js 3.7.0 (só na Dupla)
let py = null;

const progresso = (etapa, fracao) => self.postMessage({ tipo: 'progresso', etapa, fracao });

async function iniciar() {
  progresso('Carregando o Python', 0.05);
  const { loadPyodide } = await import(PYODIDE + 'pyodide.mjs');
  py = await loadPyodide({ indexURL: PYODIDE });
  progresso('Carregando o pandas', 0.4);
  await py.loadPackage(['pandas', 'tzdata']);
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

// Pacote sob demanda: plotly (9,9 MB) só na comparação. Os PNG são desenhados em Canvas (poster.js), sem Pillow.
const PRECISA = { comparar_dupla: ['plotly'] };
const extras = {};
const baixar = {
  plotly: async () => { await py.loadPackage('micropip'); await py.pyimport('micropip').install(PLOTLY); },
};
const garantir = (pacote) => (extras[pacote] ??= baixar[pacote]().catch((e) => { delete extras[pacote]; throw e; }));

async function acao({ id, nome, args = [], arquivos = [], saida = 'json' }) {
  try { await Promise.all((PRECISA[nome] || []).map(garantir)); } catch {
    throw new Error('RuntimeError: Não deu para baixar uma parte do SyncUp (os gráficos). Confira a internet e tente de novo.');
  }
  // Cada arquivo vai direto para o sistema de arquivos virtual, sem cópia extra.
  for (const { caminho, bytes } of arquivos) py.FS.writeFile(caminho, new Uint8Array(bytes));
  let resultado;
  try {
    resultado = py.pyimport('web.ponte')[nome](...args.map((a) => py.toPy(a)));
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
    if (data.tipo === 'iniciar') self.postMessage({ tipo: 'falhou', erro: 'não deu para baixar os arquivos. Confira a internet e tente de novo.' });
    else self.postMessage({ tipo: 'resposta', id: data.id, ok: false, erro: mensagem(erro) });
  }
};
