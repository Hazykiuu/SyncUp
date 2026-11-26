// Os 56 temas da Batalha v2 (PLANO-BATALHA-V2), na ordem do plano. Cada um: chave, título, unidade, casas,
// modelo de desenho, frase do story e, quando não é o padrão, `menor` (menor vence), `minimo` (valor que não
// conta como ponto), `vazio` (por que sai quando ninguém pontua), `ausente` (por que sai quando falta o dado),
// `campos` (colunas que nem todo histórico traz), `pct` (porcentagem: pede 100 plays e escala 100),
// `escala` (fração do desenho; null = o maior da rodada) e `aprox` (leva a nota "≈" do Last.fm: usa a duração dos plays).
export const FAMILIAS = ['volume', 'variedade', 'repeticao', 'relogio', 'calendario', 'constancia', 'pulos', 'aparelhos', 'descoberta', 'grupo'];
export const MODELOS = ['corrida', 'porcentagem', 'relogio', 'calendario', 'sequencia', 'contagem'];
export const OPOSTOS = [['nuncasome', 'sumico'], ['paciencia', 'dedo'], ['destino', 'adedo']];
// Título do campeão que fez 2 ouros numa família (batalha.js). Cada um vale para qualquer tema da família,
// inclusive os opostos (Grande sumiço e Sem parar; Paciência e Dedo nervoso; Só eu conheço e Gosto de turma).
export const TITULOS = {
  volume: 'Trator de Plays', variedade: 'Enciclopédia Musical', repeticao: 'Modo Obsessão', relogio: 'Fuso Próprio',
  calendario: 'Agenda Cheia', constancia: 'Ritmo Próprio', pulos: 'Comandante do Play', aparelhos: 'Sempre Plugado(a)',
  descoberta: 'Curador(a) Oficial', grupo: 'Peça-chave',
};

const P = { pct: true, escala: 100 };
const A = { aprox: true };
const CAMPO = { pulos: 'as músicas puladas', motivo: 'como cada música terminou', aleatorio: 'o modo aleatório', offline: 'o modo offline', plataforma: 'o aparelho' };
const UM_ANO = 'o período de alguém tem menos de um ano';

const LISTA = {
  volume: [
    ['horas', 'Maratonista', 'h', 0, 'corrida', 'Horas de música no período.', A],
    ['plays', 'Play infinito', 'plays', 0, 'contagem', 'Plays de pelo menos 30 segundos.', { vazio: 'ninguém deu play' }],
    ['dia', 'Dia mais insano', 'h num dia', 1, 'relogio', 'O dia em que mais ouviu, nas 24 horas.', { escala: 24, ...A }],
    ['metralhadora', 'Metralhadora', 'plays num dia', 0, 'contagem', 'O dia com mais plays de cada um.', { vazio: 'ninguém deu play' }],
    ['cruzeiro', 'Ritmo de cruzeiro', 'min por dia com música', 0, 'corrida', 'Minutos de música, em média, nos dias em que ouviu.', A],
  ],
  variedade: [
    ['artistas', 'Explorador(a)', 'artistas', 0, 'contagem', 'Artistas diferentes que cada um ouviu.'],
    ['musicas', 'Colecionador(a)', 'músicas', 0, 'contagem', 'Músicas diferentes na estante de cada um.'],
    ['buffet', 'Buffet livre', 'artistas num dia', 0, 'contagem', 'O dia com mais artistas diferentes.'],
    ['umavez', 'Uma vez e nunca mais', '% de músicas ouvidas uma vez', 1, 'porcentagem', 'Músicas que tocaram uma vez e não voltaram.', { ...P, vazio: 'ninguém ouviu uma música uma vez só' }],
    ['visita', 'Visita rápida', '% de artistas ouvidos uma vez', 1, 'porcentagem', 'Artistas com um play só no período.', { ...P, vazio: 'ninguém ouviu um artista uma vez só' }],
    ['elenco', 'Elenco rotativo', 'artistas a cada 100 plays', 1, 'contagem', 'Quantos artistas diferentes aparecem a cada 100 plays.', P],
  ],
  repeticao: [
    ['repeteco', 'Repeteco', 'vezes a mesma música num dia', 0, 'contagem', 'A mesma música, repetida num dia só.', { minimo: 1, vazio: 'ninguém repetiu uma música no mesmo dia' }],
    ['fa', 'Fã nº 1', '% no artista favorito', 1, 'porcentagem', 'Fatia dos plays no artista favorito.', P],
    ['disco', 'Disco furado', 'vezes seguidas a mesma música', 0, 'sequencia', 'A mesma música, um play atrás do outro.', { minimo: 1, vazio: 'ninguém tocou uma música duas vezes seguidas' }],
    ['hino', 'Hino pessoal', 'plays na música nº 1', 0, 'contagem', 'Plays da música mais tocada de cada um.'],
    ['panelinha', 'Panelinha', '% nos 10 artistas favoritos', 1, 'porcentagem', 'Fatia dos plays nos 10 artistas mais ouvidos.', P],
    ['playlist', 'Playlist de bolso', '% nas 10 músicas favoritas', 1, 'porcentagem', 'Fatia dos plays nas 10 músicas mais tocadas.', P],
    ['obra', 'Obra completa', 'músicas de um só artista', 0, 'contagem', 'Mais músicas diferentes de um mesmo artista.'],
  ],
  relogio: [
    ['coruja', 'Coruja', '% na madrugada', 1, 'relogio', 'Fatia dos plays entre meia-noite e 6 h.', { ...P, vazio: 'ninguém ouviu de madrugada' }],
    ['madrugador', 'Madrugador(a)', '% de manhã', 1, 'relogio', 'Fatia dos plays entre 6 h e meio-dia.', { ...P, vazio: 'ninguém ouviu de manhã' }],
    ['almoco', 'Hora do almoço', '% no almoço', 1, 'relogio', 'Fatia dos plays entre meio-dia e 14 h.', { ...P, vazio: 'ninguém ouviu na hora do almoço' }],
    ['tarde', 'Fim de tarde', '% no fim da tarde', 1, 'relogio', 'Fatia dos plays entre 17 h e 19 h.', { ...P, vazio: 'ninguém ouviu no fim da tarde' }],
    ['noite', 'Trilha da noite', '% à noite', 1, 'relogio', 'Fatia dos plays entre 18 h e meia-noite.', { ...P, vazio: 'ninguém ouviu à noite' }],
    ['espalhado', 'Relógio imprevisível', 'de 100 no espalhamento', 1, 'relogio', 'Quanto os plays se espalham pelas 24 horas: 100 é igual em todas.', P],
  ],
  calendario: [
    ['fimdesemana', 'Fim de semana', '% no sábado e no domingo', 1, 'calendario', 'Fatia dos plays no sábado e no domingo.', { ...P, vazio: 'ninguém ouviu no fim de semana' }],
    ['sextou', 'Sextou', '% na sexta à noite', 1, 'calendario', 'Fatia dos plays na sexta, das 18 h à meia-noite.', { ...P, vazio: 'ninguém ouviu na sexta à noite' }],
    ['segunda', 'Segunda sem preguiça', '% na segunda', 1, 'calendario', 'Fatia dos plays na segunda-feira.', { ...P, vazio: 'ninguém ouviu na segunda' }],
    ['natal', 'Natal com trilha', 'plays no Natal', 0, 'calendario', 'Plays de 24 a 26 de dezembro.', { vazio: 'ninguém ouviu no Natal', ausente: 'o período de alguém não passa pelo Natal' }],
    ['virada', 'Virada', 'plays na virada', 0, 'calendario', 'Plays em 31 de dezembro e 1º de janeiro.', { vazio: 'ninguém ouviu na virada', ausente: 'o período de alguém não passa pela virada do ano' }],
    ['mes', 'Mês lendário', 'h num mês', 1, 'calendario', 'O mês em que mais ouviu.', A],
  ],
  constancia: [
    ['sequencia', 'Sem parar', 'dias seguidos', 0, 'sequencia', 'Dias seguidos ouvindo, sem falhar um.'],
    ['presenca', 'Presença confirmada', '% dos dias com música', 1, 'porcentagem', 'Dias com música entre o primeiro e o último play.', P],
    ['nuncasome', 'Nunca some', 'dias na maior pausa', 1, 'corrida', 'A maior pausa sem ouvir nada. Aqui, menos é melhor.', { menor: true, ausente: 'alguém tem um play só', ...A }],
    ['sumico', 'Grande sumiço', 'dias na maior pausa', 1, 'corrida', 'A maior pausa sem ouvir nada.', { vazio: 'ninguém ficou sem ouvir', ausente: 'alguém tem um play só', ...A }],
    ['sessao', 'Sessão sem fim', 'h numa sessão', 1, 'corrida', 'A maior sessão: plays com menos de 30 min entre um e outro.', A],
    ['sessoes', 'Abre e fecha', 'sessões por dia com música', 1, 'contagem', 'Quantas vezes por dia a música volta depois de 30 min parada.', A],
    ['maratona', 'Dias de maratona', 'dias com 3 h ou mais', 0, 'calendario', 'Dias com pelo menos 3 horas de música.', { vazio: 'ninguém ouviu 3 h num dia', ...A }],
  ],
  pulos: [
    ['paciencia', 'Paciência', '% de músicas puladas', 1, 'porcentagem', 'Fatia de músicas puladas. Aqui, menos é melhor.', { ...P, menor: true, campos: ['pulos'] }],
    ['dedo', 'Dedo nervoso', '% de músicas puladas', 1, 'porcentagem', 'Fatia de músicas puladas antes do fim.', { ...P, vazio: 'ninguém pulou', campos: ['pulos'] }],
    ['ultimanota', 'Até a última nota', '% até o fim', 1, 'porcentagem', 'Fatia das faixas que tocaram até o fim.', { ...P, vazio: 'nenhuma música tocou até o fim', campos: ['motivo'] }],
    ['destino', 'Deixa o destino', '% no aleatório', 1, 'porcentagem', 'Fatia das reproduções no modo aleatório.', { ...P, vazio: 'ninguém usou o aleatório', campos: ['aleatorio'] }],
    ['adedo', 'Escolho a dedo', '% no aleatório', 1, 'porcentagem', 'Fatia das reproduções no aleatório. Aqui, menos é melhor.', { ...P, menor: true, campos: ['aleatorio'] }],
    ['offline', 'Sem sinal', '% offline', 1, 'porcentagem', 'Fatia das reproduções sem internet.', { ...P, vazio: 'ninguém ouviu offline', campos: ['offline'] }],
  ],
  aparelhos: [
    ['bolso', 'No bolso', '% no celular', 1, 'porcentagem', 'Fatia das reproduções no Android ou no iPhone.', { ...P, vazio: 'ninguém ouviu no celular', campos: ['plataforma'] }],
    ['mesa', 'Na mesa', '% no computador', 1, 'porcentagem', 'Fatia das reproduções no computador ou no navegador.', { ...P, vazio: 'ninguém ouviu no computador', campos: ['plataforma'] }],
    ['aparelhos', 'Onipresente', 'tipos de aparelho', 0, 'contagem', 'Tipos de aparelho usados, como celular, computador e TV.', { campos: ['plataforma'] }],
  ],
  descoberta: [
    ['novidades', 'Caçador de novidades', 'artistas novos por mês', 1, 'contagem', 'Artistas ouvidos pela primeira vez, por mês, depois do primeiro mês.', { vazio: 'ninguém descobriu artistas', ausente: 'o período de alguém tem menos de 2 meses' }],
    ['antigo', 'Amor antigo', 'dias com o mesmo artista', 0, 'corrida', 'Do primeiro ao último play do mesmo artista.', { vazio: 'ninguém voltou a um artista em outro dia' }],
    ['fidelidade', 'Fidelidade', 'meses com o mesmo artista', 0, 'calendario', 'O artista presente em mais meses do período.'],
    ['reencontro', 'Reencontro', 'artistas reencontrados', 0, 'contagem', 'Artistas que voltaram depois de 6 meses sem tocar.', { vazio: 'ninguém voltou a um artista depois de 6 meses' }],
    ['faro', 'Faro fresco', '% em artistas novos', 1, 'porcentagem', 'Fatia dos plays em artistas descobertos nos últimos 6 meses.', { ...P, vazio: 'ninguém ouviu artistas novos', ausente: UM_ANO }],
    ['raizes', 'Raízes', '% em artistas dos primeiros 6 meses', 1, 'porcentagem', 'Fatia dos plays em artistas descobertos nos primeiros 6 meses.', { ...P, ausente: UM_ANO }],
  ],
  grupo: [
    ['soeu', 'Só eu conheço', 'artistas só seus', 0, 'contagem', 'Artistas que mais ninguém do grupo ouviu.', { vazio: 'ninguém tem artista só seu' }],
    ['turma', 'Gosto de turma', '% em artistas de todos', 1, 'porcentagem', 'Fatia dos plays em artistas que o grupo todo ouve.', { ...P, vazio: 'nenhum artista é ouvido por todos' }],
    ['primeiro', 'Chegou primeiro', 'artistas ouvidos antes', 0, 'contagem', 'Artistas em comum que cada um ouviu antes dos outros.', { vazio: 'ninguém chegou antes', ausente: 'falta a data do primeiro play de alguém' }],
    ['dj', 'DJ do grupo', '% em artistas em comum', 1, 'porcentagem', 'Fatia dos plays em artistas que mais alguém do grupo ouve.', { ...P, vazio: 'ninguém tem artista em comum' }],
  ],
};

export const TEMAS = FAMILIAS.flatMap((familia) => LISTA[familia].map(([chave, titulo, unidade, casas, modelo, frase, extra]) => ({
  chave, titulo, unidade, casas, modelo, frase, familia, vazio: 'ninguém ouviu', campos: [], pct: false, escala: null, aprox: false, ...extra,
})));
export const TEMA = Object.fromEntries(TEMAS.map((t) => [t.chave, t]));

// Por que o tema sai quando falta o número de alguém.
export const ausente = (t) => t.ausente ?? (t.campos.length ? `nem todo histórico informa ${CAMPO[t.campos[0]]}` : 'falta um número de alguém');
