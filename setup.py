"""
Setup configuration for Academe - Multi-Agent Academic AI Assistant
"""

from setuptools import setup, find_packages

setup(
    name="academe",
    version="0.5.0",
    description="Multi-Agent Academic AI Assistant with REST API",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    install_requires=[
        # LLM & AI
        "langchain>=0.3.0",
        "langchain-google-genai>=2.0.5",
        "langgraph>=0.2.45",
        "google-generativeai>=0.8.3",
        
        # FastAPI & Web
        "fastapi>=0.115.5",
        "uvicorn[standard]>=0.32.0",
        "python-multipart>=0.0.12",
        "websockets>=14.1",
        
        # Database & Storage
        "pymongo>=4.10.1",
        "motor>=3.6.0",  # Async MongoDB driver
        "pinecone-client>=5.0.1",
        
        # Authentication & Security
        "python-jose[cryptography]>=3.3.0",
        "passlib[bcrypt]>=1.7.4",
        "bcrypt>=4.2.1",
        
        # Embeddings & Vectors
        "sentence-transformers>=3.3.1",
        
        # Document Processing
        "pypdf>=5.1.0",
        "python-docx>=1.1.2",
        
        # Async Task Processing
        "celery>=5.3.4",
        "redis>=5.0.1",
        
        # Data & Validation
        "pydantic>=2.10.4",
        "pydantic-settings>=2.7.0",
        
        # CLI & UI
        "rich>=13.7.0",
        "prompt-toolkit>=3.0.48",
        
        # Utilities
        "python-dotenv>=1.0.1",
    ],
    extras_require={
        "dev": [
            "pytest>=8.3.4",
            "pytest-asyncio>=0.24.0",
            "pytest-cov>=6.0.0",
            "black>=24.10.0",
            "flake8>=7.1.1",
            "mypy>=1.13.0",
        ],
        "eval": [
            "ragas>=0.2.7",
            "datasets>=3.2.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "academe-cli=cli.main:main",
            "academe-api=api.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
