"""Setup configuration for osint85."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="osint85",
    version="0.1.0",
    author="osint85 contributors",
    description="Terminal-based OSINT assistant with LLM-powered dork generation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hellasleeper108/osint85",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Information Technology",
        "Topic :: Security",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=[
        "typer[all]>=0.9.0",
        "rich>=13.7.0",
        "anthropic>=0.18.0",
        "openai>=1.12.0",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "sqlalchemy>=2.0.25",
    ],
    entry_points={
        "console_scripts": [
            "osint85=osint85.__main__:app",
        ],
    },
)
