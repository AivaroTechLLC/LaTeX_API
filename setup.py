from setuptools import find_packages, setup

setup(
    name="latex-compile-service",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "fastapi>=0.112.0",
        "uvicorn[standard]>=0.23.0",
        "gunicorn>=22.1.0",
        "celery>=5.5.0",
        "redis>=4.8.0",
        "python-multipart>=0.0.6",
        "slowapi>=0.1.4",
        "loguru>=0.7.0",
        "prometheus-client>=0.16.0",
        "pydantic>=2.6.0",
        "pydantic-settings>=2.2.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0",
            "httpx>=0.26.0",
            "pre-commit>=3.4.0",
        ]
    },
    python_requires=">=3.12",
)
