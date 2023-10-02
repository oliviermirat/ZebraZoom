from ._openResultsFile import openResultsFile


def getConfigurationFileUsed(videoName: str) -> dict:
  with openResultsFile(videoName, 'r') as results:
    if 'configurationFileUsed' not in results:
      raise ValueError(f'configuration file not found in {results.filename}')
    return dict(results['configurationFileUsed'].attrs)
