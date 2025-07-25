#!/usr/bin/env python3
"""
Setup script for OpenAI Realtime Sales Bot
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="openai-realtime-sales-bot",
    version="1.0.0",
    author="OpenAI Realtime Sales Bot Contributors",
    description="Production-ready conversational AI sales bot for Exotel voice streaming",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/openai-realtime-sales-bot",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Communications :: Telephony",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "sales-bot=openai_realtime_sales_bot:main",
        ],
    },
    keywords="openai, realtime, sales, bot, exotel, voice, streaming, telephony, ai",
    project_urls={
        "Bug Reports": "https://github.com/your-username/openai-realtime-sales-bot/issues",
        "Source": "https://github.com/your-username/openai-realtime-sales-bot",
        "Documentation": "https://github.com/your-username/openai-realtime-sales-bot#readme",
    },
) 