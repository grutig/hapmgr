from setuptools import setup
import os
from setuptools.command.install import install
from setuptools.config.expand import find_packages


class CustomInstallCommand(install):
    def run(self):
        install.run(self)
        admin_script = os.path.join(self.install_base, 'local', 'bin', 'hapmgr-admin')
        if os.path.exists(admin_script):
            os.chmod(admin_script, 0o755)

# Lista dei file di dati (icone, .desktop)
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
        'hapmgr': ['*.py', 'icon.svg'],
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
