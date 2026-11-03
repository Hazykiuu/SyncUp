"""Camada visual; as métricas continuam no app.py."""
from html import escape
import re
import pandas as pd
import plotly.express as px

CSS = """
html{scroll-behavior:smooth} body,.gradio-container{background:#101112!important;color:#f5f5f5!important}
.gradio-container{width:100%!important;max-width:none!important;padding:24px 32px 48px!important;margin:0!important;font-family:Inter,Arial,sans-serif!important}
.gradio-container footer{display:none!important} .gradio-container .gap{gap:20px!important}
.hero{display:flex;align-items:center;justify-content:space-between;padding:8px 0 24px;border-bottom:1px solid #2c3033;margin-bottom:8px;gap:20px}
.brand{display:flex;align-items:center;gap:15px}.brand-mark{display:grid;place-items:center;width:52px;height:52px;background:#1db954;border-radius:16px;color:#0b2012;font-size:30px;font-weight:900}
.hero h1{font-size:clamp(26px,3vw,42px);font-weight:800;letter-spacing:-1.5px;margin:0!important}.hero p{margin:5px 0 0!important;color:#a9b1b6;font-size:15px}
.pill{display:inline-flex;align-items:center;gap:8px;color:#b9c5bd;border:1px solid #35413a;background:#19241d;border-radius:100px;padding:8px 14px;font-size:12px;white-space:nowrap}
.dot{width:7px;height:7px;border-radius:50%;background:#1db954}
.upload-panel{border:1px solid #303438!important;border-radius:20px!important;padding:20px!important;background:#191c1f!important;transition:border-color .2s,box-shadow .2s!important}
.upload-panel:hover{border-color:#53675a!important;box-shadow:0 8px 25px #0002}.profile-label{font-size:12px;color:#9aa7a0;letter-spacing:1.5px;margin:0 0 12px;font-weight:700}
#comparar{background:#1db954!important;color:#081d0e!important;border:0!important;border-radius:12px!important;font-weight:700!important;min-height:48px!important;transition:transform .18s,background .18s,box-shadow .18s!important}
#comparar:hover{background:#27cd64!important;box-shadow:0 6px 22px #1db95430;transform:translateY(-2px)}#comparar:active{transform:scale(.985)}
.section-label{font-size:12px;letter-spacing:1.4px;color:#a5adb2;margin:10px 0 14px;text-transform:uppercase;font-weight:700}
.empty-state{padding:30px;border:1px dashed #39403e;border-radius:20px;background:#151a17;color:#aab8ad}.empty-state strong{display:block;color:#e7efe9;font-size:22px;margin-bottom:8px}.empty-state p{margin:0}
.metric-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.metric{background:#1a1d20;border:1px solid #313638;padding:22px;border-radius:18px;animation:enter .45s ease both}.metric.primary{background:#183523;border-color:#285e3b}
.metric small{color:#adb8b0;font-size:12px;letter-spacing:.8px;text-transform:uppercase}.metric b{display:block;font-size:clamp(30px,3vw,50px);font-weight:800;letter-spacing:-1.5px;margin:7px 0;color:#eef7f0}.metric p{margin:0;color:#a7b2ab;font-size:13px}
.period-note{font-size:13px;color:#9aa6a0;margin:14px 2px}.status-note{padding:12px 16px;border-radius:12px;background:#202a23;border:1px solid #37443b;font-size:13px;color:#c6d0c8;margin-top:12px}
.identity{border:1px solid #31363a;background:#191c20;border-radius:20px;padding:24px;animation:enter .5s ease both}.identity.violet{--accent:#b1a5ff}.identity.green{--accent:#1db954}.identity h2{font-size:22px!important;color:#fafafa;margin:4px 0 18px!important}.identity .eyebrow{color:var(--accent);font-size:12px;letter-spacing:1px;font-weight:700}
.identity .mini-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:20px}.mini-stat b{display:block;font-size:22px;color:#fff}.mini-stat span{font-size:11px;color:#aab0b6}
.trait{margin:16px 0 0;padding-top:15px;border-top:1px solid #30363a}.trait-title{display:flex;justify-content:space-between;gap:10px;align-items:center}.trait-title strong{font-size:14px;color:#eff1f3}.trait-title span{color:var(--accent);font-size:12px}.trait p{color:#aab4bb;font-size:12px;line-height:1.6;margin:8px 0 0}.track{height:5px;border-radius:10px;background:#32383b;margin-top:10px;overflow:hidden}.track i{display:block;height:100%;width:var(--value);background:var(--accent);border-radius:10px;animation:fill .8s ease both}
.rule-note{font-size:11px;color:#929ca5;margin-top:18px;line-height:1.6}.chart-panel{border:1px solid #303438!important;border-radius:20px!important;overflow:hidden;background:#191c20!important}.tabs{margin-top:24px!important}.tab-nav button{border-radius:10px!important;transition:background .2s!important}
@keyframes enter{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}@keyframes fill{from{max-width:0}to{max-width:100%}}
@media(min-width:1500px){.gradio-container{padding-left:48px!important;padding-right:48px!important}}
@media(max-width:760px){.gradio-container{padding:16px!important}.hero{align-items:flex-start}.hero>.pill{display:none}.metric-grid{grid-template-columns:1fr}.metric b{font-size:36px}.identity{padding:18px}.brand-mark{width:42px;height:42px}.upload-panel{padding:15px!important}}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation:none!important;transition:none!important;scroll-behavior:auto!important}}
"""

def formatar(numero):
    return f'{numero:,.0f}'.replace(',', '.')

def perfil_card(dados, plays, nome, cor, artistas=None, faixas=None):
    if artistas is None:
        artistas = plays.groupby('artista').size()
    if faixas is None:
        faixas = plays.groupby(['musica','artista']).size()
    concentracao = artistas.nlargest(2).sum()/len(plays)
    repeticao = faixas.nlargest(10).sum()/len(plays)
    horas = plays.data.dt.hour
    madrugada = ((horas>=0)&(horas<6)).mean()
    principal = 'Fiel aos favoritos' if concentracao>=.6 else 'Gosto distribuído'
    repeat = 'Mestre do repeat' if repeticao>=.4 else 'Repertório variado'
    noturno = 'Coruja musical' if madrugada>=.4 else 'Fora da madrugada'
    def trait(titulo,valor,texto):
        return f'<div class="trait"><div class="trait-title"><strong>{titulo}</strong><span>{valor:.1%}</span></div><div class="track"><i style="--value:{valor*100:.2f}%"></i></div><p>{texto}</p></div>'
    return f'''<article class="identity {cor}"><div class="eyebrow">IDENTIDADE MUSICAL</div><h2>{escape(nome or 'Perfil')}</h2>
    <div class="mini-stats"><div class="mini-stat"><b>{formatar(len(plays))}</b><span>plays ≥30s</span></div><div class="mini-stat"><b>{dados.minutos.sum()/60:,.1f}</b><span>horas · todas as execuções</span></div><div class="mini-stat"><b>{formatar(len(artistas))}</b><span>artistas</span></div></div>
    {trait(principal,concentracao,'Participação dos dois artistas líderes nas reproduções.')}
    {trait(repeat,repeticao,'Participação das dez faixas líderes nas reproduções. Em amostras pequenas, este valor tende a ser alto.')}
    {trait(noturno,madrugada,'Reproduções entre 00h e 05h59, no horário de Brasília.')}
    <p class="rule-note">Regras experimentais: favoritos ≥60%; repeat ≥40%; madrugada ≥40%. Descrevem este recorte de escuta; não inferem personalidade.</p></article>'''

def resumo_html(texto):
    valores = re.findall(r'(\d+\.\d+)%',texto)[:3]
    titulos = [('Similaridade musical','Cosseno · frequência por artista'),('Artistas em comum','Jaccard · todos os artistas'),('Favoritos compartilhados','Jaccard · Top 20')]
    cards = ''.join(f'<div class="metric {"primary" if i==0 else ""}"><small>{titulo}</small><b>{valor.replace(".",",")}%</b><p>{sub}</p></div>' for i,((titulo,sub),valor) in enumerate(zip(titulos,valores)))
    periodo = next((x.removeprefix('Período: ') for x in texto.splitlines() if x.startswith('Período: ')), '')
    aviso = next((x.strip('*') for x in texto.splitlines() if x.startswith('**Os ')), '')
    return f'<div class="metric-grid">{cards}</div><div class="period-note">{escape(periodo)} · Similaridade calculada sobre o histórico de escuta.</div><div class="status-note">{escape(aviso)}</div>'

def grafico_artistas(longo,ordem):
    fig=px.bar(longo,x='Participação (%)',y='Artista',color='Perfil',orientation='h',barmode='group',color_discrete_sequence=['#1db954','#b1a5ff'],category_orders={'Artista':list(ordem)},height=690)
    fig.update_layout(template='plotly_dark',paper_bgcolor='#191c20',plot_bgcolor='#191c20',font=dict(family='Arial',size=13,color='#dbe2e6'),margin=dict(l=20,r=30,t=65,b=40),legend=dict(orientation='h',y=1.08,x=0),transition_duration=500,bargap=.24)
    fig.update_xaxes(gridcolor='#30383e',ticksuffix='%');fig.update_yaxes(title=None)
    fig.update_traces(hovertemplate='%{y}<br>%{x:.2f}% das reproduções<extra>%{fullData.name}</extra>')
    return fig

def grafico_meses(a,b,nomes):
    # Exibe apenas meses com registros, sem inventar zeros para lacunas do histórico.
    partes=[]
    for dados,nome in zip((a,b),nomes):
        # Agrupar por números; formatar apenas os meses resultantes, não cada play.
        mes = dados.data.dt.year * 100 + dados.data.dt.month
        mensal=dados.groupby(mes).minutos.sum().div(60).rename('Horas').rename_axis('Mês').reset_index()
        mensal['Mês'] = mensal['Mês'].map(lambda valor: f'{valor//100:04d}-{valor%100:02d}')
        mensal['Perfil']=nome;partes.append(mensal)
    fig=px.line(pd.concat(partes),x='Mês',y='Horas',color='Perfil',markers=True,color_discrete_sequence=['#1db954','#b1a5ff'],height=400)
    fig.update_layout(template='plotly_dark',paper_bgcolor='#191c20',plot_bgcolor='#191c20',margin=dict(l=30,r=30,t=30,b=50),legend=dict(orientation='h',y=1.12),hovermode='x unified',transition_duration=500)
    fig.update_xaxes(nticks=10,gridcolor='#30383e');fig.update_yaxes(gridcolor='#30383e')
    return fig

def criar_interface():
    import gradio as gr
    from app import comparar
    import zipfile,json
    vazio='<div class="empty-state"><strong>Dois históricos. Novas conexões.</strong><p>Importe os arquivos acima para descobrir a afinidade e a identidade musical de cada perfil.</p></div>'
    espera=lambda nome,cor: f'<article class="identity {cor}"><div class="eyebrow">IDENTIDADE MUSICAL</div><h2>{nome}</h2><p style="color:#aab4bb">Após a comparação, seus hábitos ganham forma aqui.</p><div class="trait"><strong>Favoritos · Repetição · Madrugada</strong><p>Três características calculadas a partir das reproduções, com a justificativa de cada resultado.</p></div></article>'
    with gr.Blocks(theme=gr.themes.Base(primary_hue='green',neutral_hue='slate'),css=CSS,title='SyncUp',js="() => { document.body.classList.add('dark'); }") as demo:
        gr.HTML('<header class="hero"><div class="brand"><div class="brand-mark">♫</div><div><h1>SyncUp</h1><p>Compare o que vocês ouvem. Descubra o que conecta vocês.</p></div></div><div class="pill"><span class="dot"></span>Protótipo v0.4 · UCL</div></header>')
        with gr.Row():
            with gr.Column(elem_classes='upload-panel'):
                gr.HTML('<div class="profile-label">01 / PRIMEIRO PERFIL</div>')
                na=gr.Textbox(value='Carlos',label='Nome')
                fa=gr.File(label='Histórico Spotify · ZIP ou JSON',file_types=['.zip','.json'],type='filepath')
            with gr.Column(elem_classes='upload-panel'):
                gr.HTML('<div class="profile-label">02 / SEGUNDO PERFIL</div>')
                nb=gr.Textbox(value='Henrique Paiva',label='Nome')
                fb=gr.File(label='Histórico Spotify · ZIP ou JSON',file_types=['.zip','.json'],type='filepath')
        with gr.Row():
            comum=gr.Checkbox(value=True,label='Usar somente o período coberto pelos dois históricos',scale=3)
            botao=gr.Button('Descobrir afinidade →',elem_id='comparar',scale=1)
        resultado=gr.HTML(vazio)
        with gr.Row():
            with gr.Column(scale=3,min_width=450):
                gr.HTML('<div class="section-label">Seus artistas, lado a lado</div>')
                plot=gr.Plot(label='Participação na escuta · passe o mouse para ver os valores',elem_classes='chart-panel')
            with gr.Column(scale=2,min_width=320):
                gr.HTML('<div class="section-label">Arquétipos do período</div>')
                aa=gr.HTML(espera('Primeiro perfil','green'))
                ab=gr.HTML(espera('Segundo perfil','violet'))
        with gr.Tabs():
            with gr.Tab('Rankings de artistas'):
                with gr.Row():
                    ta=gr.Dataframe(label='Top 20 · primeiro perfil',interactive=False,wrap=True)
                    tb=gr.Dataframe(label='Top 20 · segundo perfil',interactive=False,wrap=True)
            with gr.Tab('Rankings de músicas'):
                with gr.Row():
                    ma=gr.Dataframe(label='Top 20 · primeiro perfil',interactive=False,wrap=True)
                    mb=gr.Dataframe(label='Top 20 · segundo perfil',interactive=False,wrap=True)
            with gr.Tab('Conexões'):
                cx=gr.Markdown()
            with gr.Tab('Evolução da escuta'):
                gr.Markdown('Horas por mês, considerando todas as execuções válidas no período. Meses com dados ausentes não recebem zeros artificiais.')
                mensal=gr.Plot(elem_classes='chart-panel')
            with gr.Tab('Estatísticas · describe()'):
                stats=gr.Dataframe(interactive=False)
            with gr.Tab('Diagnóstico'):
                gr.Markdown('Mesmo nome não significa mesmo conteúdo; similaridade de 100% não prova arquivos idênticos. Confira os arquivos recebidos e suas coberturas.')
                diagnostico=gr.Dataframe(interactive=False)
        gr.Markdown('Plays: execuções ≥30 segundos. Horas: todas as execuções válidas. Os arquétipos seguem regras experimentais e descrevem hábitos de escuta.',elem_classes='rule-note')
        def executar(*args):
            try:
                r=list(comparar(*args));r[0]=resumo_html(r[0]);return r
            except (ValueError,zipfile.BadZipFile,json.JSONDecodeError) as erro:
                raise gr.Error(str(erro))
        botao.click(executar,[fa,fb,na,nb,comum],[resultado,plot,ta,tb,ma,mb,aa,ab,cx,stats,diagnostico,mensal],show_progress='full',concurrency_limit=1)
    return demo
