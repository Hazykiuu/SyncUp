"""App web de ponta a ponta: exemplo dos quatro modos, pré-leitura e "menos movimento"."""

import json
import re
import zipfile
from pathlib import Path

import pytest
from playwright.sync_api import expect

SITE = Path(__file__).resolve().parents[2] / 'site'

pytestmark = pytest.mark.navegador

TEMPO = 45_000  # a Dupla e a Batalha montam no Worker; o CI é mais lento que o PC


def _abrir_exemplo(pagina, url, modo):
    pagina.goto(f'{url}/app/#{modo}')
    # Os quatro modos ficam montados; só o visível aparece para o get_by_role.
    pagina.get_by_role('button', name='Ver um exemplo').click()
    player = pagina.locator('.resultado .st-player:visible').first
    expect(player).to_be_visible(timeout=TEMPO)
    return player


@pytest.mark.parametrize('modo', ['wrapped', 'dupla', 'batalha', 'match'])
def test_exemplo_chega_aos_stories_e_avanca(page, site_url, modo):
    player = _abrir_exemplo(page, site_url, modo)
    contador = player.locator('.st-contador')
    expect(contador).to_have_text(re.compile(r'^\d+/\d+$'))
    player.focus()
    player.press(' ')  # pausa: o relógio não avança sozinho no meio do teste
    expect(player).to_have_class(re.compile(r'\bpausado\b'))
    atual, total = map(int, contador.inner_text().split('/'))
    assert total > 1
    player.press('ArrowRight')
    expect(contador).to_have_text(f'{min(atual + 1, total)}/{total}')


def test_batalha_com_semente_repete_o_sorteio(nova_pagina, site_url):
    """Batalha v2: ?semente=N fixa os 10 temas sorteados; "Ficaram fora" só diz o que faltou, agrupado."""
    sorteios = []
    for _ in range(2):
        pagina = nova_pagina()
        pagina.goto(f'{site_url}/app/?semente=7#batalha')
        pagina.get_by_role('button', name='Ver um exemplo').click()
        rodadas = pagina.locator('#resultado-batalha .rodadas > li h3')
        expect(rodadas).to_have_count(10, timeout=TEMPO)
        sorteios.append(rodadas.all_inner_texts())
        nota = pagina.locator('#resultado-batalha .nota', has_text='Ficaram fora do sorteio')
        expect(nota).to_contain_text('porque')
        expect(nota).not_to_contain_text('empataram')
    assert sorteios[0] == sorteios[1]


def test_pre_leitura_mostra_periodo_e_reproducoes(page, site_url):
    page.goto(f'{site_url}/app/#wrapped')
    # Os quatro modos ficam montados: o cartão certo é o da tela visível.
    tela = page.get_by_role('region', name='Seu histórico')
    tela.locator('input[type=file]').first.set_input_files(SITE / 'app' / 'demo-wrapped.zip')
    painel = tela.locator('dl.telemetria')
    expect(painel).to_be_visible(timeout=TEMPO)
    expect(painel.locator('.tl-periodo dd')).to_have_text(re.compile(r'.+ → .+'))
    expect(painel).to_contain_text('Reproduções')
    expect(tela.get_by_text('Lido neste aparelho')).to_be_visible()


def test_menos_movimento_troca_direto(nova_pagina, site_url):
    pagina = nova_pagina(reduced_motion='reduce')
    player = _abrir_exemplo(pagina, site_url, 'wrapped')
    expect(player).to_be_focused()  # sem a transição, o foco vai direto para o player


def test_app_sem_rolagem_lateral_no_celular(nova_pagina, site_url):
    pagina = nova_pagina(viewport={'width': 375, 'height': 812})
    _abrir_exemplo(pagina, site_url, 'wrapped')
    largura = pagina.evaluate('document.documentElement.scrollWidth - innerWidth')
    assert largura <= 0, f'rola {largura}px para o lado'


def _chegar_da_pagina_inicial(pagina, url):
    pagina.add_init_script("try { sessionStorage.setItem('syncup-entrada', '1') } catch {}")
    pagina.goto(f'{url}/app/#wrapped')


def test_chegada_logo_pousa_e_some(page, site_url):
    _chegar_da_pagina_inicial(page, site_url)
    expect(page.locator('.pouso')).to_be_attached()
    expect(page.locator('.pouso')).to_have_count(0, timeout=5_000)  # entrou em sintonia e pousou
    expect(page.locator('body')).to_have_class(re.compile('sintonizado'))
    # a logo de verdade volta quando a cópia pousa em cima dela
    expect(page.locator('#app .marca .logo:visible').first).to_have_css('opacity', '1')


def test_chegada_com_menos_movimento_sem_logo_grande(nova_pagina, site_url):
    pagina = nova_pagina(reduced_motion='reduce')
    _chegar_da_pagina_inicial(pagina, site_url)
    expect(pagina.locator('.pouso')).to_have_count(0)
    expect(pagina.locator('#principal .app-cabeca:visible')).to_be_visible()


def test_abrir_o_app_direto_sem_entrada(page, site_url):
    page.goto(f'{site_url}/app/#wrapped')
    expect(page.locator('.pouso')).to_have_count(0)


def test_wrapped_com_historico_curto_avisa_em_vez_dos_stories(page, site_url, tmp_path):
    curto = tmp_path / 'curto.json'
    curto.write_text(
        '[{"ts": "2023-12-29T03:00:00Z", "ms_played": 200000,'
        ' "master_metadata_track_name": "Faixa", "master_metadata_album_artist_name": "Banda"}]',
        encoding='utf-8',
    )
    page.goto(f'{site_url}/app/#wrapped')
    tela = page.get_by_role('region', name='Seu histórico')
    tela.locator('input[type=file]').first.set_input_files(curto)
    expect(tela.get_by_text('Lido neste aparelho')).to_be_visible(timeout=TEMPO)
    page.get_by_role('button', name='Montar meu Wrapped').click()
    expect(page.locator('[role=alert]:visible')).to_contain_text(
        'Histórico curto demais', timeout=TEMPO
    )
    expect(page.locator('.resultado .st-player:visible')).to_have_count(0)


def test_app_abre_sem_o_unpkg(page, site_url):
    page.route('https://unpkg.com/**', lambda rota: rota.abort())
    page.goto(f'{site_url}/app/#wrapped')
    expect(page.get_by_role('button', name='Montar meu Wrapped')).to_be_attached(timeout=TEMPO)


def test_foco_do_teclado_nao_fica_sob_a_barra_no_celular(nova_pagina, site_url):
    """R2-02 (WCAG 2.4.11): nenhum elemento focado fica inteiro atrás da barra de modos."""
    pagina = nova_pagina(viewport={'width': 390, 'height': 844}, reduced_motion='reduce')
    _abrir_exemplo(pagina, site_url, 'dupla').focus()
    coberto = """() => { const e = document.activeElement;
      if (!e || e === document.body || e.closest('.nav-app')) return null;
      const r = e.getBoundingClientRect(), n = document.querySelector('.nav-app').getBoundingClientRect();
      return r.top >= n.top - 1 && r.bottom <= n.bottom + 1 ? e.innerText.slice(0, 40) : null; }"""
    cobertos = []
    for _ in range(80):
        pagina.keyboard.press('Tab')
        pagina.wait_for_timeout(60)
        if texto := pagina.evaluate(coberto):
            cobertos.append(texto)
    assert cobertos == []


@pytest.mark.parametrize('nome, mensagem', [
    ('quebrado.zip', 'inválido ou incompleto'),
    ('grande.zip', 'Use o app para PC'),
    ('outro.json', 'Use o histórico estendido de áudio do Spotify'),
])  # fmt: skip
def test_erro_de_entrada_aparece_na_tela(page, site_url, tmp_path, nome, mensagem):
    """R1-06: os erros de leitura do arquivo chegam à tela, num alerta."""
    arquivo = tmp_path / nome
    if nome == 'quebrado.zip':
        arquivo.write_bytes(b'PK\x03\x04isto nao e um zip')
    elif nome == 'outro.json':
        arquivo.write_text('[{"x": 1}]', encoding='utf-8')
    else:
        with zipfile.ZipFile(arquivo, 'w', zipfile.ZIP_DEFLATED) as pacote:
            pacote.writestr('Streaming_History_Audio_2023.json', '[]' + ' ' * (65 * 2**20))
    page.goto(f'{site_url}/app/#wrapped')
    tela = page.get_by_role('region', name='Seu histórico')
    tela.locator('input[type=file]').first.set_input_files(arquivo)
    expect(tela.get_by_role('alert').first).to_contain_text(mensagem, timeout=TEMPO)


def _historico(pasta, nome, semente):
    """Plays fictícios (cada pessoa com um total diferente, para a Batalha não empatar em tudo), com IDs de 22 caracteres como os do Spotify."""
    eventos = [
        {'ts': f'2023-12-{1 + i % 28:02d}T{i % 24:02d}:{i % 60:02d}:00Z', 'ms_played': 200_000,
         'master_metadata_track_name': f'Faixa {(i + semente) % 7}',
         'master_metadata_album_artist_name': f'Banda {(i + semente) % 5}',
         'spotify_track_uri': 'spotify:track:' + chr(65 + i % 7) * 22}
        for i in range(300 + 60 * semente)
    ]  # fmt: skip
    caminho = pasta / f'{nome}.json'
    caminho.write_text(json.dumps(eventos), encoding='utf-8')
    return caminho


@pytest.mark.parametrize('ligado', [True, False])
@pytest.mark.parametrize('modo, pessoas, botao', [
    ('wrapped', 1, 'Montar meu Wrapped'),
    ('dupla', 2, 'Comparar históricos'),
    ('match', 2, 'Ver quem combina'),
    ('batalha', 3, 'Começar a batalha'),
])  # fmt: skip
def test_capas_e_som_decide_o_que_sai_do_aparelho(
    page, site_url, tmp_path, modo, pessoas, botao, ligado
):
    """R3-05: com a opção desligada, mostrar um resultado não pede nada para fora."""
    pedidos = []
    page.on(
        'request',
        lambda r: r.url.startswith((site_url, 'blob:', 'data:', 'https://unpkg.com'))
        or pedidos.append(r.url),
    )
    page.goto(f'{site_url}/app/#{modo}')
    opcao = page.get_by_role('checkbox', name=re.compile('^Capas e som'))
    expect(opcao).to_be_checked()
    if not ligado:
        opcao.uncheck()
        page.reload()  # a escolha fica guardada neste navegador
        expect(opcao).not_to_be_checked()
    if modo == 'wrapped':
        cartoes = page.get_by_role('region', name='Seu histórico')
    else:
        cartoes = page.locator('#principal section.pessoa:visible')
    for i in range(pessoas):
        cartao = cartoes if modo == 'wrapped' else cartoes.nth(i)
        if modo != 'wrapped':
            cartao.locator('input.entrada').first.fill(f'Pessoa {i}')
        cartao.locator('input[type=file]').first.set_input_files(_historico(tmp_path, f'p{i}', i))
    page.wait_for_timeout(1_500)  # a pré-leitura libera o botão
    page.get_by_role('button', name=re.compile(botao)).locator('visible=true').last.click()
    expect(page.locator('.resultado .st-player:visible').first).to_be_visible(timeout=TEMPO)
    page.wait_for_timeout(2_000)
    assert bool(pedidos) is ligado, pedidos[:3]


@pytest.mark.parametrize('pessoa_a, pessoa_b, artista', [
    ('Rafa', 'Lu', 'Orquestra Filarmonica Imaginaria de Instrumentos Antigos e Sintetizadores'),
    ('Maria Eduarda Albuquerque Figueiredo dos Santos', 'Ana Clara Vasconcelos Bittencourt', 'Banda Longa'),
])  # fmt: skip
def test_stories_da_dupla_cabem_com_nomes_longos(
    nova_pagina, site_url, tmp_path, pessoa_a, pessoa_b, artista
):
    """R2-04: nenhum texto sai da moldura do story."""
    pagina = nova_pagina(viewport={'width': 390, 'height': 844}, reduced_motion='reduce')
    pagina.goto(f'{site_url}/app/#dupla')
    pessoas = pagina.locator('#principal section.pessoa:visible')
    for j, nome in enumerate([pessoa_a, pessoa_b]):
        eventos = [
            {'ts': f'2023-{1 + i % 12:02d}-{1 + i % 27:02d}T{i % 24:02d}:00:00Z', 'ms_played': 200_000,
             'master_metadata_track_name': f'Faixa {(i * (j + 3)) % 30}', 'spotify_track_uri': f'spotify:track:{i % 40}',
             'master_metadata_album_artist_name': artista if i % 3 == 0 else f'Banda {(i * (j + 5)) % 12}'}
            for i in range(400)
        ]  # fmt: skip
        caminho = tmp_path / f'{j}.json'
        caminho.write_text(json.dumps(eventos), encoding='utf-8')
        pessoas.nth(j).locator('input.entrada').first.fill(nome)
        pessoas.nth(j).locator('input[type=file]').first.set_input_files(caminho)
    pagina.get_by_role('button', name=re.compile('Comparar hist')).first.click()
    player = pagina.locator('.resultado .st-player:visible').first
    expect(player).to_be_visible(timeout=TEMPO)
    player.focus()
    player.press(' ')
    fora = """() => { const p = [...document.querySelectorAll('.st-player')].find((e) => e.offsetParent);
      const f = p.querySelector('.st-slot.ativo').getBoundingClientRect(), tipo = p.querySelector('.st-slot.ativo section').className;
      return [...p.querySelectorAll('.st-slot.ativo *')].filter((e) => {
        if (e.childElementCount || !e.textContent.trim() || e.closest('.st-avatares')) return false;
        const b = e.getBoundingClientRect();
        return b.width && Math.max(f.top - b.top, b.bottom - f.bottom, f.left - b.left, b.right - f.right) > 1;
      }).map((e) => `${tipo}: ${e.textContent.trim().slice(0, 20)}`); }"""
    sobre_o_contador = """() => { const p = [...document.querySelectorAll('.st-player')].find((e) => e.offsetParent);
      const c = p.querySelector('.st-contador').getBoundingClientRect(), s = p.querySelector('.st-slot.ativo');
      if (!s.querySelector('.st-cabe')) return [];
      return [...s.querySelectorAll('.st-conteudo *')].filter((e) => !e.childElementCount && e.textContent.trim()
        && e.getBoundingClientRect().width && e.getBoundingClientRect().top < c.bottom - 1).map((e) => 'sob o contador: ' + e.textContent.trim().slice(0, 20)); }"""
    ruins = []
    for _ in range(int(player.locator('.st-contador').inner_text().split('/')[1])):
        pagina.wait_for_timeout(250)
        ruins += pagina.evaluate(fora) + pagina.evaluate(sobre_o_contador)
        player.press('ArrowRight')
    assert ruins == []


def test_sem_rede_o_painel_do_som_nao_fica_preparando(nova_pagina, site_url):
    """R2-05: quando os trechos não vêm, o painel e o aviso dizem a mesma coisa."""
    pagina = nova_pagina(viewport={'width': 1280, 'height': 900})
    _abrir_exemplo(pagina, site_url, 'wrapped')
    expect(pagina.get_by_text(re.compile('buscar os trechos')).first).to_be_visible(timeout=TEMPO)
    painel = pagina.locator('.palco-agora:visible .palco-faixa small').first
    expect(painel).to_have_text('Stories sem som')


@pytest.mark.parametrize('modo', ['wrapped', 'dupla', 'batalha', 'match'])
def test_da_para_cancelar_o_calculo(page, site_url, modo):
    """R2-06: um Worker que não responde deixa o cálculo parado; "Cancelar" volta à tela de envio."""
    rota = '**/*-worker.js'
    page.route(rota, lambda r: r.fulfill(body='', content_type='text/javascript'))
    page.goto(f'{site_url}/app/#{modo}')
    exemplo = page.get_by_role('button', name='Ver um exemplo').locator('visible=true')
    exemplo.click()
    processando = page.locator('.processando:visible')
    expect(processando).to_be_visible(timeout=TEMPO)
    processando.get_by_role('button', name='Cancelar').click()
    expect(processando).to_have_count(0)
    expect(page.locator('[role=alert]:visible')).to_have_count(0)
    expect(exemplo).to_be_enabled()
    page.unroute(rota)
    exemplo.click()  # o envio seguinte funciona
    expect(page.locator('.resultado .st-player:visible').first).to_be_visible(timeout=TEMPO)


def test_match_diz_em_que_escala_esta_a_nota(page, site_url):
    """R2-07: 7% pode ser "Boa": cada par diz onde fica o topo da escala."""
    page.goto(f'{site_url}/app/#match')
    page.get_by_role('button', name='Ver um exemplo').locator('visible=true').click()
    expect(page.locator('.dueto:visible').first).to_be_visible(timeout=TEMPO)
    pares = page.locator('.dueto-par:visible').all()
    assert pares
    for par in pares:
        expect(par.locator('.dueto-escala')).to_contain_text('25% já é sintonia rara')
    expect(page.get_by_text('Como a nota é calculada').first).to_be_visible()


def test_transparencia_reduzida_tira_todo_o_vidro(page, site_url):
    """R2-08: com "transparência reduzida" no sistema, nada na tela fica borrado, nem o dock."""
    page.context.new_cdp_session(page).send(
        'Emulation.setEmulatedMedia',
        {'features': [{'name': 'prefers-reduced-transparency', 'value': 'reduce'}]},
    )
    page.set_viewport_size({'width': 390, 'height': 844})
    _abrir_exemplo(page, site_url, 'wrapped')
    page.wait_for_timeout(1_500)  # a transição para o resultado troca os elementos
    page.evaluate("document.querySelector('.resultado .st-player').scrollIntoView()")
    expect(page.locator('.dock.visivel')).to_be_visible()
    borrados = page.evaluate("""() => [...document.querySelectorAll('*')].filter((e) => {
      const c = getComputedStyle(e), r = e.getBoundingClientRect();
      return c.backdropFilter !== 'none' && r.width && r.bottom > 0 && r.top < innerHeight && c.visibility !== 'hidden' && +c.opacity > 0;
    }).map((e) => String(e.className))""")
    assert borrados == []


def test_match_nao_fica_preso_quando_o_exemplo_nao_baixa(page, site_url):
    """Revisão da v1.28: a falha vira alerta; depois de cancelar, nada aparece."""
    page.route('**/demo-*.zip', lambda r: r.fulfill(status=500))
    page.goto(f'{site_url}/app/#match')
    exemplo = page.get_by_role('button', name='Ver um exemplo').locator('visible=true')
    exemplo.click()
    expect(page.locator('[role=alert]:visible')).to_be_visible(timeout=TEMPO)
    expect(page.locator('.processando:visible')).to_have_count(0)
    page.unroute('**/demo-*.zip')
    page.evaluate("""() => { const real = window.fetch; window.fetch = (u, o) => String(u).includes('demo-')
      ? new Promise((ok) => setTimeout(() => ok(new Response('', { status: 500 })), 1500)) : real(u, o); }""")
    exemplo.click()
    page.locator('.processando:visible').get_by_role('button', name='Cancelar').click()
    page.wait_for_timeout(2_500)
    expect(page.locator('[role=alert]:visible')).to_have_count(0)


def test_sem_armazenamento_a_caixa_desligada_ainda_vale(page, site_url, tmp_path):
    """Revisão da v1.28: se o navegador não deixa guardar a escolha, ela vale nesta visita."""
    page.add_init_script(
        "Storage.prototype.setItem = Storage.prototype.getItem = () => { throw new Error('bloqueado'); };"
    )
    pedidos = []
    page.on(
        'request', lambda r: r.url.startswith((site_url, 'blob:', 'data:')) or pedidos.append(r.url)
    )
    page.goto(f'{site_url}/app/#wrapped')
    page.get_by_role('checkbox', name=re.compile('^Capas e som')).uncheck()
    tela = page.get_by_role('region', name='Seu histórico')
    tela.locator('input[type=file]').first.set_input_files(_historico(tmp_path, 'p', 0))
    page.wait_for_timeout(1_500)
    page.get_by_role('button', name='Montar meu Wrapped').click()
    expect(page.locator('.resultado .st-player:visible').first).to_be_visible(timeout=TEMPO)
    page.wait_for_timeout(2_000)
    assert pedidos == []


def test_painel_do_som_de_um_modo_nao_muda_o_de_outro(nova_pagina, site_url):
    """Revisão da v1.28: os quatro modos ficam montados; "sem som" é de cada um."""
    pagina = nova_pagina(viewport={'width': 1280, 'height': 900})
    _abrir_exemplo(pagina, site_url, 'wrapped')
    painel = pagina.locator('.palco-agora:visible .palco-faixa small').first
    expect(painel).to_have_text('Stories sem som', timeout=TEMPO)
    pagina.route(re.compile('apple[.]com'), lambda r: None)  # a busca da Dupla fica no ar
    pagina.locator('.nav-item[href="#dupla"]').click()
    expect(pagina.locator('.app-corpo')).to_have_attribute('data-modo', 'dupla')
    pagina.wait_for_timeout(1_000)  # a troca de modo ainda mostra os dois lados por um instante
    pagina.get_by_role('button', name='Ver um exemplo').locator('visible=true').click()
    expect(pagina.locator('.resultado .st-player:visible').first).to_be_visible(timeout=TEMPO)
    pagina.wait_for_timeout(1_000)
    pagina.locator('.nav-item[href="#wrapped"]').click()
    expect(painel).to_have_text('Stories sem som')
