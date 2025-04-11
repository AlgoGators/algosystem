from setuptools import setup, find_packages

setup(
    name="algosystem",
    version="0.1.0",
    author="AlgoGators Team",
    author_email="team@algogators.org",
    description="A batteries-included pythonic library for AlgoGators members",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/algogators/algosystem",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pandas>=1.3.0",
        "numpy>=1.20.0",
        "matplotlib>=3.4.0",
        "seaborn>=0.11.0",
        "sqlalchemy>=1.4.0",
        "click>=8.0.0",
        "scipy>=1.7.0",
        "pytz>=2021.1",
        "requests>=2.25.0",
        "pyyaml>=5.4.0",
        'weasyprint>=53.0',
        'markdown>=3.3.4',
        'pyyaml',
    ],
    entry_points={
        "console_scripts": [
            "algosystem=algosystem.cli.commands:cli",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
)
