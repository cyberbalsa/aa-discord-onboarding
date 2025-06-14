from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="aa-discord-onboarding",
    version="1.0.0",
    author="Eve Balsa",
    author_email="eve@balsa.info",
    description="Discord onboarding plugin for Alliance Auth with EVE Online integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jetbalsa/aa-discord-onboarding",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
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
        "Framework :: Django",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Communications :: Chat",
    ],
    python_requires=">=3.8",
    install_requires=[
        "allianceauth>=3.0.0",
        "django>=4.0",
        "celery>=5.0",
        "discord.py>=2.0",
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-django", 
            "black",
            "flake8",
        ],
    },
)