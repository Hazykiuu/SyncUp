// Números dos temas novos da Batalha v2. Os 10 de antes continuam vindo do calcularWrapped, que não muda
// (paridade com o Python). Roda na fase 2 do Worker, uma pessoa por vez; depois disso as colunas são descartadas.
// Regras comuns: `utc` é o FIM do play (o Last.fm grava uts + ms), então ordem, sessões e pausas usam o
// início (utc − ms); horas e datas usam `local` (o fim, na hora local); "plays" são as reproduções de 30 s ou
// mais, e minutos e horas contam todas; dado que falta é null (o tema sai), nunca 0.
import { TEMPO_MINIMO_PLAY_MS } from './calculo.js';

const MIN = 60_000, HORA = 60 * MIN, DIA = 24 * HORA;
const SESSAO = 30 * MIN; // pausa a partir da qual começa outra sessão
const SEIS_MESES = 182 * DIA;
const MINIMO_CONHECIDOS = 0.5; // como no Wrapped: o campo precisa vir em metade dos eventos
const CELULAR = new Set(['Android', 'iOS']), COMPUTADOR = new Set(['Windows', 'macOS', 'Linux', 'Navegador']);
const somar = (mapa, k, v = 1) => mapa.set(k, (mapa.get(k) || 0) + v);
const pct = (parte, total) => (parte * 100) / total;
const maximo = (valores) => { let m = 0; for (const v of valores) if (v > m) m = v; return m; };
const vezes100 = (v) => (v === null ? null : v * 100);

// `d`: o calcularWrapped do mesmo recorte; `contagens`: plays por artista; `antes`: artista → { local (primeira vez),
// ultimo (início do último play) } do que a pessoa já tinha ouvido antes do recorte.
export function medidasNovas(c, d, contagens, antes = new Map()) {
  const n = c.utc.length, plays = d.plays;
  const datas = new Map(); // dia local → [mês corrido (ano * 12 + mês), mês, dia do mês], uma conta por dia
  const data = (dia) => {
    let x = datas.get(dia);
    if (!x) { const t = new Date(dia * DIA); x = [t.getUTCFullYear() * 12 + t.getUTCMonth(), t.getUTCMonth() + 1, t.getUTCDate()]; datas.set(dia, x); }
    return x;
  };

  // Todas as reproduções: minutos por dia e por mês, aparelho, período e início de cada uma.
  const msDia = new Map(), msMes = new Map(), aparelhos = new Map(), inicio = new Float64Array(n);
  let primeiroDia = Infinity, ultimoDia = -Infinity, comAparelho = 0;
  for (let i = 0; i < n; i++) {
    const dia = Math.floor(c.local[i] / DIA);
    if (dia < primeiroDia) primeiroDia = dia;
    if (dia > ultimoDia) ultimoDia = dia;
    somar(msDia, dia, c.ms[i]);
    somar(msMes, data(dia)[0], c.ms[i]);
    if (c.plataforma[i] !== null) { somar(aparelhos, c.plataforma[i]); comAparelho++; }
    inicio[i] = c.utc[i] - c.ms[i];
  }

  const diaDe = (ano, mes, dia) => Date.UTC(ano, mes - 1, dia) / DIA;
  const cobre = (de, ate) => de >= primeiroDia && ate <= ultimoDia; // o período passa pela data inteira
  const cobreNatal = (ano) => cobre(diaDe(ano, 12, 24), diaDe(ano, 12, 26));
  const cobreVirada = (ano) => cobre(diaDe(ano, 12, 31), diaDe(ano + 1, 1, 1));

  // Plays: por dia, por música, por artista, dia da semana e datas especiais.
  const playsDia = new Map(), artistasDia = new Map(), pares = new Map(), playsPar = [], parDe = new Int32Array(n).fill(-1);
  const artistas = new Map(); // artista → { primeiro, ultimo (local), meses, musicas }
  let sextou = 0, segunda = 0, natal = 0, virada = 0, pMin = Infinity, pMax = -Infinity;
  for (let i = 0; i < n; i++) {
    if (c.ms[i] < TEMPO_MINIMO_PLAY_MS) continue;
    const l = c.local[i], dia = Math.floor(l / DIA), [mesCorrido, mes, diaMes] = data(dia);
    const hora = Math.floor((l - dia * DIA) / HORA), semana = (((dia + 3) % 7) + 7) % 7; // 0 = segunda
    const art = c.artista[i];
    somar(playsDia, dia);
    let doDia = artistasDia.get(dia);
    if (!doDia) artistasDia.set(dia, (doDia = new Set()));
    doDia.add(art);
    let porArtista = pares.get(c.musica[i]);
    if (!porArtista) pares.set(c.musica[i], (porArtista = new Map()));
    let id = porArtista.get(art);
    if (id === undefined) { id = playsPar.length; porArtista.set(art, id); playsPar.push(0); }
    playsPar[id]++;
    parDe[i] = id;
    let a = artistas.get(art);
    if (!a) artistas.set(art, (a = { primeiro: antes.get(art)?.local ?? l, ultimo: l, meses: new Set(), musicas: new Set() }));
    if (l < a.primeiro) a.primeiro = l;
    if (l > a.ultimo) a.ultimo = l;
    a.meses.add(mesCorrido);
    a.musicas.add(id);
    if (semana === 4 && hora >= 18) sextou++;
    if (semana === 0) segunda++;
    const ano = (mesCorrido - mes + 1) / 12; // mesCorrido conta os meses a partir do 0
    if (mes === 12 && diaMes >= 24 && diaMes <= 26 && cobreNatal(ano)) natal++;
    if (((mes === 12 && diaMes === 31) && cobreVirada(ano)) || ((mes === 1 && diaMes === 1) && cobreVirada(ano - 1))) virada++;
    if (l < pMin) pMin = l;
    if (l > pMax) pMax = l;
  }

  // Na ordem do início: sessões e pausas (com o maior fim até ali, porque plays se sobrepõem),
  // a mesma música em sequência (só plays: um pulo curto no meio não quebra) e os reencontros.
  const ordem = new Uint32Array(n).map((_, i) => i).sort((x, y) => inicio[x] - inicio[y] || x - y);
  let sessoes = 0, maiorSessao = 0, maiorPausa = 0, comecoSessao = 0, fim = -Infinity;
  let seguidas = 0, maisSeguidas = 0, parAnterior = -1;
  const ultimoPlay = new Map(), reencontrados = new Set();
  for (const i of ordem) {
    if (inicio[i] - fim >= SESSAO || sessoes === 0) {
      if (sessoes) maiorSessao = Math.max(maiorSessao, fim - comecoSessao);
      sessoes++;
      comecoSessao = inicio[i];
    }
    if (fim > -Infinity) maiorPausa = Math.max(maiorPausa, inicio[i] - fim);
    fim = Math.max(fim, c.utc[i]);
    if (parDe[i] < 0) continue;
    seguidas = parDe[i] === parAnterior ? seguidas + 1 : 1;
    parAnterior = parDe[i];
    if (seguidas > maisSeguidas) maisSeguidas = seguidas;
    const art = c.artista[i], anterior = ultimoPlay.get(art) ?? antes.get(art)?.ultimo;
    if (anterior !== undefined && inicio[i] - anterior >= SEIS_MESES) reencontrados.add(art);
    ultimoPlay.set(art, inicio[i]);
  }
  maiorSessao = Math.max(maiorSessao, fim - comecoSessao);

  // Natal e virada só valem se o período passa por pelo menos um inteiro: de 24 a 26/12, ou 31/12 e 1º/1 seguinte.
  const anos = [];
  for (let ano = new Date(primeiroDia * DIA).getUTCFullYear(); ano <= new Date(ultimoDia * DIA).getUTCFullYear(); ano++) anos.push(ano);
  const temNatal = anos.some(cobreNatal), temVirada = anos.some(cobreVirada);

  const porHora = d.plays_por_hora;
  const entropia = porHora.reduce((s, v) => (v ? s - (v / plays) * Math.log(v / plays) : s), 0);
  const mes0 = data(Math.floor(pMin / DIA))[0], meses = data(Math.floor(pMax / DIA))[0] - mes0;
  let novos = 0, antigo = 0, fidelidade = 0, obra = 0, faro = 0, raizes = 0;
  for (const [art, a] of artistas) {
    if (data(Math.floor(a.primeiro / DIA))[0] > mes0) novos++;
    antigo = Math.max(antigo, Math.floor(a.ultimo / DIA) - Math.floor(a.primeiro / DIA));
    fidelidade = Math.max(fidelidade, a.meses.size);
    obra = Math.max(obra, a.musicas.size);
    if (a.primeiro >= pMax - SEIS_MESES) faro += contagens.get(art);
    if (a.primeiro < pMin + SEIS_MESES) raizes += contagens.get(art);
  }
  const umAno = pMax - pMin >= 365 * DIA; // as duas janelas de 6 meses não se cruzam
  const top10 = [...contagens.values()].sort((x, y) => y - x).slice(0, 10).reduce((s, v) => s + v, 0);
  // Aparelho: um play perdido (menos de 1% do que tem aparelho) não conta como mais um tipo.
  const comAparelhos = comAparelho / n >= MINIMO_CONHECIDOS;
  const tipos = new Map(); // celular e computador juntam os sistemas; TV e "Outro" contam sozinhos
  for (const [k, v] of aparelhos) somar(tipos, CELULAR.has(k) ? 'celular' : COMPUTADOR.has(k) ? 'computador' : k, v);
  const fatia = (grupo) => pct([...aparelhos].reduce((s, [k, v]) => s + (grupo.has(k) ? v : 0), 0), comAparelho);
  const h = d.habitos;
  const diasComMusica = msDia.size;

  return {
    metralhadora: maximo(playsDia.values()),
    cruzeiro: (d.horas * 60) / diasComMusica,
    buffet: maximo([...artistasDia.values()].map((s) => s.size)),
    umavez: pct(playsPar.filter((v) => v === 1).length, playsPar.length),
    visita: pct([...contagens.values()].filter((v) => v === 1).length, contagens.size),
    elenco: pct(contagens.size, plays),
    disco: maisSeguidas,
    hino: d.top_musicas[0].plays,
    panelinha: pct(top10, plays),
    playlist: d.medidas.repeticao * 100,
    obra,
    madrugador: d.periodos['Manhã'] * 100,
    almoco: pct(porHora[12] + porHora[13], plays),
    tarde: pct(porHora[17] + porHora[18], plays),
    noite: d.periodos.Noite * 100,
    espalhado: (entropia / Math.log(24)) * 100, // entropia das 24 horas: 100 = o mesmo tanto em cada hora
    fimdesemana: d.medidas.fim_de_semana * 100,
    sextou: pct(sextou, plays),
    segunda: pct(segunda, plays),
    natal: temNatal ? natal : null,
    virada: temVirada ? virada : null,
    mes: maximo(msMes.values()) / HORA,
    presenca: pct(d.dias_com_musica, d.dias_periodo),
    nuncasome: n > 1 ? maiorPausa / DIA : null,
    sumico: n > 1 ? maiorPausa / DIA : null,
    sessao: maiorSessao / HORA,
    sessoes: sessoes / diasComMusica,
    maratona: [...msDia.values()].filter((ms) => ms >= 3 * HORA).length,
    dedo: vezes100(h.pulos),
    ultimanota: vezes100(h.fim_natural),
    destino: vezes100(h.aleatorio),
    adedo: vezes100(h.aleatorio),
    offline: vezes100(h.offline),
    bolso: comAparelhos ? fatia(CELULAR) : null,
    mesa: comAparelhos ? fatia(COMPUTADOR) : null,
    aparelhos: comAparelhos ? [...tipos.values()].filter((v) => v * 100 >= comAparelho).length : null,
    novidades: meses > 0 ? novos / meses : null, // o 1º mês fica de fora: nele tudo é novo
    antigo,
    fidelidade,
    reencontro: reencontrados.size,
    faro: umAno ? pct(faro, plays) : null,
    raizes: umAno ? pct(raizes, plays) : null,
  };
}

// Temas em relação ao grupo, a partir do resumo de cada um: `contagens` (plays por artista) e `primeiros`
// (início do primeiro play de cada artista, em UTC). Sem `primeiros` de alguém, "Chegou primeiro" sai.
export function numerosDoGrupo(lutadores) {
  const quantos = new Map(); // artista → quantas pessoas ouviram
  for (const { contagens } of lutadores) for (const k of contagens.keys()) somar(quantos, k);
  const chegou = lutadores.every((l) => l.primeiros) ? lutadores.map(() => 0) : null;
  if (chegou) {
    for (const [k, q] of quantos) {
      if (q < 2) continue;
      let melhor = Infinity, quem = -1;
      lutadores.forEach((l, i) => {
        const t = l.primeiros.get(k);
        if (t < melhor) { melhor = t; quem = i; } else if (t === melhor) quem = -1; // mesmo instante: ninguém chegou antes
      });
      if (quem >= 0) chegou[quem]++;
    }
  }
  return lutadores.map(({ contagens }, i) => {
    let total = 0, soeu = 0, todos = 0, comum = 0;
    for (const [k, v] of contagens) {
      const q = quantos.get(k);
      total += v;
      if (q === 1) soeu++;
      if (q === lutadores.length) todos += v;
      if (q > 1) comum += v;
    }
    return { soeu, turma: pct(todos, total), primeiro: chegou ? chegou[i] : null, dj: pct(comum, total) };
  });
}
