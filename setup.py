from setuptools import setup
import re

requirements = []

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

version = ''
with open('sxync/__init__.py') as f:
    version = re.search(
        r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE).group(1)

readme = ""

with open("README.md") as f:
    readme = f.read()

setup(name="sxync",
      author="Yadiel A. Rodriguez",
      url="https://github.com/neokuze/sxync",
      version=version,
      packages=["sxync"],
      license="GPL-3.0",
      description="A Python library for connecting to Pymes/ Roxvent Chat",
      long_description=readme,
      long_description_content_type="text/markdown",
      install_requires=requirements,
      python_requires=">=3.9"
      )
