from setuptools import setup
import os
from setuptools.command.install import install
from setuptools.config.expand import find_packages

def find_locale_files():
    locale_files = []
    for root, dirs, files in os.walk('locale'):
        for file in files:
            if file.endswith('.mo'):
                dest_dir = os.path.join('share', root)
                source_file = os.path.join(root, file)
                locale_files.append((dest_dir, [source_file]))
    return locale_files

class CustomInstallCommand(install):
    def run(self):
        install.run(self)
        admin_script = os.path.join(self.install_base, 'local', 'bin', 'hapmgr-admin')
        if os.path.exists(admin_script):
            os.chmod(admin_script, 0o755)


data_files = [
    ('share/icons/hicolor/scalable/apps', ['data/icons/hapmgr.svg']),
    ('share/applications', ['data/applications/hapmgr.desktop']),
    ('bin', ['data/applications/hapmgr-admin']),
    ('share/polkit-1/actions', ['data/applications/com.hapmgr.policy']),

]

setup(
    name="hapmgr",
    version="1.0",
    packages=find_packages(),
    package_data={
        'hapmgr': ['*.py', 'icon.svg', 'locale/*/LC_MESSAGES/*.mo'],
    },
    author="Giorgio L. Rutigliano",
    author_email="giorgio@i8zse.eu",
    description="Linux hamradio applications manager",
    data_files=data_files,
    entry_points={
        'gui_scripts': [
            'hapmgr=hapmgr.main:main',
        ],
    },
    install_requires=[
        'PyQt5', "babel",
    ],
)
