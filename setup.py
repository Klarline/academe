"""Setup file for Academe package"""

from setuptools import setup, find_packages

setup(
    name="academe",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "langgraph>=0.2.45",
        "langchain>=0.3.7",
        "langchain-google-genai>=2.0.5",
        "langchain-anthropic>=0.2.4",
        "langchain-openai>=0.2.9",
        "python-dotenv>=1.0.0",
        "pydantic>=2.10.4",
        "pydantic-settings>=2.7.0",
    ],
    python_requires=">=3.11",
)