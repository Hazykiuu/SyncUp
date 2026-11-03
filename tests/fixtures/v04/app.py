"""SyncUp: métricas com Python e Pandas para preparação e EDA."""
import json
import hashlib
import textwrap
import zipfile
import re
from pathlib import Path
from functools import lru_cache
import pandas as pd


def _chave_arquivo(arquivo):
    caminho = Path(arquivo).resolve()
    estado = caminho.stat()
    return str(caminho), estado.st_size, estado.st_mtime_ns, estado.st_ctime_ns, estado.st_ino


@lru_cache(maxsize=4)
def _historico(chave):
    # Cache limitado a quatro arquivos; alterações no arquivo invalidam a chave.
    caminho = Path(chave[0])
    registros = []
    campos = ['ts', 'ms_played', 'master_metadata_track_name', 'master_metadata_album_artist_name']
    encontrados = set()

    def selecionar(conteudo):
        if isinstance(conteudo, list):
            for item in conteudo:
                if isinstance(item, dict) and 'ms_played' in item:
                    if len(encontrados) < len(campos):
                        encontrados.update(set(campos).intersection(item))
                    # Não construir uma tabela com metadados que nunca serão usados.
                    registros.append((item.get('ts'), item.get('ms_played'),
                                      item.get('master_metadata_track_name'),
                                      item.get('master_metadata_album_artist_name')))

    if caminho.suffix.lower() == '.zip':
        with zipfile.ZipFile(caminho) as pacote:
            for nome in pacote.namelist():
                if nome.lower().endswith('.json'):
                    conteudo = json.loads(pacote.read(nome))
                    selecionar(conteudo)
    else:
        conteudo = json.loads(caminho.read_text(encoding='utf-8-sig'))
        selecionar(conteudo)
    if not set(campos).issubset(encontrados):
        raise ValueError('Use o histórico estendido de áudio do Spotify (ZIP ou JSON).')
    dados = pd.DataFrame.from_records(registros, columns=campos)
    dados = dados.rename(columns={'master_metadata_track_name': 'musica', 'master_metadata_album_artist_name': 'artista'})
    dados['data'] = pd.to_datetime(dados['ts'], utc=True, errors='coerce').dt.tz_convert('America/Sao_Paulo')
    dados['ms_played'] = pd.to_numeric(dados['ms_played'], errors='coerce')
    # Retemos apenas campos necessários: não usamos IP ou outros dados de dispositivo.
    dados = dados[['data', 'ms_played', 'musica', 'artista']].dropna()
    dados = dados[dados['ms_played'] >= 0].copy()
    # Os mesmos nomes aparecem milhares de vezes: limpar cada nome único uma vez.
    for coluna in ('musica', 'artista'):
        nomes = {nome: nome.strip() if isinstance(nome, str) else None
                 for nome in dados[coluna].unique()}
        dados[coluna] = dados[coluna].map(nomes)
    excluidas = {nome for nome in dados['musica'].dropna().unique()
                 if re.sub(r'[^\w]', '', nome.casefold()) == 'falsaesperança'}
    dados = dados[~dados['musica'].isin(excluidas)].copy()
    dados['minutos'] = dados['ms_played'] / 60000
    h = hashlib.sha256()
    with caminho.open('rb') as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b''):
            h.update(bloco)
    return dados, h.hexdigest()


def carregar(arquivo):
    # O notebook recebe uma cópia: editar sua tabela não altera o cache do app.
    return _historico(_chave_arquivo(arquivo))[0].copy()


def limpar_cache():
    """Libera os históricos guardados na memória desta sessão."""
    _historico.cache_clear()


def metricas(a, b):
    # Aceita dicionários ou Series. Artistas ausentes têm frequência zero.
    a, b = dict(a.items()), dict(b.items())
    ca = {artista for artista, valor in a.items() if valor > 0}
    cb = {artista for artista, valor in b.items() if valor > 0}
    produto = sum(float(a[x]) * float(b[x]) for x in a.keys() & b.keys())
    norma_a = sum(float(valor) ** 2 for valor in a.values()) ** 0.5
    norma_b = sum(float(valor) ** 2 for valor in b.values()) ** 0.5
    denominador = norma_a * norma_b
    cosseno = max(0.0, min(1.0, produto / denominador)) if denominador else None
    jaccard = len(ca & cb) / len(ca | cb) if ca | cb else None
    return cosseno, jaccard


def arquetipo(contagens):
    total = contagens.sum()
    concentracao = contagens.nlargest(2).sum() / total
    nome = 'Fiel aos favoritos' if concentracao >= .60 else 'Gosto distribuído'
    return f'**{nome}** — seus dois artistas líderes representam **{concentracao:.1%}** das reproduções no recorte. Regra experimental: concentração ≥60% recebe Fiel aos favoritos.'


def tabela(series, nome):
    frame = series.sort_values(ascending=False).head(20).rename('Reproduções').reset_index()
    frame.columns = [nome, 'Reproduções']
    return frame


def comparar(arquivo_a, arquivo_b, nome_a, nome_b, periodo_comum=True):
    if not arquivo_a or not arquivo_b:
        raise ValueError('Selecione um arquivo de histórico para cada pessoa.')
    (a, hash_a), (b, hash_b) = (_historico(_chave_arquivo(arquivo_a)),
                              _historico(_chave_arquivo(arquivo_b)))
    if a.empty or b.empty:
        raise ValueError('Um dos históricos não contém registros de músicas válidos.')
    historicos_iguais = a.reset_index(drop=True).equals(b.reset_index(drop=True))
    hashes = [hash_a, hash_b]
    diagnostico = pd.DataFrame({
        'Perfil': [nome_a, nome_b],
        'Arquivo': [Path(arquivo_a).name, Path(arquivo_b).name],
        'SHA-256 do arquivo': hashes,
        'Registros de músicas antes do recorte': [len(a),len(b)],
        'Início do histórico': [str(a.data.min()),str(b.data.min())],
        'Fim do histórico': [str(a.data.max()),str(b.data.max())],
    })
    cobertura_a, cobertura_b = (a.data.min(), a.data.max()), (b.data.min(), b.data.max())
    if periodo_comum:
        inicio = max(cobertura_a[0], cobertura_b[0])
        fim = min(cobertura_a[1], cobertura_b[1])
        if inicio > fim:
            raise ValueError('Os históricos não possuem período de cobertura em comum. Desmarque a opção para comparar períodos diferentes.')
        a, b = a[a.data.between(inicio, fim)], b[b.data.between(inicio, fim)]
        periodo = f'{inicio:%d/%m/%Y} a {fim:%d/%m/%Y} (horário de Brasília)'
    else:
        periodo = 'Históricos completos, com coberturas potencialmente diferentes.'
    # Tempo ouvido considera todas as execuções; rankings contam ≥30 segundos.
    va, vb = a[a.ms_played >= 30000], b[b.ms_played >= 30000]
    if va.empty or vb.empty:
        raise ValueError('Não há reproduções de pelo menos 30 segundos para os dois perfis nesse período.')
    ra, rb = va.groupby('artista').size(), vb.groupby('artista').size()
    faixas_a = va.groupby(['musica', 'artista']).size()
    faixas_b = vb.groupby(['musica', 'artista']).size()
    total_a, total_b = len(va), len(vb)
    cosseno, jaccard = metricas(ra, rb)
    topa, topb = set(ra.nlargest(20).index), set(rb.nlargest(20).index)
    top_jaccard = len(topa & topb) / len(topa | topb)
    nome_a, nome_b = nome_a.strip() or 'Pessoa A', nome_b.strip() or 'Pessoa B'
    resumo = f'''## Similaridade musical: {cosseno:.1%}
**Cosseno:** compara o padrão de frequência por artista. **Jaccard geral:** {jaccard:.1%}. **Jaccard do Top 20:** {top_jaccard:.1%}.

Período: {periodo}

| Perfil | Plays ≥30s | Horas ouvidas (todas as execuções) | Artistas com plays ≥30s |
|---|---:|---:|---:|
| {nome_a} | {len(va):,} | {a.minutos.sum()/60:.1f} | {len(ra)} |
| {nome_b} | {len(vb):,} | {b.minutos.sum()/60:.1f} | {len(rb)} |

O percentual mede semelhança dos dados musicais. Valores ausentes de escuta são tratados como zero; ausência no arquivo não prova que a pessoa não gosta do artista.
    '''
    # Alinhar todos os artistas antes de selecionar os maiores pesos combinados.
    todos = ra.index.union(rb.index)
    pesos = ra.reindex(todos, fill_value=0)/ra.sum() + rb.reindex(todos, fill_value=0)/rb.sum()
    if hashes[0] == hashes[1]:
        resumo += '\n\n**Os arquivos recebidos possuem bytes idênticos (SHA-256 igual). Confira os arquivos selecionados na aba Diagnóstico.**'
    elif historicos_iguais:
        resumo += '\n\n**Os ZIPs são diferentes, mas os registros de músicas após a limpeza são idênticos. Isso não identifica o dono dos arquivos.**'
    elif a.reset_index(drop=True).equals(b.reset_index(drop=True)):
        resumo += '\n\n**Os históricos completos são diferentes; apenas os registros no período selecionado coincidem.**'
    else:
        resumo += '\n\n**Os históricos recebidos possuem registros diferentes.**'
    resumo = textwrap.dedent(resumo)
    selecionados = pesos.nlargest(12).index
    grafico = pd.DataFrame({'Artista': selecionados, f'A · {nome_a}': ra.reindex(selecionados, fill_value=0)/ra.sum()*100, f'B · {nome_b}': rb.reindex(selecionados, fill_value=0)/rb.sum()*100})
    longo = grafico.melt(id_vars='Artista', var_name='Perfil', value_name='Participação (%)')
    musicasa = faixas_a.sort_values(ascending=False).head(20).rename('Reproduções').reset_index()
    musicasb = faixas_b.sort_values(ascending=False).head(20).rename('Reproduções').reset_index()
    comuns = sorted(set(ra.index) & set(rb.index), key=lambda x: (-(ra[x]/total_a+rb[x]/total_b), x))
    conexoes = '**Artistas em comum:** ' + ', '.join(comuns[:20])
    conexoes += '\n\n**Favoritos de A ausentes no recorte de B:** ' + ', '.join(x for x in ra.sort_values(ascending=False).index if x not in rb.index)[:700]
    conexoes += '\n\n**Favoritos de B ausentes no recorte de A:** ' + ', '.join(x for x in rb.sort_values(ascending=False).index if x not in ra.index)[:700]
    estatisticas = pd.concat({f'A · {nome_a}': a[['minutos']].describe(), f'B · {nome_b}': b[['minutos']].describe()}, axis=1)
    estatisticas.columns = ['Minutos por execução · A', 'Minutos por execução · B']
    from ui import perfil_card, grafico_artistas, grafico_meses
    fig = grafico_artistas(longo, selecionados)
    card_a = perfil_card(a, va, nome_a, 'green', ra, faixas_a)
    card_b = perfil_card(b, vb, nome_b, 'violet', rb, faixas_b)
    mensal = grafico_meses(a, b, [f'A · {nome_a}', f'B · {nome_b}'])
    return resumo, fig, tabela(ra, 'Artista'), tabela(rb, 'Artista'), musicasa, musicasb, card_a, card_b, conexoes, estatisticas.reset_index(names='Medida'), diagnostico, mensal


def criar_interface():
    from ui import criar_interface as construir
    return construir()


if __name__ == '__main__':
    criar_interface().launch(inbrowser=True)
