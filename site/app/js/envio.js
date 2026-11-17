// Cartão de uma pessoa: nome + arquivos do histórico (vários, por clique ou arrastando).
// O espaço de soltar é um "deck": vazio, lendo, pronto (período e plays) ou com erro, antes do "Comparar".
import { html, useEffect, useRef, useState } from 'preact-htm';
import { chegarLista } from './chegada.js';
import { MESES } from './stories/logica.js';
import { abrirWorker } from './worker.js';

const ACEITOS = /\.(zip|json)$/i;
// Acima disso o celular (iPhone ~350 MB por aba) corre risco de fechar a página no meio da conta.
const TETO = 50 * 1048576;
const tamanho = (b) => (b >= 1048576 ? `${(b / 1048576).toFixed(1).replace('.', ',')} MB` : `${Math.max(1, Math.round(b / 1024))} KB`);
// O resumo traz a hora local já deslocada, em ms: lida como UTC dá o mês certo.
const mes = (ms) => { const d = new Date(ms); return `${MESES[d.getUTCMonth()]}/${d.getUTCFullYear()}`; };

// Uma fila para a página toda: lê uma pessoa por vez (na Batalha seriam até seis históricos na memória ao mesmo tempo).
let fila = Promise.resolve();
function lerResumo(arquivos) {
  let w = null, cancelado = false;
  const promessa = new Promise((ok, erro) => {
    fila = fila.then(async () => {
      if (cancelado) return erro(new DOMException('cancelado', 'AbortError'));
      w = abrirWorker('resumo-worker.js');
      try { ok((await w.pedir({ arquivos })).dados); } catch (e) { erro(e); } finally { w.cancelar(); }
    });
  });
  return { promessa, cancelar: () => { cancelado = true; w?.cancelar(); } };
}

const ICONE_ARQUIVO = html`<svg class="deck-icone" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5" /><path d="M8.5 15v-2M11 17v-6M13.5 16v-4M16 14.5v-1" /></svg>`;

export function Pessoa({ rotulo, cor, nome, aoMudarNome, arquivos, aoMudarArquivos, desabilitado, titulo = `Pessoa ${rotulo}`, exemplo = rotulo === 'A' ? 'Ana' : 'Bia', extra = null }) {
  const entrada = useRef(null);
  const [arrastando, setArrastando] = useState(false);
  const [aviso, setAviso] = useState('');
  const [leitura, setLeitura] = useState(null); // null | {lendo} | {dados} | {erro}
  useEffect(() => { if (!arquivos.length) setAviso(''); }, [arquivos]); // a demonstração zera a lista
  // Lê os arquivos assim que entram: período e plays aparecem no cartão; um arquivo errado avisa já aqui.
  useEffect(() => {
    if (!arquivos.length) { setLeitura(null); return undefined; }
    setLeitura({ lendo: true });
    const r = lerResumo(arquivos);
    r.promessa.then((dados) => setLeitura({ dados }), (e) => { if (e.name !== 'AbortError') setLeitura({ erro: e.message }); });
    return r.cancelar;
  }, [arquivos]);
  const somar = (escolhidos) => {
    const novos = [...escolhidos].filter((f) => ACEITOS.test(f.name));
    const chave = (f) => `${f.name}|${f.size}`;
    const existentes = new Set(arquivos.map(chave));
    const lista = [...arquivos, ...novos.filter((f) => !existentes.has(chave(f)))];
    if (lista.reduce((t, f) => t + f.size, 0) > TETO) { setAviso('Passou de 50 MB para esta pessoa. Envie só o Histórico Estendido (o ZIP do Spotify costuma ter bem menos).'); return; }
    // Arrastar ignora o accept do campo: o que não é .zip nem .json sai com aviso, nunca em silêncio.
    setAviso(novos.length < escolhidos.length ? 'Só aceitamos .zip ou .json (o ZIP do Histórico Estendido do Spotify).' : '');
    if (lista.length > arquivos.length) aoMudarArquivos(lista); // nada novo: a lista (e o aviso) ficam como estão
  };
  const idNome = `nome-${rotulo}`;
  const d = leitura?.dados;
  const estado = !arquivos.length ? 'vazio' : leitura?.erro ? 'erro' : d ? 'pronto' : 'lendo';
  return html`
    <section class=${`pessoa vidro ${cor}`} aria-labelledby=${`titulo-${rotulo}`}>
      <div class="pessoa-topo">
        <span class=${`avatar ${cor}`} aria-hidden="true">${rotulo}</span>
        <div><h2 id=${`titulo-${rotulo}`}>${titulo}</h2>${(rotulo === 'A' || rotulo === 'B') && html`<small class="lado">Lado ${rotulo}</small>`}</div>
        ${extra}
      </div>
      <label class="campo" for=${idNome}>Nome</label>
      <input id=${idNome} class="entrada" value=${nome} placeholder=${`Ex.: ${exemplo}`}
        onInput=${(e) => aoMudarNome(e.target.value)} disabled=${desabilitado} autocomplete="off" />
      <div class=${`soltar ${estado}${arrastando ? ' sobre' : ''}`}
        onDragOver=${(e) => { e.preventDefault(); setArrastando(true); }}
        onDragLeave=${() => setArrastando(false)}
        onDrop=${(e) => { e.preventDefault(); setArrastando(false); if (!desabilitado) somar(e.dataTransfer.files); }}>
        ${estado === 'vazio' ? html`
          ${ICONE_ARQUIVO}
          <p><b>Arraste seu my_spotify_data.zip</b> ou escolha o arquivo</p>`
        : html`<div class="deck" aria-live="polite">
          ${estado === 'lendo' && html`<span class="selo-deck">Lendo o histórico…</span>`}
          ${estado === 'pronto' && html`<span class="selo-deck ok"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12 5 5 9-10" /></svg>Histórico pronto</span>
            <p class="deck-periodo">${mes(d.inicio)} → ${mes(d.fim)}</p>
            <p class="deck-plays"><b class="num">${d.plays.toLocaleString('pt-BR')}</b> reproduções · ${arquivos.length} ${arquivos.length === 1 ? 'parte' : 'partes'}</p>`}
          ${estado === 'erro' && html`<p class="erro" role="alert">${leitura.erro}</p>`}
        </div>`}
        <button type="button" class="btn btn-borda vidro" onClick=${() => entrada.current.click()} disabled=${desabilitado}>
          ${arquivos.length ? '+ Adicionar mais arquivos' : 'Escolher arquivos'}
        </button>
        <input ref=${entrada} type="file" accept=".zip,.json" multiple hidden
          onChange=${(e) => { somar(e.target.files); e.target.value = ''; }} />
        ${estado === 'vazio' && html`<small>Pode enviar várias partes, em ZIP ou JSON.</small>`}
        ${aviso && html`<p class="erro" role="alert">${aviso}</p>`}
      </div>
      ${arquivos.length > 0 && html`
        <ul class="lista-arquivos" aria-label=${`Arquivos: ${titulo}`}>
          ${arquivos.map((f, i) => html`
            <li key=${f.name + f.size} ref=${chegarLista}>
              <span class="nome-arquivo">${f.name}</span><span class="peso">${tamanho(f.size)}</span>
              <button type="button" class="tirar" aria-label=${`Tirar ${f.name}`} disabled=${desabilitado}
                onClick=${() => aoMudarArquivos(arquivos.filter((_, j) => j !== i))}>×</button>
            </li>`)}
        </ul>`}
    </section>`;
}
