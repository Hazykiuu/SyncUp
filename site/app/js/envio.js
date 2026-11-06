// Cartão de uma pessoa: nome + arquivos do histórico (vários, por clique ou arrastando).
import { html, useRef, useState } from 'preact-htm';

const ACEITOS = /\.(zip|json)$/i;
const tamanho = (b) => (b >= 1048576 ? `${(b / 1048576).toFixed(1).replace('.', ',')} MB` : `${Math.max(1, Math.round(b / 1024))} KB`);

export function Pessoa({ rotulo, cor, nome, aoMudarNome, arquivos, aoMudarArquivos, desabilitado }) {
  const entrada = useRef(null);
  const [arrastando, setArrastando] = useState(false);
  const somar = (lista) => {
    const novos = [...lista].filter((f) => ACEITOS.test(f.name));
    const chave = (f) => `${f.name}|${f.size}`;
    const existentes = new Set(arquivos.map(chave));
    aoMudarArquivos([...arquivos, ...novos.filter((f) => !existentes.has(chave(f)))]);
  };
  const idNome = `nome-${rotulo}`;
  return html`
    <section class=${`pessoa vidro ${cor}`} aria-labelledby=${`titulo-${rotulo}`}>
      <div class="pessoa-topo">
        <span class=${`avatar ${cor}`} aria-hidden="true">${rotulo}</span>
        <h2 id=${`titulo-${rotulo}`}>Pessoa ${rotulo}</h2>
      </div>
      <label class="campo" for=${idNome}>Nome</label>
      <input id=${idNome} class="entrada" value=${nome} placeholder=${rotulo === 'A' ? 'Ex.: Ana' : 'Ex.: Bia'}
        onInput=${(e) => aoMudarNome(e.target.value)} disabled=${desabilitado} autocomplete="off" />
      <div class=${`soltar ${arrastando ? 'sobre' : ''}`}
        onDragOver=${(e) => { e.preventDefault(); setArrastando(true); }}
        onDragLeave=${() => setArrastando(false)}
        onDrop=${(e) => { e.preventDefault(); setArrastando(false); if (!desabilitado) somar(e.dataTransfer.files); }}>
        <p><b>Arraste o ZIP do Histórico Estendido</b> ou</p>
        <button type="button" class="btn btn-borda vidro" onClick=${() => entrada.current.click()} disabled=${desabilitado}>
          ${arquivos.length ? '+ Adicionar mais arquivos' : 'Escolher arquivos'}
        </button>
        <input ref=${entrada} type="file" accept=".zip,.json" multiple hidden
          onChange=${(e) => { somar(e.target.files); e.target.value = ''; }} />
        <small>Pode enviar várias partes. Os arquivos não saem do seu aparelho.</small>
      </div>
      ${arquivos.length > 0 && html`
        <ul class="lista-arquivos" aria-label=${`Arquivos da pessoa ${rotulo}`}>
          ${arquivos.map((f, i) => html`
            <li key=${f.name + f.size}>
              <span class="nome-arquivo">${f.name}</span><span class="peso">${tamanho(f.size)}</span>
              <button type="button" class="tirar" aria-label=${`Tirar ${f.name}`} disabled=${desabilitado}
                onClick=${() => aoMudarArquivos(arquivos.filter((_, j) => j !== i))}>×</button>
            </li>`)}
        </ul>`}
    </section>`;
}
