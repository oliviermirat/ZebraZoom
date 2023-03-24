import requests
import sys


if __name__ == '__main__':
    if not len(sys.argv) == 2:
        raise ValueError('Expecting one argument: authentication token.')
    base_url = 'https://api.github.com/repos/oliviermirat/ZebraZoom'
    headers = {'Accept': 'application/vnd.github+json',
               'Authorization': 'Bearer %s' % sys.argv[1],
               'X-GitHub-Api-Version': '2022-11-28'}
    release_tag = requests.get('%s/releases/latest' % base_url,
                               headers=headers).json()['tag_name']
    commits = requests.get('%s/compare/%s...HEAD' % (base_url, release_tag),
                           headers=headers).json()['commits']
    notes = (' '.join(comment['body']
                      for comment in requests.get(commit['comments_url'],
                                                  headers=headers).json())
             for commit in commits)
    sys.stdout.write('\n'.join('- %s' % note for note in notes if note))
    sys.stdout.flush()
