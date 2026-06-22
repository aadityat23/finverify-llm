from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="finverify",
    version="0.1.0",
    author="Aaditya Thokal",
    author_email="aaditya.thokal24@gmail.com",
    description="Deterministic verification for financial LLM outputs. 42× accuracy improvement on FinQA.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aadityat23/finverify-llm",
    project_urls={
        "Live Demo": "https://finverify-llm.vercel.app",
        "HuggingFace Model": "https://huggingface.co/aadi2026/finverify-lora",
        "Bug Tracker": "https://github.com/aadityat23/finverify-llm/issues",
    },
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[],  # Zero dependencies for local DVL
    extras_require={
        "api": ["httpx>=0.24"],  # For async client
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Typing :: Typed",
    ],
    keywords="llm verification financial nlp hallucination dvl finqa",
)
