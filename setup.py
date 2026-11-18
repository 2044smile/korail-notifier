# -*- coding: utf-8 -*-
"""
Korail2 -- Korail (www.letskorail.com) wrapper for Python.
==========================================================

If you're reading this code, you should know what Korail is.

Just play. Have fun. Enjoy the Korail2!
```````````````````````````````````````

::

    >>> from korail2 import Korail

Links
`````

* `GitHub repository <http://github.com/carpedm20/korail2>`_
* `development version
  <http://github.com/carpedm20/korail2/zipball/master>`_


"""
from setuptools import setup

# detect the current version
version = '0.5.0'

with open('README.rst', encoding='utf8') as f:
    long_desc = f.read()

setup(
    name='korail2',
    packages=['korail2', 'notifier'],
    version=version,
    python_requires='>=3.10',
    description='Korail(www.letskorail.com) wrapper for Python',
    long_description=long_desc,
    license='BSD License',
    author='Taehoon Kim',
    author_email='carpedm20@gmail.com',
    url='http://github.com/carpedm20/korail2',
    keywords=['Korail'],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    install_requires=[
        'requests>=2.31',
        'PyCryptodome>=3.19',
        'python-dotenv>=1.0',
    ],
)
