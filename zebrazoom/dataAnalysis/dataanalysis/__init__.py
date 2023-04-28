import re


_ALPHABET_REGEX = re.compile(r'[^a-zA-Z]+')
_SORT_PRIORITY = {'wt': 0, 'ctrl': 0, 'ctrls': 0, 'controls': 0, 'control': 0, 'wildtype': 0, 'wildtypes': 0,
                  'het': 1, 'heterozygote': 1, 'heterozygotes': 1,
                  'mut': 2, 'mutant': 2, 'mutants': 2}


def sortGenotypes(genotypes):
  def key(genotype):
    if not isinstance(genotype, str):
      return float('inf'), genotype
    return _SORT_PRIORITY.get(re.sub(_ALPHABET_REGEX, '', genotype).casefold(), float('inf')), genotype
  return sorted(genotypes, key=key)