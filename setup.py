#!/usr/bin/env python3
"""
OLS 침투 판정 엔진 설치 스크립트
"""

from setuptools import setup, find_packages
import os

# 현재 디렉토리에서 requirements.txt 읽기
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        # 주석과 빈 줄 제거
        return [line.strip() for line in lines 
                if line.strip() and not line.strip().startswith('#')]
    return []

setup(
    name="ols-penetration-engine",
    version="1.0.0",
    description="ICAO/국내 기준 장애물제한표면(OLS) 침투 판정 엔진",
    long_description=open('README.md', encoding='utf-8').read() if os.path.exists('README.md') else "",
    long_description_content_type="text/markdown",
    author="OLS Team",
    author_email="ols-team@example.com",
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        'dev': [
            'pytest>=7.4.0',
            'pytest-cov>=4.1.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
            'mypy>=1.5.0'
        ]
    },
    entry_points={
        'console_scripts': [
            'ols-engine=ols_engine.main:main',
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: GIS",
    ],
)