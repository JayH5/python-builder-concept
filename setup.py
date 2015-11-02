from setuptools import setup, find_packages

setup(name='python-builder-concept',
      version='0.1a0',
      description='Automated building of Python wheels using Docker to create '
                  'build environments',
      classifiers=[
          "Programming Language :: Python",
      ],
      author='Jamie Hewland',
      author_email='jamie@praekeltfoundation.org',
      url='http://github.com/JayH5/python-builder-concept',
      license='BSD',
      keywords='pip,docker,virtualenv',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'click',
          'docker-py',
          'py',
          'pystache',
          'PyYAML',
      ],
      tests_require=[
          'pytest'
      ],
      entry_points={
          'console_scripts': ['builder = python_builder_concept.cli:main'],
      })
