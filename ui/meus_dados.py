"""Painel "Meus dados" e bloco de privacidade: o que fica no computador e como apagar."""

from __future__ import annotations

from pathlib import Path

from configuracao import ConfiguracaoCarga
from formatacao import escape_html, fmt_num
from privacidade import dados_locais, limpar_cache_local
from ui.comum import info

PASTA_CACHE = Path(ConfiguracaoCarga().diretorio_cache)

PRIVACIDADE = """<section class="su-privacy" aria-labelledby="su-privacy-title">
  <h2 id="su-privacy-title">Seus dados ficam com você</h2>
  <p class="su-note">O SyncUp roda no seu computador. Não há conta, servidor nem anúncios.</p>
  <div class="su-privacy-grid">
    <div><h3>Fica no seu computador</h3><ul>
      <li>Os históricos que você envia: lidos nesta sessão e apagados em até 1 hora.</li>
      <li>O cache, até você apagar em <b>Opções de dados → Meus dados</b>.</li>
      <li>Os downloads (CSV, PNG, XSPF), em pastas temporárias apagadas ao fim da sessão.</li>
    </ul></div>
    <div><h3>Vai para a internet só se você pedir</h3><ul>
      <li><b>ListenBrainz</b>: só o nome de usuário público que você digitar.</li>
      <li><b>MusicBrainz</b>: só nomes de artistas, e só com a caixa de estilo marcada.</li>
    </ul></div>
    <div><h3>Nunca é guardado</h3><ul>
      <li>IP, modelo do aparelho e outros campos do histórico que não são música.</li>
      <li>Nada é vendido nem compartilhado: o código é aberto para qualquer um conferir.</li>
    </ul></div>
  </div>
</section>"""


def _tamanho(n: int) -> str:
    if n < 1024**2:
        return f'{fmt_num(n / 1024, 1)} KB'
    return f'{fmt_num(n / 1024**2, 1)} MB'


def resumo_html() -> str:
    """Lista o que está guardado agora, com tamanho e data da última mudança."""
    linhas = ''.join(
        f'<li><b>{escape_html(i.rotulo)}</b><span>{escape_html(i.detalhe)}</span>'
        + (
            f'<small>{fmt_num(i.arquivos)} arquivo{"s" if i.arquivos != 1 else ""} · '
            f'{_tamanho(i.tamanho)}'
            if i.arquivos
            else '<small>vazio'
        )
        + (f' · {i.atualizado:%d/%m/%Y %H:%M}' if i.atualizado else '')
        + '</small></li>'
        for i in dados_locais(PASTA_CACHE)
    )
    return f'<ul class="su-my-data">{linhas}</ul>'


def limpar_cache(confirmado: bool) -> str:
    if confirmado:
        info(f'Cache limpo: {fmt_num(limpar_cache_local(PASTA_CACHE))} arquivo(s) apagado(s).')
    return resumo_html()
