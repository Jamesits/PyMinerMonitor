import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="miner_monitor",
    version="0.0.1",
    author="James Swineson",
    author_email="pypi@public.swineson.me",
    description="Collects cryptocurrency miner statuses and push to InfluxDB",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Jamesits/PyMinerMonitor",
    packages=setuptools.find_packages(),
    classifiers=(
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ),

    entry_points={
        'console_scripts': [
            'miner_monitor = miner_monitor.collector:main_func',
        ],
        'setuptools.installation': [
            'eggsecutable = miner_monitor.collector:main_func',
        ]
    },
    install_requires=[
        'requests'
    ]
)