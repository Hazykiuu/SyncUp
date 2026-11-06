// App do SyncUp no navegador: casca (topo, motor) e a tela Dupla.
import { html, render, useEffect, useState } from 'preact-htm';
import { aoProgredir, executar, iniciar } from './motor.js';
import { Pessoa } from './envio.js';
import { Opcoes, PADRAO } from './opcoes.js';
import { Resultado } from './resultado.js';
import { Wrapped } from './wrapped.js';

function Motor({ estado }) {
  if (estado.pronto) return html`<p class="motor ok" role="status"><span class="ponto" aria-hidden="true"></span>Pronto · tudo roda no seu aparelho</p>`;
  if (estado.erro) return html`<p class="motor erro" role="alert">Não foi possível carregar o SyncUp: ${estado.erro} <button type="button" class="btn btn-borda vidro" onClick=${() => location.reload()}>Tentar de novo</button></p>`;
  return html`
    <div class="motor" role="status" aria-live="polite">
      <span>${estado.etapa}</span>
      <div class="trilho" role="progressbar" aria-label="Carregando o SyncUp" aria-valuemin="0" aria-valuemax="100" aria-valuenow=${Math.round(estado.fracao * 100)}>
        <i style=${`width:${Math.round(estado.fracao * 100)}%`}></i>
      </div>
      <small>Na primeira visita o navegador baixa o Python (~30 MB); depois fica guardado.</small>
    </div>`;
}

function Dupla({ pronto }) {
  const [nomes, setNomes] = useState(['', '']);
  const [arquivos, setArquivos] = useState([[], []]);
  const [opcoes, setOpcoes] = useState(PADRAO);
  const [fase, setFase] = useState({ tipo: 'parado' });
  const ocupado = fase.tipo === 'processando';
  const pode = pronto && !ocupado && arquivos[0].length > 0 && arquivos[1].length > 0;

  const rodar = async (args, envio = []) => {
    setFase({ tipo: 'processando', etapa: 'Lendo os históricos e calculando a sintonia…' });
    try {
      const r = await executar('comparar_dupla', args, { arquivos: envio });
      setFase({ tipo: 'resultado', r });
      requestAnimationFrame(() => document.getElementById('resultado')?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
    } catch (e) { setFase({ tipo: 'erro', mensagem: e.message }); }
  };
  const comparar = () => {
    const envio = arquivos.flatMap((lista, p) => lista.map((arquivo, i) => ({ caminho: `/tmp/${p ? 'b' : 'a'}-${i}-${arquivo.name.replace(/[^\w.-]/g, '_')}`, arquivo })));
    const caminhos = [0, 1].map((p) => envio.filter((e) => e.caminho.startsWith(`/tmp/${p ? 'b' : 'a'}-`)).map((e) => e.caminho));
    rodar([caminhos[0], caminhos[1], nomes[0] || 'Pessoa A', nomes[1] || 'Pessoa B', opcoes], envio);
  };
  const demo = async () => {
    setFase({ tipo: 'processando', etapa: 'Gerando dois históricos fictícios no seu aparelho…' });
    try {
      const d = await executar('arquivos_demo');
      setNomes([d.nome_a, d.nome_b]); setArquivos([[], []]);
      await rodar([[d.a], [d.b], d.nome_a, d.nome_b, opcoes]);
    } catch (e) { setFase({ tipo: 'erro', mensagem: e.message }); }
  };
  // Atualização por função: duas mudanças no mesmo instante não apagam uma à outra.
  const mudar = (lista, i, v) => lista.map((x, j) => (j === i ? v : x));

  return html`
    <div class="pessoas">
      <${Pessoa} rotulo="A" cor="verde" nome=${nomes[0]} aoMudarNome=${(v) => setNomes((n) => mudar(n, 0, v))} arquivos=${arquivos[0]} aoMudarArquivos=${(v) => setArquivos((a) => mudar(a, 0, v))} desabilitado=${ocupado} />
      <${Pessoa} rotulo="B" cor="roxo" nome=${nomes[1]} aoMudarNome=${(v) => setNomes((n) => mudar(n, 1, v))} arquivos=${arquivos[1]} aoMudarArquivos=${(v) => setArquivos((a) => mudar(a, 1, v))} desabilitado=${ocupado} />
    </div>
    <${Opcoes} valor=${opcoes} aoMudar=${setOpcoes} desabilitado=${ocupado} />
    <div class="barra-acao">
      <button type="button" class="btn btn-verde" onClick=${comparar} disabled=${!pode} aria-describedby="dica-comparar">
        ${ocupado ? 'Comparando…' : 'Comparar históricos'}<span class="seta" aria-hidden="true">→</span></button>
      <button type="button" class="btn btn-borda vidro" onClick=${demo} disabled=${!pronto || ocupado}>Testar com dados fictícios</button>
      <small id="dica-comparar">${!pronto ? 'Esperando o SyncUp terminar de carregar.' : arquivos[0].length && arquivos[1].length ? '' : 'Envie pelo menos um arquivo para cada pessoa.'}</small>
    </div>
    <div aria-live="polite">
      ${fase.tipo === 'processando' && html`<p class="processando vidro"><span class="giro" aria-hidden="true"></span>${fase.etapa}</p>`}
      ${fase.tipo === 'erro' && html`<p class="erro vidro" role="alert"><b>Não deu certo.</b> ${fase.mensagem}</p>`}
    </div>
    <div id="resultado">${fase.tipo === 'resultado' && html`<${Resultado} r=${fase.r} />`}</div>`;
}

function App() {
  const [motor, setMotor] = useState({ etapa: 'Preparando…', fracao: 0, pronto: false, erro: '' });
  // As duas telas ficam montadas (hidden): trocar de aba não perde o resultado.
  const lerModo = () => (location.hash === '#wrapped' ? 'wrapped' : 'dupla');
  const [modo, setModo] = useState(lerModo);
  useEffect(() => {
    const mudar = () => setModo(lerModo());
    addEventListener('hashchange', mudar);
    return () => removeEventListener('hashchange', mudar);
  }, []);
  useEffect(() => {
    aoProgredir(({ etapa, fracao }) => setMotor((m) => ({ ...m, etapa, fracao })));
    iniciar().then(() => setMotor((m) => ({ ...m, pronto: true }))).catch((e) => setMotor((m) => ({ ...m, erro: e.message })));
  }, []);
  return html`
    <header class="app-topo shell">
      <a class="marca vivo" href="../" aria-label="SyncUp, voltar ao site"><span class="logo" aria-hidden="true"><i></i><i></i><i></i><i></i></span>SyncUp</a>
      <nav class="abas-app" aria-label="Modos">
        ${[['dupla', 'Dupla'], ['wrapped', 'Wrapped']].map(([id, rotulo]) => html`<a class=${modo === id ? 'ativa' : ''} href=${`#${id}`} aria-current=${modo === id ? 'page' : null}>${rotulo}</a>`)}
        <span aria-disabled="true">Match <small>em breve</small></span>
        <span aria-disabled="true">Grupo <small>em breve</small></span>
      </nav>
    </header>
    <main id="principal" class="shell app-corpo">
      <div class="app-cabeca">
        <span class="etiqueta">${modo === 'wrapped' ? 'Wrapped' : 'Dupla'} · 100% no seu aparelho</span>
        <h1>${modo === 'wrapped' ? 'Seu Wrapped da vida toda' : 'Compare dois históricos'}</h1>
        <p class="sub">${modo === 'wrapped' ? 'Envie o seu Histórico Estendido do Spotify e veja a sua vida musical em stories.' : 'Envie o Histórico Estendido do Spotify de duas pessoas.'} Nada é enviado para nenhum servidor.</p>
        <${Motor} estado=${motor} />
      </div>
      <div hidden=${modo !== 'dupla'}><${Dupla} pronto=${motor.pronto} /></div>
      <div hidden=${modo !== 'wrapped'}><${Wrapped} pronto=${motor.pronto} /></div>
    </main>`;
}

render(html`<${App} />`, document.getElementById('app'));
