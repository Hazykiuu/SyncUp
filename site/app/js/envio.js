// Cartão de uma pessoa: nome + arquivos do histórico (vários, por clique ou arrastando).
// O espaço de soltar é um "deck": vazio, lendo, pronto (período e plays) ou com erro, antes do "Comparar".
import { html, useEffect, useRef, useState } from 'preact-htm';
import { chegarLista } from './chegada.js';
import { historicoDoLastfm, USUARIO_VALIDO } from './lastfm.js';
import { MESES } from './stories/logica.js';
import { Contador } from './stories/slides.js';
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

// Last.fm (1.23): sem o ZIP do Spotify, a pessoa busca as escutas pelo nome de usuário. O download vira um
// arquivo JSON igual ao do Spotify e entra no cartão como qualquer outro (marcado com `lastfm` para a telemetria
// e para o "≈" nos minutos).
const restante = (ms) => (ms < 60000 ? 'menos de 1 min' : `cerca de ${Math.round(ms / 60000)} min`);
function BuscaLastfm({ id, desabilitado, aoPronto }) {
  const [aberto, setAberto] = useState(false);
  const [usuario, setUsuario] = useState('');
  const [periodo, setPeriodo] = useState('tudo');
  const [baixando, setBaixando] = useState(null); // null | progresso de baixarScrobbles
  const [erro, setErro] = useState('');
  const controle = useRef(null);
  const campo = useRef(null);
  useEffect(() => () => controle.current?.abort(), []);
  useEffect(() => { if (aberto) campo.current?.focus(); }, [aberto]); // abriu: o foco vai para o campo
  const buscar = async (e) => {
    e.preventDefault();
    const nome = usuario.trim();
    if (!USUARIO_VALIDO.test(nome)) { setErro('Esse nome não parece do Last.fm: de 2 a 15 letras, números, - ou _, começando por letra.'); return; }
    controle.current = new AbortController();
    setErro(''); setBaixando({ scrobbles: 0, total: 0, restanteMs: 0 });
    try {
      const r = await historicoDoLastfm(nome, { periodo, sinal: controle.current.signal, aoProgresso: setBaixando });
      const arquivo = new File([r.json], `lastfm-${nome}.json`, { type: 'application/json' });
      if (arquivo.size > TETO) { setErro('Passou de 50 MB para esta pessoa. Escolha "Último ano" e busque de novo.'); return; }
      arquivo.lastfm = { usuario: nome, cobertura: r.cobertura, capas: r.capas };
      aoPronto(arquivo);
    } catch (falha) { if (falha.name !== 'AbortError') setErro(falha.message); } finally { setBaixando(null); controle.current = null; }
  };
  if (!aberto) return html`<button type="button" class="lastfm-abrir" onClick=${() => setAberto(true)} disabled=${desabilitado}>Sem o ZIP do Spotify? <b>Usar o Last.fm</b></button>`;
  return html`<form id=${id} class="lastfm" onSubmit=${buscar} aria-labelledby=${`${id}-titulo`}>
    <h3 id=${`${id}-titulo`} class="lastfm-titulo">Buscar no Last.fm</h3>
    <label class="campo" for=${`${id}-usuario`}>Usuário do Last.fm<small id=${`${id}-dica`}>Só o nome vai ao Last.fm. As escutas vêm de lá direto para este aparelho.</small></label>
    <input ref=${campo} id=${`${id}-usuario`} name="usuario" class="entrada" value=${usuario} onInput=${(e) => { setUsuario(e.target.value); setErro(''); }}
      required maxlength="15" autocomplete="off" autocorrect="off" autocapitalize="none" spellcheck="false" enterkeyhint="search"
      aria-describedby=${`${id}-dica`} aria-invalid=${erro ? 'true' : undefined} disabled=${desabilitado || !!baixando} />
    <fieldset class="lastfm-periodo" disabled=${desabilitado || !!baixando}>
      <legend class="campo">Período</legend>
      <label><input type="radio" name=${`${id}-periodo`} value="tudo" checked=${periodo === 'tudo'} onChange=${() => setPeriodo('tudo')} /> Todo o histórico</label>
      <label><input type="radio" name=${`${id}-periodo`} value="ano" checked=${periodo === 'ano'} onChange=${() => setPeriodo('ano')} /> Último ano</label>
    </fieldset>
    ${baixando ? html`<div class="lastfm-baixando">
        <span class="selo-deck" role="status"><span class="giro" aria-hidden="true"></span>Baixando do Last.fm…</span>
        <progress aria-label="Escutas baixadas do Last.fm" max=${baixando.total || undefined} value=${baixando.total ? Math.min(baixando.scrobbles, baixando.total) : undefined}></progress>
        <small class="num" aria-hidden="true">${baixando.total ? `${baixando.scrobbles.toLocaleString('pt-BR')} de ${baixando.total.toLocaleString('pt-BR')} escutas · ${restante(baixando.restanteMs)}` : 'Contando as escutas…'}</small>
        <button type="button" class="btn btn-borda superficie" onClick=${() => controle.current?.abort()}>Cancelar</button>
      </div>`
    : html`<div class="lastfm-acoes">
        <button type="submit" class="btn btn-borda superficie" disabled=${desabilitado}>Buscar escutas</button>
        <button type="button" class="lastfm-fechar" onClick=${() => { setAberto(false); setErro(''); }}>Voltar ao ZIP</button>
      </div>`}
    ${erro && html`<p class="erro" role="alert">${erro}</p>`}
  </form>`;
}

const ICONE_ARQUIVO = html`<svg class="deck-icone" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5" /><path d="M8.5 15v-2M11 17v-6M13.5 16v-4M16 14.5v-1" /></svg>`;

export function Pessoa({ rotulo, cor, nome, aoMudarNome, arquivos, aoMudarArquivos, desabilitado, titulo = `Pessoa ${rotulo}`, exemplo = rotulo === 'A' ? 'Mari' : 'Juca', extra = null, modo = '' }) {
  // `modo`: Batalha e Match ficam montados juntos e numeram as pessoas do mesmo jeito; o prefixo evita IDs repetidos.
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
  const idNome = `${modo}nome-${rotulo}`, idTitulo = `${modo}titulo-${rotulo}`;
  const d = leitura?.dados;
  const estado = !arquivos.length ? 'vazio' : leitura?.erro ? 'erro' : d ? 'pronto' : 'lendo';
  const lastfm = arquivos.find((f) => f.lastfm)?.lastfm;
  return html`
    <section class=${`pessoa superficie ${cor}`} aria-labelledby=${idTitulo}>
      <div class="pessoa-topo">
        <span class=${`avatar ${cor}`} aria-hidden="true">${rotulo}</span>
        <div><h2 id=${idTitulo}>${titulo}</h2>${(rotulo === 'A' || rotulo === 'B') && html`<small class="lado">Lado ${rotulo}</small>`}</div>
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
          ${estado === 'lendo' && html`<span class="selo-deck"><span class="giro" aria-hidden="true"></span>Lendo neste aparelho…</span>`}
          ${estado === 'pronto' && html`<span class="selo-deck ok"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12 5 5 9-10" /></svg>${lastfm ? 'Do Last.fm' : 'Lido neste aparelho'}</span>
            <dl class="telemetria">
              <div class="tl-periodo"><dt>Período</dt><dd>${mes(d.inicio)} → ${mes(d.fim)}</dd></div>
              <div><dt>Reproduções</dt><dd class="num"><span aria-hidden="true"><${Contador} valor=${d.plays} ativo /></span><span class="sr-only">${d.plays.toLocaleString('pt-BR')}</span></dd></div>
              ${lastfm ? html`<div><dt>Duração real</dt><dd class="num">${Math.round(lastfm.cobertura * 100)}%</dd></div>`
                : html`<div><dt>${arquivos.length === 1 ? 'Parte' : 'Partes'}</dt><dd class="num">${arquivos.length}</dd></div>`}
            </dl>`}
          ${estado === 'erro' && html`<p class="erro" role="alert">${leitura.erro}</p>`}
        </div>`}
        ${!lastfm && html`<button type="button" class="btn btn-borda superficie" onClick=${() => entrada.current.click()} disabled=${desabilitado}>
          ${arquivos.length ? '+ Adicionar mais arquivos' : 'Escolher arquivos'}
        </button>`}
        <input ref=${entrada} type="file" accept=".zip,.json" multiple hidden
          onChange=${(e) => { somar(e.target.files); e.target.value = ''; }} />
        ${estado === 'vazio' && html`<small>Pode enviar várias partes, em ZIP ou JSON.</small>`}
        ${aviso && html`<p class="erro" role="alert">${aviso}</p>`}
      </div>
      ${!arquivos.length && html`<${BuscaLastfm} id=${`${modo}lastfm-${rotulo}`} desabilitado=${desabilitado} aoPronto=${(f) => aoMudarArquivos([f])} />`}
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

// "Calculando…" dos 4 modos, com a saída: Cancelar volta à tela de envio.
export function Processando({ etapa, aoCancelar, aoMontar }) {
  return html`<p ref=${aoMontar} class="processando superficie"><span class="giro" aria-hidden="true"></span><span>${etapa}</span>
    <button type="button" class="btn btn-borda superficie" onClick=${aoCancelar}>Cancelar</button></p>`;
}
