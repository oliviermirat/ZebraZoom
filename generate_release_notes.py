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
    section_titles = ('New features', 'Enhancements', 'Bug fixes')
    notes = [[] for _ in section_titles]
    for commit in commits:
        for comment in requests.get(commit['comments_url'],
                                    headers=headers).json():
            text = comment['body'].strip()
            if text.startswith('-'):
                section = 0
            else:
                section = int(text[0]) - 1
                text = text[1:].lstrip()
            notes[section].append(text)
    formatted_sections = ('## %s\n%s' % (section_title,
                                         '\n'.join(section_notes))
                          for section_title, section_notes
                          in zip(section_titles, notes) if section_notes)
    sys.stdout.write('# Release notes\n')
    sys.stdout.write('\n'.join(formatted_sections))
    sys.stdout.flush()
