#!/usr/bin/env python3
import argparse
import collections
import json
import os
import re
import subprocess

HERE = os.path.abspath(os.path.dirname(__file__))
VIM_CLONE = os.path.join(HERE, 'vim')
MANIFEST = os.path.join(HERE, 'org.vim.Vim.json')
APPDATA = os.path.join(HERE, 'org.vim.Vim.appdata.xml')


def run(args, **kwargs):
    print('$', ' '.join(args))
    return subprocess.run(args, check=True, **kwargs)


def run_and_read(args):
    result = run(args, stdout=subprocess.PIPE)
    return result.stdout.decode('ascii').strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--remote', default='origin')
    args = parser.parse_args()

    with open(MANIFEST, 'r') as f:
        manifest = json.load(f, object_pairs_hook=collections.OrderedDict)

    vim_source = manifest['modules'][-1]['sources'][0]

    if not os.path.isdir(VIM_CLONE):
        run(('git', 'clone', vim_source['url'], VIM_CLONE))

    os.chdir(VIM_CLONE)
    run(('git', 'pull'))
    sha = run_and_read(('git', 'show-ref', '--hash', 'HEAD'))
    tag = run_and_read(('git', 'describe', '--tags', 'HEAD'))
    date = run_and_read(('git', 'log', '-1', '--date=short',
                         '--pretty=format:%cd'))
    os.chdir(HERE)

    # Patch manifest
    vim_source['tag'] = tag
    vim_source['commit'] = sha
    manifest['modules'][-1]['sources'][0] = vim_source

    with open(MANIFEST, 'w') as f:
        json.dump(fp=f, obj=manifest, indent=2)

    # Patch appdata. Sorry, I can't bring myself to use an XML parser.
    with open(APPDATA, 'r') as f:
        xml = f.read()

    xml = re.sub(r'<release version="(.+?)" date="(.+?)">',
                 '<release version="{}" date="{}">'.format(tag, date),
                 xml)
    with open(APPDATA, 'w') as f:
        f.write(xml)

    branch = 'update-to-{}'.format(tag)
    run(('git', 'checkout', '-b', branch))
    run(('git', 'commit', '-am', 'Update to {}'.format(tag)))
    run(('git', 'push', '-u', args.remote, branch))
    run(('hub', 'pull-request'))


if __name__ == '__main__':
    main()
