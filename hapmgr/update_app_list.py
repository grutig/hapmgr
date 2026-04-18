#!/usr/bin/env python3
import subprocess
import re
from collections import deque
import gettext
import os
import json
from pathlib import Path

# Gettext configuration
_ = gettext.gettext

def get_pack_tree(package):
    """Returns the list of dependencies for a package"""
    os.environ['LC_ALL'] = 'C'
    try:
        output = subprocess.check_output(
            ['apt-cache', 'depends', package],
            universal_newlines=True
        )
        dependencies = []
        for line in output.split('\n'):
            if line.startswith('  Depends: '):
                dep = line.split('Depends: ')[1].strip()
                dependencies.append(dep.split(':')[0])  # Removes any :arch suffix
            if line.startswith('  Recommends: '):
                dep = line.split('Recommends: ')[1].strip()
                dependencies.append(dep.split(':')[0])  # Removes any :arch suffix
        del os.environ['LC_ALL']
        return dependencies

    except subprocess.CalledProcessError as e:
        del os.environ['LC_ALL']
        return []
    except Exception as e:
        del os.environ['LC_ALL']
        return []


def get_pack_info(package):
    """Returns the name and description of a package"""

    try:
        output = subprocess.check_output(
            ['apt-cache', 'show', package],
            universal_newlines=True
        )
        name = None
        description = None
        section = None
        for line in output.split('\n'):
            if line.startswith('Package: '):
                name = line.split('Package: ')[1].strip()
            elif line.startswith(f'Description-{langcode}'):
                description = line.split(f'Description-{langcode}: ')[1].strip()
                # Take only the first line of the description
                description = description.split('\n')[0]
                # Remove any (metapackage) annotations
                description = re.sub(r'\s*\(.*\)\s*', '', description)
            elif line.startswith('Section: '):
                section = line.split('Section: ')[1].strip()
            if line and description and section:
                break
        return name, description, section == "metapackages"
    except subprocess.CalledProcessError as e:
        return None, None, None


def process_meta(metapackage):
    """
    Processes a metapackage and returns its components
    """
    packages = []
    metas = []
    components = get_pack_tree(metapackage)

    for package in components:
        if package[0] == "<" and package[-1] == ">":
            # skip virtual packages
            continue
        name, description, meta = get_pack_info(package)
        if meta and name:
          metas.append(name)
        elif name and description:
            # Extracts the short metapackage name (e.g., "antenna" from "hamradio-antenna")
            metapackage_short = metapackage.split('hamradio-')[-1]
            packages.append({
                'app': name,
                'pack': _(metapackage_short),
                'desc': _(description)
            })

    return packages, metas


def main():
    global langcode

    home = Path(os.environ["HOME"])
    jpacks = home / ".config" / "hapmgr" / "packages.json"
    jpacks.parent.mkdir(exist_ok=True, parents=True)

    # Start from hamradio-all
    packages = []
    done_metas = []
    metaqueue = deque(['hamradio-all'])

    langcode = os.environ.get('LANG', '').split("_")[0].lower()

    while metaqueue:
        cur_meta = metaqueue.popleft()
        done_metas.append(cur_meta)
        # process metapackage and queque new
        packs, metas = process_meta(cur_meta)
        for meta in metas:
            if meta in done_metas or meta in metaqueue:
                continue
            metaqueue.append(meta)
        for pack in packs:
            if not any(p['app'] == pack['app'] for p in packages):
                packages.append(pack)
    # Sort by application name (case-insensitive)
    packages.sort(key=lambda x: x['app'].lower())

    with open (jpacks, 'w') as f:
        json.dump(packages, f)





if __name__ == '__main__':
    main()
