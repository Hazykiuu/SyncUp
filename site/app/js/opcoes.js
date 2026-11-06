// Opções de dados, recolhidas por padrão (os padrões servem para quase todo mundo).
import { html } from 'preact-htm';

export const PADRAO = { comum: true, ponderacao: 'bruta', fuso: 'America/Sao_Paulo', musicas: '', artistas: '', varios: 'manter', deduplicar: false };

const FUSOS = ['America/Sao_Paulo', 'America/Manaus', 'America/Fortaleza', 'America/Noronha', 'America/Rio_Branco', 'Europe/Lisbon', 'UTC'];

export function Opcoes({ valor, aoMudar, desabilitado }) {
  const muda = (campo) => (e) => aoMudar({ ...valor, [campo]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });
  return html`
    <details class="opcoes vidro">
      <summary>Opções de dados <small>período, fuso e filtros</small></summary>
      <fieldset disabled=${desabilitado}>
        <label class="marcar"><input type="checkbox" checked=${valor.comum} onChange=${muda('comum')} />
          Comparar só o período em comum <small>(recomendado: os dois históricos no mesmo intervalo)</small></label>
        <div class="grade-opcoes">
          <label class="campo">Ponderação do cosseno
            <select class="entrada" value=${valor.ponderacao} onChange=${muda('ponderacao')}>
              <option value="bruta">Bruta (x)</option><option value="raiz">Raiz quadrada (√x)</option><option value="log1p">Logaritmo (ln(1+x))</option>
            </select></label>
          <label class="campo">Fuso horário
            <select class="entrada" value=${valor.fuso} onChange=${muda('fuso')}>${FUSOS.map((f) => html`<option value=${f}>${f}</option>`)}</select></label>
          <label class="campo">Various Artists
            <select class="entrada" value=${valor.varios} onChange=${muda('varios')}>
              <option value="manter">Manter</option><option value="ignorar">Ignorar</option>
            </select></label>
        </div>
        <div class="grade-opcoes">
          <label class="campo">Músicas ignoradas <small>uma por linha</small>
            <textarea class="entrada" rows="2" value=${valor.musicas} onInput=${muda('musicas')}></textarea></label>
          <label class="campo">Artistas ignorados <small>um por linha</small>
            <textarea class="entrada" rows="2" value=${valor.artistas} onInput=${muda('artistas')}></textarea></label>
        </div>
        <label class="marcar"><input type="checkbox" checked=${valor.deduplicar} onChange=${muda('deduplicar')} />
          Remover registros duplicados <small>(mesma faixa no mesmo instante)</small></label>
      </fieldset>
    </details>`;
}
