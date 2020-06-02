from setuptools import setup, find_namespace_packages


SHORT_DESCRIPTION = 'Documentation generator for PostgreSQL DB'

try:
    with open('README.md', encoding='utf8') as readme:
        LONG_DESCRIPTION = readme.read()

except FileNotFoundError:
    LONG_DESCRIPTION = SHORT_DESCRIPTION


setup(
    name='foliantcontrib.pgsqldoc',
    description=SHORT_DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    version='1.1.6',
    author='Daniil Minukhin',
    author_email='ddddsa@gmail.com',
    # package_dir={'': 'foliant/preprocessors/'},
    packages=find_namespace_packages(exclude=['*.test', 'foliant', '*.templates']),
    package_data={'foliant.preprocessors.pgsqldoc': ['templates/*.j2']},
    license='MIT',
    platforms='any',
    install_requires=[
        'foliant>=1.0.5',
        'foliantcontrib.utils.combined_options',
        'foliantcontrib.plantuml',
        'psycopg2-binary',
        'jinja2',
        'PyYAML'
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Documentation",
        "Topic :: Utilities",
    ]
)
