from setuptools import setup, find_packages

version = '0.0'

setup(name='torspider',
      version=version,
      description="Example/prototype of an asynchroneous web-crawler based on Tornado",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='web-crawler web-spider scraper',
      author='Sergey Krushinsky',
      author_email='krushinsky@gmail.com',
      url='http://crawlers.info',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=[
          'tornado',
          'pycurl',
          'bs4',
          'lxml',
          'motor',
          'langdetect',
          'python-dateutil',
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
