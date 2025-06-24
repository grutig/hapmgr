#!/usr/bin/env python3
import subprocess
import re
from collections import deque
import gettext
import os

# Gettext configuration
_ = gettext.gettext

# Set LC_ALL=C for English descriptions
os.environ['LC_ALL'] = 'C'


def get_pack_tree(package):
    """Returns the list of dependencies for a package"""
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
        return dependencies

    except subprocess.CalledProcessError as e:
        return []
    except Exception as e:
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
            elif line.startswith('Description-en'):
                description = line.split('Description-en: ')[1].strip()
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
    # Start from hamradio-all
    packages = []
    done_metas = []
    metaqueue = deque(['hamradio-all'])

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
    # update messages.pot
    potfile = "locale/messages.pot"
    potentries = set()
    try:
        with open(potfile, "r") as f:
            content = f.read()
            potentries = set(re.findall(r'msgid "(.*?)"', content))
    except FileNotFoundError:
        content = '''msgid ""
    msgstr ""
    "Project-Id-Version: 1.0\\n"
    "MIME-Version: 1.0\\n"
    "Content-Type: text/plain; charset=UTF-8\\n"
    "Content-Transfer-Encoding: 8bit\\n"

    '''
    pfh = open(potfile, "w")
    pfh.write(content)

    with open("packages.py", "w") as f:
        f.write("class Packs:\n")
        f.write("   packages = []\n")
        f.write("   def __init__(self, _):\n")
        for package in packages:
            if "'" in package['desc']:
                package['desc'] = package['desc'].replace("'", '\u0060')
            f.write("      self.packages.append("+str(package).replace("'desc':", "'desc': _(").replace("'}", "')}") + ")\n")
            if package['desc'] not in potentries:
                msgid = package['desc']
                pfh.write(f'\nmsgid "{msgid}"\nmsgstr ""\n')

    pfh.close()
    # translate message strings


if __name__ == '__main__':
    main()