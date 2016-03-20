import os

from setuptools import setup, find_packages, Command


class CleanCommand(Command):
    """Custom clean command to tidy up the project root."""
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        os.system('rm -vrf ./build ./dist ./*.pyc ./*.tgz ./*.egg-info')


here = os.path.abspath(os.path.dirname(__file__))

try:
    with open(os.path.join(here, 'README.md')) as f:
        README = f.read()
except IOError:
    VERSION = README = ''

install_requires = [
    'yosai',
    'redis',
]

setup(
    name='yosai_dpcache',
    use_scm_version={
        'version_scheme': 'post-release',
        'local_scheme': 'dirty-tag'
    },
    description="A caching integration for Yosai",
    long_description=README,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Security',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords='caching yosai',
    author='Darin Gordon',
    author_email='dkcdkg@gmail.com',
    url='http://www.github.com/yosaiproject/yosai_dpcache',
    license='Apache License 2.0',
    packages=find_packages('.', exclude=['ez_setup', 'test*']),
    setup_requires=[
        'setuptools_scm >= 1.7.0'
    ],
    install_requires=install_requires,
    zip_safe=False,
    cmdclass={'clean': CleanCommand}
)
