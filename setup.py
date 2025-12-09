from setuptools import setup, find_packages

setup(
    name="mirrordna-symbiosis",
    version="0.1.0",
    description="The Symbiotic Intelligence Spine for Local AI",
    long_description=open("RELEASE_THE_LINK.md").read(),
    long_description_content_type="text/markdown",
    author="MirrorBrain (Antigravity)",
    author_email="system@mirrordna.ai",
    url="https://github.com/MirrorDNA-Reflection-Protocol/MirrorDNA-Symbiosis",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "requests",
        "chromadb",
        "sentence-transformers"
    ],
    entry_points={
        "console_scripts": [
            "omega-link=sovereign_link:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.9",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
