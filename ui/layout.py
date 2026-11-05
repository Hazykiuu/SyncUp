"""Montagem da interface Gradio: Início, abas e eventos."""

from __future__ import annotations

import os
from zoneinfo import available_timezones

import gradio as gr

from configuracao import MUSICAS_IGNORADAS_PADRAO, VERSAO
from dados import (
    habilitar_leitura_paralela,
)
from formatacao import escape_html, fmt_pct
from perfil_gosto import listar_perfis
from perfis import AVISO_TRACOS, LIMIAR_FAVORITOS, LIMIAR_MADRUGADA, LIMIAR_REPEAT
from spotify_api import PASTA_PERFIS, REDIRECT_PADRAO
from ui.comum import (
    CONCORRENCIA,
    CSS,
    HEAD,
    JS,
    OPCOES_PONDERACAO,
    _limpar_exportacoes,
)
from ui.dupla import (
    baixar_cartao,
    baixar_cartao_sintonia,
    baixar_playlist,
    carregar_demo,
    executar_dupla,
    executar_grupo,
)
from ui.match import (
    atualizar_perfis,
    baixar_cartao_match,
    baixar_festa,
    executar_match,
    perfis_salvos,
)
from ui.meu_wrapped import baixar_wrapped, carregar_demo_wrapped, executar_wrapped
from ui.meus_dados import (
    PRIVACIDADE,
    apagar_perfil_salvo,
    atualizar_meus_dados,
    limpar_cache,
    resumo_html,
)


def _tema() -> gr.themes.Base:
    """Tema nativo do Gradio com a paleta escura do Spotify."""
    fonte = [gr.themes.Font('Figtree'), 'Helvetica Neue', 'Helvetica', 'Arial', 'sans-serif']
    cores = dict(
        body_background_fill='#121212',
        body_text_color='#ffffff',
        body_text_color_subdued='#b3b3b3',
        background_fill_primary='#181818',
        background_fill_secondary='#1f1f1f',
        block_background_fill='#181818',
        block_border_color='#2a2a2a',
        block_border_width='1px',
        block_label_text_color='#b3b3b3',
        block_label_background_fill='#181818',
        block_title_text_color='#ffffff',
        block_info_text_color='#b3b3b3',
        border_color_primary='#2a2a2a',
        border_color_accent='#1ed760',
        color_accent='#1ed760',
        color_accent_soft='#1f3d2a',
        input_background_fill='#2a2a2a',
        input_border_color='#2a2a2a',
        input_border_color_focus='#1ed760',
        input_placeholder_color='#b3b3b3',
        checkbox_background_color='#2a2a2a',
        checkbox_background_color_selected='#1ed760',
        checkbox_border_color='#727272',
        checkbox_border_color_selected='#1ed760',
        checkbox_label_background_fill='#181818',
        checkbox_label_background_fill_selected='#181818',
        checkbox_label_text_color='#ffffff',
        checkbox_label_text_color_selected='#ffffff',
        table_text_color='#ffffff',
        table_even_background_fill='#181818',
        table_odd_background_fill='#1f1f1f',
        table_border_color='#2a2a2a',
        table_row_focus='#2a2a2a',
        button_primary_background_fill='#1ed760',
        button_primary_background_fill_hover='#3be477',
        button_primary_text_color='#000000',
        button_primary_text_color_hover='#000000',
        button_secondary_background_fill='#2a2a2a',
        button_secondary_background_fill_hover='#3e3e3e',
        button_secondary_text_color='#ffffff',
        button_secondary_text_color_hover='#ffffff',
        link_text_color='#1ed760',
        link_text_color_hover='#3be477',
        loader_color='#1ed760',
        slider_color='#1ed760',
        stat_background_fill='#1ed760',
        panel_background_fill='#181818',
        accordion_text_color='#ffffff',
        shadow_drop='0 8px 24px rgba(0,0,0,.5)',
    )
    # Mesmas cores no modo escuro do navegador.
    sem_variante = {'color_accent', 'shadow_drop'}
    cores |= {f'{chave}_dark': valor for chave, valor in cores.items() if chave not in sem_variante}
    return gr.themes.Base(
        primary_hue='green',
        secondary_hue='violet',
        neutral_hue='neutral',
        font=fonte,
        font_mono=fonte,
        radius_size=gr.themes.sizes.radius_lg,
    ).set(
        **cores,
        block_info_text_size='15px',
        block_label_text_size='15px',
        block_title_text_size='17px',
        input_text_size='16px',
        button_large_text_size='16px',
        button_small_text_size='16px',
        button_medium_text_size='16px',
        button_large_radius='999px',
        button_medium_radius='999px',
        button_small_radius='999px',
    )


def _secao(titulo: str, texto: str = '') -> gr.HTML:
    """Cabeçalho de seção no estilo das prateleiras do Spotify."""
    corpo = f'<p>{escape_html(texto)}</p>' if texto else ''
    return gr.HTML(f'<div class="su-section"><h3>{escape_html(titulo)}</h3>{corpo}</div>')


TOPO = f"""<header class="su-topbar">
  <div class="su-logo sm" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
  <b>SyncUp</b><span class="su-topbar-tag">v{VERSAO} · código aberto</span>
</header>"""


INICIO_TOPO = """<section class="su-hero">
  <div class="su-logo" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
  <div class="su-hero-text">
    <small>SEUS HISTÓRICOS DO SPOTIFY, LADO A LADO</small>
    <h1>Descubra com quem<br>você está em sintonia.</h1>
    <p>Compare, encontre o seu match e poste o resultado. Tudo roda neste computador.</p>
  </div>
</section>
<h3 class="su-home-h">O que dá para fazer</h3>"""


INICIO_RODAPE = """<section class="su-steps-home">
  <h3 class="su-home-h">Como funciona</h3>
  <ol>
    <li><b>1</b><span><strong>Pegue seus dados</strong>O Histórico Estendido do Spotify (ZIP), um login ou o usuário do ListenBrainz.</span></li>
    <li><b>2</b><span><strong>Envie e aperte o play</strong>O SyncUp compara rankings, horários e hábitos.</span></li>
    <li><b>3</b><span><strong>Compartilhe</strong>Baixe o story 1080×1920 e poste.</span></li>
  </ol>
</section>
<section class="su-open">
  <span>🔒 100% local</span><span>MIT · código aberto</span><span>ListenBrainz e MusicBrainz</span>
  <a href="https://github.com/Hazykiuu/SyncUp" target="_blank" rel="noopener">Ver no GitHub →</a>
</section>"""

# Aba de destino, sub-aba da Dupla (ou None), ícone, título, texto e cor de cada cartão.


RECURSOS = [
    ('dupla', None, '🎧', 'Dupla', 'Blend, identidades e rankings de duas pessoas.', '#1ed760'),
    (
        'dupla',
        'sintonia',
        '💞',
        'Em sintonia',
        'Quando vocês ouviram a mesma música ao mesmo tempo.',
        '#f573a0',
    ),
    ('match', None, '✨', 'Match', 'Junte a galera e descubra as melhores duplas.', '#c4b7ff'),
    ('match', None, '🎉', 'Playlist da festa', 'Músicas que agradam o grupo inteiro.', '#ffa42b'),
    ('wrapped', None, '📼', 'Wrapped', 'A sua vida inteira no Spotify, em stories.', '#4cc9f0'),
    ('grupo', None, '👥', 'Grupo', 'Até 6 perfis comparados numa matriz.', '#e8db5a'),
]


def _cartao_recurso(icone: str, titulo: str, texto: str, cor: str) -> gr.Button:
    """Cartão de recurso do Início; devolve o botão que leva à aba."""
    with gr.Column(elem_classes='su-feature', min_width=240):
        gr.HTML(
            f'<div class="su-feature-in" style="--c:{cor}">'
            f'<span class="su-feature-ico" aria-hidden="true">{icone}</span>'
            f'<h4>{escape_html(titulo)}</h4><p>{escape_html(texto)}</p></div>'
        )
        # Texto próprio por botão: leitores de tela não ouvem seis "Abrir" iguais.
        return gr.Button(f'Abrir {titulo} →', elem_classes='su-secondary', size='sm')


VAZIO = """<div class="su-blend"><div class="su-blend-hero" style="grid-template-columns:auto 1fr">
<div class="su-logo" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
<div class="su-blend-text"><div class="su-eyebrow">PRONTO PARA TOCAR</div>
<h2>Envie os dois históricos e aperte o play</h2>
<p>Use o Histórico Estendido (ZIP ou JSONs) de cada pessoa, ou experimente com dados fictícios.</p></div></div></div>"""


def criar_interface() -> gr.Blocks:
    """Constrói Gradio 5 com tema Spotify, CSS/JS externos e comparação de dupla/grupo."""
    habilitar_leitura_paralela()
    with gr.Blocks(
        theme=_tema(),
        css=CSS,
        js=JS,
        head=HEAD,
        title='SyncUp',
        analytics_enabled=False,
        delete_cache=(3600, 3600),
    ) as demo:
        gr.HTML(TOPO)
        # Opções avançadas numa gaveta lateral fechada: a página mostra só o que encanta.
        with gr.Sidebar(label='Opções de dados', open=False, elem_classes='su-sidebar'):
            gr.HTML(
                '<div class="su-side-head"><b>Opções de dados</b>'
                '<span>Valem para todas as abas.</span></div>'
            )
            fuso = gr.Dropdown(
                sorted(available_timezones()), value='America/Sao_Paulo', label='Fuso horário IANA'
            )
            ignorar_musicas = gr.Textbox(
                value='',
                placeholder='\n'.join(MUSICAS_IGNORADAS_PADRAO),
                lines=3,
                label='Músicas ignoradas · um nome por linha',
            )
            ignorar_artistas = gr.Textbox(
                value='', lines=3, label='Artistas ignorados · um nome por linha'
            )
            varios = gr.Dropdown(
                choices=[
                    ('Manter como artista agregado', 'manter'),
                    ('Ignorar coletâneas', 'ignorar'),
                ],
                value='manter',
                label='Various Artists',
            )
            disco = gr.Checkbox(value=False, label='Cache Parquet em disco · dependência opcional')
            deduplicar = gr.Checkbox(
                value=False, label='Remover eventos idênticos · UTC, duração, artista e música'
            )
            gr.Markdown(
                'Various Artists não identifica o intérprete real. Arquivos inteiros repetidos '
                'são rejeitados dentro do mesmo perfil.',
                elem_classes='su-note',
            )
            gr.Markdown(AVISO_TRACOS, elem_classes='su-note')
            with gr.Accordion('Meus dados', open=False, elem_classes='su-my-data-box'):
                gr.Markdown(
                    'O que o SyncUp guardou neste computador. Apagar não tem volta.',
                    elem_classes='su-note',
                )
                meus_dados_html = gr.HTML(resumo_html())
                perfil_apagar = gr.Dropdown(
                    choices=[p.stem for p in listar_perfis(PASTA_PERFIS)],
                    value=None,
                    label='Perfil do Spotify salvo',
                )
                apagar_btn = gr.Button('Apagar este perfil', variant='stop')
                limpar_btn = gr.Button('Limpar todo o cache', variant='stop')
                # Recebe o resultado do confirm() do navegador: cancelar não apaga nada.
                confirmado = gr.Checkbox(value=False, visible=False)
        opcoes = [fuso, ignorar_musicas, ignorar_artistas, varios, disco, deduplicar]
        with gr.Tabs(elem_classes='su-nav') as abas:
            with gr.Tab('Início', id='inicio'):
                gr.HTML(INICIO_TOPO)
                atalhos = []
                for linha in (RECURSOS[:3], RECURSOS[3:]):
                    with gr.Row(elem_classes='su-features'):
                        for aba, sub, icone, titulo, texto, cor in linha:
                            atalhos.append((aba, sub, _cartao_recurso(icone, titulo, texto, cor)))
                gr.HTML(INICIO_RODAPE)
                gr.HTML(PRIVACIDADE)
            with gr.Tab('Dupla', id='dupla'):
                estado = gr.State(value=None, time_to_live=3600)
                pastas = gr.State(value=[], time_to_live=3600, delete_callback=_limpar_exportacoes)
                with gr.Row(equal_height=True):
                    with gr.Column(elem_classes=['su-panel', 'a']):
                        gr.HTML(
                            '<div class="su-panel-title"><span class="su-avatar a">A</span>Primeiro perfil</div>'
                        )
                        na = gr.Textbox(value='Pessoa A', label='Nome do primeiro perfil')
                        fa = gr.File(
                            file_count='multiple',
                            file_types=['.zip', '.json'],
                            type='filepath',
                            label='Todas as partes do histórico de A',
                        )
                    with gr.Column(elem_classes=['su-panel', 'b']):
                        gr.HTML(
                            '<div class="su-panel-title"><span class="su-avatar b">B</span>Segundo perfil</div>'
                        )
                        nb = gr.Textbox(value='Pessoa B', label='Nome do segundo perfil')
                        fb = gr.File(
                            file_count='multiple',
                            file_types=['.zip', '.json'],
                            type='filepath',
                            label='Todas as partes do histórico de B',
                        )
                gr.Markdown(
                    'Cada painel representa uma pessoa; vários ZIPs/JSONs do painel serão unidos.',
                    elem_classes='su-note',
                )
                with gr.Row(equal_height=True):
                    comum = gr.Checkbox(value=True, label='Período coberto pelos dois históricos')
                    peso = gr.Dropdown(
                        choices=OPCOES_PONDERACAO,
                        value='bruta',
                        label='Ponderação do cosseno e Ruzicka',
                    )
                    with gr.Column(min_width=260):
                        botao = gr.Button(
                            'Comparar históricos', variant='primary', elem_classes='su-play'
                        )
                        demo_btn = gr.Button(
                            'Testar com dados fictícios', elem_classes='su-secondary'
                        )
                with gr.Column(visible=True) as vazio:
                    gr.HTML(VAZIO)
                with gr.Column(visible=False, elem_classes='su-results') as resultados:
                    resumo = gr.HTML()
                    with gr.Row(equal_height=True):
                        aa = gr.HTML()
                        ab = gr.HTML()
                    with gr.Tabs(elem_classes='su-subnav') as sub_dupla:
                        with gr.Tab('Wrapped', id='wrapped_dupla'):
                            wrapped_dupla = gr.HTML()
                        with gr.Tab('Em sintonia', id='sintonia'):
                            momentos = gr.HTML()
                            with gr.Row():
                                sintonia_btn = gr.Button(
                                    'Gerar story da sintonia', elem_classes='su-secondary'
                                )
                            sintonia_img = gr.Image(show_label=False, interactive=False)
                            sintonia_arquivo = gr.File(label='Baixar story PNG', interactive=False)
                            with gr.Accordion('Quase juntos: até 1 h de distância', open=False):
                                gr.Markdown(
                                    'Pares de plays com até 1 h entre os horários de fim (UTC), '
                                    'sem repetir eventos. Os totais de artista e de música são '
                                    'alternativos, não somáveis. Até 200 exemplos por tabela.',
                                    elem_classes='su-note',
                                )
                                momentos_a = gr.Dataframe(
                                    interactive=False,
                                    wrap=True,
                                    label='Pares de mesmo artista · exemplos',
                                )
                                momentos_m = gr.Dataframe(
                                    interactive=False,
                                    wrap=True,
                                    label='Pares de mesma música e artista · exemplos',
                                )
                        with gr.Tab('Rankings'):
                            corrida = gr.HTML()
                            with gr.Row(equal_height=True):
                                lista_aa = gr.HTML()
                                lista_ab = gr.HTML()
                            with gr.Row(equal_height=True):
                                lista_ma = gr.HTML()
                                lista_mb = gr.HTML()
                            conexoes = gr.Markdown()
                            with gr.Accordion('Tabelas completas · top 20', open=False):
                                with gr.Row():
                                    ta = gr.Dataframe(
                                        interactive=False, wrap=True, label='Artistas A · top 20'
                                    )
                                    tb = gr.Dataframe(
                                        interactive=False, wrap=True, label='Artistas B · top 20'
                                    )
                                with gr.Row():
                                    ma = gr.Dataframe(
                                        interactive=False, wrap=True, label='Músicas A · top 20'
                                    )
                                    mb = gr.Dataframe(
                                        interactive=False, wrap=True, label='Músicas B · top 20'
                                    )
                        with gr.Tab('Gráficos'):
                            _secao(
                                'Quem ouve quem',
                                'Participação dos artistas líderes nos plays de cada perfil.',
                            )
                            plot = gr.Plot(show_label=False, elem_classes='su-chart')
                            _secao('Horários e traços')
                            gr.Markdown(AVISO_TRACOS, elem_classes='su-note')
                            heatmap = gr.Plot(show_label=False, elem_classes='su-chart')
                            radar = gr.Plot(show_label=False, elem_classes='su-chart')
                            gr.Markdown(
                                f'Favoritos: top 2 ≥{fmt_pct(LIMIAR_FAVORITOS)}. Repeat: top 10 faixas ≥{fmt_pct(LIMIAR_REPEAT)}. '
                                f'Madrugada: 00h–05h59 ≥{fmt_pct(LIMIAR_MADRUGADA)}. Em amostras pequenas, top 10 tende a ser alto.',
                                elem_classes='su-note',
                            )
                            _secao('Onde vocês se diferenciam')
                            slope = gr.Plot(show_label=False, elem_classes='su-chart')
                            _secao('Mês a mês')
                            mensal = gr.Plot(show_label=False, elem_classes='su-chart')
                        with gr.Tab('Compartilhar'):
                            _secao('Cartão da dupla', 'PNG 1080×1350 gerado neste computador.')
                            criar_cartao = gr.Button('Gerar cartão PNG', elem_classes='su-play')
                            imagem = gr.Image(
                                type='filepath', interactive=False, label='Prévia do cartão'
                            )
                            png_download = gr.File(label='Baixar cartão PNG', interactive=False)
                            _secao('Ponte musical')
                            ponte = gr.Markdown()
                            _secao(
                                'Playlist em comum',
                                'Faixas que os dois ouviram. Os links abrem buscas no Spotify.',
                            )
                            playlist = gr.Dataframe(
                                interactive=False, wrap=True, label='Playlist comum · prévia'
                            )
                            exportar = gr.Button(
                                'Exportar playlist comum · CSV', elem_classes='su-secondary'
                            )
                            csv_download = gr.File(label='Baixar playlist CSV', interactive=False)
                    with gr.Accordion('Detalhes técnicos', open=False, elem_classes='su-tech'):
                        gr.Markdown(
                            'Contribuição por artista = aᵢ·bᵢ/(|a|·|b|); a soma é o cosseno, em '
                            'pontos percentuais e com a ponderação escolhida (100 líderes).',
                            elem_classes='su-note',
                        )
                        contrib = gr.Dataframe(
                            interactive=False, wrap=True, label='Contribuições ao cosseno'
                        )
                        gr.Markdown(
                            'Entropia = −Σp·ln(p)/ln(k); Gini = Σ(2i−k−1)xᵢ/(kΣx), com contagens '
                            'brutas dos artistas observados. Não medem diversidade de gêneros.',
                            elem_classes='su-note',
                        )
                        diversidade = gr.Dataframe(
                            interactive=False, label='Diversidade e desigualdade observadas'
                        )
                        stats = gr.Dataframe(
                            interactive=False, label='describe() · minutos por execução'
                        )
                        gr.Markdown(
                            'Descartes exclusivos: podcast → duração → data → identificação → '
                            'Various Artists → filtros → duplicados. SHA-256 identifica conteúdo, '
                            'não o dono.',
                            elem_classes='su-note',
                        )
                        diag = gr.Dataframe(interactive=False, wrap=True, label='Diagnóstico')
                saidas = [
                    estado,
                    resumo,
                    plot,
                    heatmap,
                    radar,
                    slope,
                    aa,
                    ab,
                    ta,
                    tb,
                    ma,
                    mb,
                    contrib,
                    playlist,
                    ponte,
                    momentos,
                    momentos_a,
                    momentos_m,
                    diversidade,
                    stats,
                    diag,
                    mensal,
                    conexoes,
                    csv_download,
                    imagem,
                    png_download,
                    corrida,
                    lista_aa,
                    lista_ab,
                    lista_ma,
                    lista_mb,
                    resultados,
                    vazio,
                    wrapped_dupla,
                ]
                botao.click(
                    executar_dupla,
                    [fa, fb, na, nb, comum, peso, *opcoes],
                    saidas,
                    api_name='comparar_dupla',
                    scroll_to_output=True,
                )
                demo_btn.click(carregar_demo, None, [fa, fb, na, nb], api_name=False)
                exportar.click(
                    baixar_playlist,
                    [estado, pastas],
                    [csv_download, pastas],
                    api_name='exportar_playlist',
                )
                criar_cartao.click(
                    baixar_cartao,
                    [estado, pastas],
                    [imagem, png_download, pastas],
                    api_name='gerar_cartao',
                )
                sintonia_btn.click(
                    baixar_cartao_sintonia,
                    [estado, pastas],
                    [sintonia_img, sintonia_arquivo, pastas],
                    api_name='baixar_sintonia',
                )
            with gr.Tab('Match', id='match'):
                gr.HTML(
                    '<div class="su-section"><h3>Quem combina com quem?</h3>'
                    '<p>Junte a galera por qualquer fonte. O SyncUp compara todos com todos, '
                    'forma as duplas que mais combinam e gera pôsteres prontos para postar.</p></div>'
                )
                with gr.Row(equal_height=True, elem_classes='su-sources'):
                    with gr.Column(elem_classes=['su-panel', 'a']):
                        gr.HTML(
                            '<div class="su-panel-title"><span class="su-avatar a">Z</span>'
                            'Histórico ZIP<small>sem limite</small></div>'
                        )
                        fm = gr.File(
                            file_count='multiple',
                            file_types=['.zip', '.json'],
                            type='filepath',
                            label='Um ZIP do Histórico Estendido por pessoa',
                        )
                        nm = gr.Textbox(lines=3, label='Nomes, um por linha, na ordem dos arquivos')
                    with gr.Column(elem_classes=['su-panel', 'c']):
                        gr.HTML(
                            '<div class="su-panel-title"><span class="su-avatar c">L</span>'
                            'ListenBrainz<small>sem limite · só o usuário</small></div>'
                            '<p class="su-note">Código aberto. Crie uma conta grátis em '
                            '<a href="https://listenbrainz.org" target="_blank" rel="noopener">'
                            'listenbrainz.org</a> e conecte o Spotify uma vez em '
                            '<i>Settings → Music services</i>. Ninguém precisa de Client ID.</p>'
                        )
                        lb = gr.Textbox(
                            lines=3,
                            label='Usuários do ListenBrainz, um por linha',
                            placeholder='nicollas\nbia_musica',
                        )
                    with gr.Column(elem_classes=['su-panel', 'b']):
                        gr.HTML(
                            '<div class="su-panel-title"><span class="su-avatar b">S</span>'
                            'Login com Spotify<small>até 5 · cadastrados</small></div>'
                        )
                        nome_sp = gr.Textbox(
                            label='Nome de quem vai entrar', placeholder='Ex.: Bia'
                        )
                        conectar = gr.Button('Conectar com Spotify', elem_classes='su-secondary')
                        conhecidos = gr.State(value=perfis_salvos())
                        salvos = gr.CheckboxGroup(
                            choices=perfis_salvos(),
                            value=perfis_salvos(),
                            label='Perfis coletados pelo Spotify',
                        )
                        recarregar = gr.Button('Atualizar lista', elem_classes='su-secondary')
                        with gr.Accordion('Configurar (só quem criou o app)', open=False):
                            cid = gr.Textbox(
                                value=os.environ.get('SPOTIFY_CLIENT_ID', ''),
                                label='Client ID do app no Spotify',
                                placeholder='Cole o Client ID do Developer Dashboard',
                            )
                            gr.HTML(
                                '<ol class="su-steps">'
                                '<li>Em <b>developer.spotify.com/dashboard</b>, com conta '
                                '<b>Premium</b>, crie um app e marque só <b>Web API</b>.</li>'
                                f'<li>Redirect URI: <code>{escape_html(REDIRECT_PADRAO)}</code></li>'
                                '<li>Em <b>User Management</b>, cadastre o e-mail da conta '
                                'Spotify de cada amigo (máx. 5).</li>'
                                '<li>Cole o Client ID acima ou defina <code>SPOTIFY_CLIENT_ID</code>.'
                                '</li></ol><p class="su-note">Regra do Spotify para apps pessoais. '
                                'Sem cadastro, use o ListenBrainz ou o ZIP. O token nunca é salvo.</p>'
                            )
                generos_mb = gr.Checkbox(
                    value=False,
                    label='Comparar também o estilo (gêneros do MusicBrainz)',
                    info='Envia só nomes de artistas, 1 por segundo. Na 1ª vez, ~25 s por pessoa.',
                )
                buscar = gr.Button(
                    'Encontrar os matches', variant='primary', elem_classes='su-play'
                )
                estado_m = gr.State(value=None, time_to_live=3600)
                pastas_m = gr.State(
                    value=[], time_to_live=3600, delete_callback=_limpar_exportacoes
                )
                with gr.Column(visible=False, elem_classes='su-results') as match_resultados:
                    with gr.Tabs():
                        with gr.Tab('Revelação'):
                            match_stories = gr.HTML()
                        with gr.Tab('Duplas'):
                            match_cartoes = gr.HTML()
                        with gr.Tab('Todos com todos'):
                            match_plot = gr.Plot(show_label=False, elem_classes='su-chart')
                            match_ranking = gr.Dataframe(
                                interactive=False, wrap=True, label='Com quem cada um mais combina'
                            )
                        with gr.Tab('Playlist da festa'):
                            gr.Markdown(
                                'Até 30 músicas que cobrem o gosto de todo o grupo, equilibrando '
                                'quem ainda tem pouco. Baixe em CSV ou XSPF (formato aberto, abre '
                                'no VLC). Os links são buscas no Spotify.',
                                elem_classes='su-note',
                            )
                            festa_btn = gr.Button(
                                'Montar playlist da festa', elem_classes='su-secondary'
                            )
                            festa_lista = gr.HTML()
                            festa_arquivos = gr.File(
                                label='Baixar CSV e XSPF', file_count='multiple', interactive=False
                            )
                        with gr.Tab('Para postar'):
                            gr.Markdown(
                                'Story 1080×1920 para o Instagram, gerado neste computador.',
                                elem_classes='su-note',
                            )
                            dupla_m = gr.Dropdown(label='Escolha a dupla', choices=[])
                            cartao_m_btn = gr.Button(
                                'Gerar story da dupla', elem_classes='su-secondary'
                            )
                            cartao_m_img = gr.Image(show_label=False, interactive=False)
                            cartao_m_arquivo = gr.File(label='Baixar cartão PNG', interactive=False)
                conectar.click(
                    None,
                    [cid, nome_sp],
                    None,
                    js="(cid, nome) => { window.open('/spotify/login?client_id=' + "
                    "encodeURIComponent(cid || '') + '&nome=' + encodeURIComponent(nome || ''), "
                    "'_blank'); }",
                    api_name=False,
                )
                recarregar.click(
                    atualizar_perfis, [salvos, conhecidos], [salvos, conhecidos], api_name=False
                )
                # Cada aba nova do navegador vê os perfis salvos depois que o servidor subiu.
                demo.load(
                    atualizar_perfis, [salvos, conhecidos], [salvos, conhecidos], api_name=False
                )
                buscar.click(
                    executar_match,
                    [fm, nm, salvos, *opcoes, generos_mb, lb],
                    [
                        match_cartoes,
                        match_plot,
                        match_ranking,
                        match_resultados,
                        match_stories,
                        estado_m,
                        dupla_m,
                    ],
                    api_name='encontrar_matches',
                    scroll_to_output=True,
                    # Um Match por vez: o MusicBrainz aceita 1 consulta/s para o app todo.
                    concurrency_limit=1,
                )
                festa_btn.click(
                    baixar_festa,
                    [estado_m, pastas_m],
                    [festa_lista, festa_arquivos, pastas_m],
                    api_name='playlist_festa',
                )
                cartao_m_btn.click(
                    baixar_cartao_match,
                    [estado_m, dupla_m, pastas_m],
                    [cartao_m_img, cartao_m_arquivo, pastas_m],
                    api_name='baixar_cartao_match',
                )
            with gr.Tab('Wrapped', id='wrapped'):
                gr.HTML(
                    '<div class="su-section"><h3>Seu Wrapped da vida toda</h3>'
                    '<p>Envie o Histórico Estendido de uma pessoa (todas as partes) e veja a vida '
                    'inteira no Spotify em stories: artista e música da vida, anos, recordes, '
                    'relógio musical, hábitos e o seu arquétipo de escuta.</p></div>'
                )
                estado_w = gr.State(value=None, time_to_live=3600)
                pastas_w = gr.State(
                    value=[], time_to_live=3600, delete_callback=_limpar_exportacoes
                )
                with gr.Row(equal_height=True):
                    with gr.Column(elem_classes=['su-panel', 'a']):
                        nw = gr.Textbox(value='', label='Seu nome', placeholder='Ex.: Carlos')
                        fw = gr.File(
                            file_count='multiple',
                            file_types=['.zip', '.json'],
                            type='filepath',
                            label='Histórico completo (ZIP ou todos os JSONs)',
                        )
                    with gr.Column(min_width=260):
                        gerar_w = gr.Button(
                            'Gerar meu Wrapped', variant='primary', elem_classes='su-play'
                        )
                        demo_w = gr.Button(
                            'Testar com dados fictícios', elem_classes='su-secondary'
                        )
                        gr.Markdown(
                            'Usa as **Opções de dados** do topo (fuso e filtros). '
                            '"Vida toda" = todo o período do histórico enviado.',
                            elem_classes='su-note',
                        )
                with gr.Column(visible=False, elem_classes='su-results') as wrapped_resultados:
                    with gr.Row(elem_classes='su-wrapped-row'):
                        stories_w = gr.HTML()
                        detalhe_w = gr.HTML()
                    with gr.Row():
                        baixar_w = gr.Button(
                            'Baixar story do resumo · PNG 1080×1920', elem_classes='su-secondary'
                        )
                    with gr.Row():
                        imagem_w = gr.Image(
                            type='filepath', interactive=False, label='Prévia do story'
                        )
                        arquivo_w = gr.File(label='Baixar story PNG', interactive=False)
                gerar_w.click(
                    executar_wrapped,
                    [fw, nw, *opcoes],
                    [estado_w, stories_w, detalhe_w, wrapped_resultados, imagem_w, arquivo_w],
                    api_name='gerar_wrapped',
                    scroll_to_output=True,
                )
                demo_w.click(carregar_demo_wrapped, None, [fw, nw], api_name=False)
                baixar_w.click(
                    baixar_wrapped,
                    [estado_w, pastas_w],
                    [imagem_w, arquivo_w, pastas_w],
                    api_name='baixar_wrapped',
                )
            with gr.Tab('Grupo', id='grupo'):
                gr.Markdown(
                    f'Regras: top 2 artistas ≥{fmt_pct(LIMIAR_FAVORITOS)}; top 10 faixas ≥{fmt_pct(LIMIAR_REPEAT)}; '
                    f'madrugada 00h–05h59 ≥{fmt_pct(LIMIAR_MADRUGADA)}. As proporções aparecem na tabela. '
                    + AVISO_TRACOS,
                    elem_classes='su-note',
                )
                gr.Markdown(
                    'Cada arquivo desta aba representa **uma pessoa**. Se houver várias partes por pessoa, '
                    'use `comparar_grupo()` com `EntradaPerfil` pelo Python. Na matriz comum, todas as células usam a mesma janela global.',
                    elem_classes='su-note',
                )
                with gr.Row(equal_height=True):
                    with gr.Column(elem_classes=['su-panel', 'a']):
                        fg = gr.File(
                            file_count='multiple',
                            file_types=['.zip', '.json'],
                            type='filepath',
                            label='3 a 6 históricos · um arquivo por pessoa',
                        )
                    with gr.Column(elem_classes=['su-panel', 'b']):
                        ng = gr.Textbox(
                            lines=6, label='Um nome por linha, na mesma ordem dos arquivos'
                        )
                with gr.Row(equal_height=True):
                    cg = gr.Checkbox(value=True, label='Período comum a todos os perfis')
                    pg = gr.Dropdown(
                        choices=OPCOES_PONDERACAO,
                        value='bruta',
                        label='Ponderação do cosseno do grupo',
                    )
                    grupo = gr.Button('Comparar grupo', variant='primary', elem_classes='su-play')
                with gr.Column(visible=False, elem_classes='su-results') as grupo_resultados:
                    grupo_cartoes = gr.HTML()
                    grupo_texto = gr.Markdown(elem_classes='su-note')
                    grupo_plot = gr.Plot(show_label=False, elem_classes='su-chart')
                    grupo_matriz = gr.Dataframe(
                        interactive=False, label='Matriz · valores em percentual'
                    )
                    grupo_perfis = gr.Dataframe(
                        interactive=False, wrap=True, label='Perfis e arquétipos'
                    )
                    grupo_diag = gr.Dataframe(
                        interactive=False, wrap=True, label='Diagnóstico de cada perfil'
                    )
                grupo.click(
                    executar_grupo,
                    [fg, ng, cg, pg, *opcoes],
                    [
                        grupo_plot,
                        grupo_matriz,
                        grupo_perfis,
                        grupo_diag,
                        grupo_texto,
                        grupo_cartoes,
                        grupo_resultados,
                    ],
                    api_name='comparar_grupo',
                    scroll_to_output=True,
                )
        for aba, sub, atalho in atalhos:
            if sub is None:
                atalho.click(lambda a=aba: gr.Tabs(selected=a), None, abas, api_name=False)
            else:
                atalho.click(
                    lambda a=aba, s=sub: (gr.Tabs(selected=a), gr.Tabs(selected=s)),
                    None,
                    [abas, sub_dupla],
                    api_name=False,
                )
        apagar_btn.click(
            apagar_perfil_salvo,
            perfil_apagar,
            [meus_dados_html, perfil_apagar],
            js="(nome) => nome && confirm('Apagar o perfil de ' + nome + '? Não dá para desfazer.')"
            " ? nome : ''",
            api_name=False,
        ).then(atualizar_perfis, [salvos, conhecidos], [salvos, conhecidos], api_name=False)
        limpar_btn.click(
            limpar_cache,
            confirmado,
            [meus_dados_html, perfil_apagar],
            js="() => confirm('Limpar todo o cache? Os históricos serão lidos de novo na próxima vez.')",
            api_name=False,
        )
        demo.load(atualizar_meus_dados, None, [meus_dados_html, perfil_apagar], api_name=False)
        gr.Markdown(
            'Plays: ≥30 segundos. Horas e describe(): todas as execuções válidas. '
            'O Ruzicka usa pesos absolutos e é sensível ao volume de escuta. ' + AVISO_TRACOS,
            elem_classes=['su-note', 'su-footer'],
        )
    return demo.queue(default_concurrency_limit=CONCORRENCIA)
