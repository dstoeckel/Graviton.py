from setuptools import setup, find_packages

setup(
    name = 'graviton',
    version = '0.2',
    packages = ['graviton'],
    author = 'Daniel Stöckel',
    author_email = 'dstoeckel@bioinf.uni-sb.de',
    description = 'Bindings to the RESTful API of Graviton-based web services such as GeneTrail2.',
    license = 'GPLv3',
    url = 'https://github.com/dstoeckel/graviton.py',
    install_requires = [
        'six'
    ]
)
