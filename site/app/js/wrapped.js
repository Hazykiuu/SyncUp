// Tela Wrapped: o histórico de uma pessoa vira stories da vida toda e um PNG.
import { html, useState } from 'preact-htm';
import { baixar, executar } from './motor.js';
import { Pessoa } from './envio.js';
import { Opcoes, PADRAO } from './opcoes.js';
import { TesteSom } from './som.js';

const Html = ({ conteudo }) => html`<div class="nucleo" dangerouslySetInnerHTML=${{ __html: conteudo }} />`;

export function Wrapped({ pronto }) {
  const [nome, setNome] = useState('');
  const [arquivos, setArquivos] = useState([]);
  const [opcoes, setOpcoes] = useState(PADRAO);
  const [fase, setFase] = useState({ tipo: 'parado' });
  const [baixando, setBaixando] = useState(false);
  const ocupado = fase.tipo === 'processando';

  const rodar = async (args, envio = []) => {
    setFase({ tipo: 'processando', etapa: 'Lendo o histórico completo e montando os stories…' });
    try {
      const r = await executar('wrapped', args, { arquivos: envio });
      setFase({ tipo: 'resultado', r });
      requestAnimationFrame(() => document.getElementById('resultado-wrapped')?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
    } catch (e) { setFase({ tipo: 'erro', mensagem: e.message }); }
  };
  const montar = () => {
    const envio = arquivos.map((arquivo, i) => ({ caminho: `/tmp/w-${i}-${arquivo.name.replace(/[^\w.-]/g, '_')}`, arquivo }));
    rodar([envio.map((e) => e.caminho), nome || 'Você', opcoes], envio);
  };
  const demo = async () => {
    setFase({ tipo: 'processando', etapa: 'Gerando um histórico fictício no seu aparelho…' });
    try {
      const d = await executar('arquivos_demo');
      setNome(d.nome_a); setArquivos([]);
      await rodar([[d.a], d.nome_a, opcoes]);
    } catch (e) { setFase({ tipo: 'erro', mensagem: e.message }); }
  };
  const png = async () => {
    setBaixando(true);
    try { baixar(await executar('cartao_wrapped', [], { saida: 'arquivo' })); } catch (e) { setFase({ tipo: 'erro', mensagem: e.message }); } finally { setBaixando(false); }
  };

  return html`
    <div class="pessoas uma">
      <${Pessoa} rotulo="♪" titulo="Seu histórico" cor="verde" nome=${nome} aoMudarNome=${setNome} arquivos=${arquivos} aoMudarArquivos=${setArquivos} desabilitado=${ocupado} />
    </div>
    <${Opcoes} valor=${opcoes} aoMudar=${setOpcoes} desabilitado=${ocupado} comPeriodo=${false} />
    <div class="barra-acao">
      <button type="button" class="btn btn-verde" onClick=${montar} disabled=${!pronto || ocupado || !arquivos.length}>
        ${ocupado ? 'Montando…' : 'Montar meu Wrapped'}<span class="seta" aria-hidden="true">→</span></button>
      <button type="button" class="btn btn-borda vidro" onClick=${demo} disabled=${!pronto || ocupado}>Testar com dados fictícios</button>
    </div>
    <div aria-live="polite">
      ${ocupado && html`<p class="processando vidro"><span class="giro" aria-hidden="true"></span>${fase.etapa}</p>`}
      ${fase.tipo === 'erro' && html`<p class="erro vidro" role="alert"><b>Não deu certo.</b> ${fase.mensagem}</p>`}
    </div>
    <div id="resultado-wrapped">${fase.tipo === 'resultado' && html`
      <section class="resultado" aria-label=${`Wrapped de ${fase.r.nome}`}>
        <${Html} conteudo=${fase.r.stories} />
        <div class="compartilhar"><div class="acoes">
          <button type="button" class="btn btn-verde" onClick=${png} disabled=${baixando}>${baixando ? 'Gerando…' : 'Baixar o story · PNG'}</button>
        </div></div>
        <details class="vidro detalhe"><summary>Como o arquétipo foi calculado</summary><${Html} conteudo=${fase.r.arquetipos} /></details>
        <${TesteSom} musicas=${fase.r.musicas} />
      </section>`}</div>`;
}
