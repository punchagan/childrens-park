from setuptools import setup, find_packages


def find_version():
    return '1.5a1'


# Get the long description from the relevant file
with open('README.rst') as f:
    long_description = f.read()

setup(
    name='park',
    version=find_version(),
    description='A simple python xmpp chatroom',
    long_description=long_description,

    # The project URL.
    url='http://github.com/punchagan/childrens-park',

    # Author details
    author='Puneeth Chaganti',
    author_email='punchagan[at]muse-amuse[dot]in',

    # Choose your license
    license='GPLv3',

    # What does your project relate to?
    keywords='jabber xmpp chat bot chatroom',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages.
    packages=find_packages(exclude=['docs', 'tests*']),

    # Non python files to be bundled in the egg.
    package_data={'park.plugins': ['data/*.*']},

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed.
    install_requires=[
        'jabberbot',
        'xmpppy==0.5.0rc1',
        'beautifulsoup',
    ],

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and
    # allow pip to create the appropriate form of executable for the target
    # platform.
    entry_points={
        'console_scripts': [
            'park=park.chatroom:main',
        ],
    }
)
