// Perfis feitos à mão para os cenários do dueto (testes e capturas). Determinísticos: nada de aleatório.
// Grupo 1 (5 pessoas): Ana e Bruno com sobreposição alta (Bruno ⊂ Ana: Lado B de Ana vazio, o de Bruno cheio)
// e um trio (Caio, Duda e um nome longo) que só se cruza entre si.
// Grupo 2 (4 pessoas): Eva e Fábio com sobreposição baixa; dois nomes longos sem nenhum artista em comum.
const perfil = (nome, artistas) => ({
  nome, fonte: 'convite',
  top_artistas: { short_term: artistas, medium_term: artistas, long_term: artistas },
  top_musicas: { short_term: [], medium_term: [], long_term: [] },
});
const serie = (prefixo, n) => Array.from({ length: n }, (_, i) => `${prefixo} ${i + 1}`);

const COMUNS_AB = ['Djavan', 'Gal Costa', 'Caetano Veloso', 'Marisa Monte', 'Tim Maia', 'Jorge Ben Jor'];
const TRIO = ['Arctic Monkeys', 'The Strokes', 'Tame Impala'];

export const GRUPO_1 = [
  perfil('Ana', [...COMUNS_AB, ...serie('Ana Extra', 10)]),
  perfil('Bruno', COMUNS_AB.slice()),
  perfil('Caio', [...TRIO, 'Phoenix', ...serie('Caio Solo', 6)]),
  perfil('Duda', [...TRIO, 'Phoenix', ...serie('Duda Solo', 6)]),
  perfil('Maria Eduarda Albuquerque Vasconcelos', [...TRIO, ...serie('Maria Solo', 7)]),
];

export const GRUPO_2 = [
  perfil('Eva', ['Björk', ...serie('Eva Solo', 12)]),
  perfil('Fábio', [...serie('Fábio Solo', 12), 'Björk']),
  perfil('João Pedro Cavalcanti de Albuquerque', serie('Joao Solo', 10)),
  perfil('Luiza Fernandes Montenegro', serie('Luiza Solo', 10)),
];
