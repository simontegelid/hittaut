from setuptools import setup, find_packages, Extension



setup(
    name="hittaut",
    version="0.0.1",
    description="Find the optimal way through hittaut.nu",
    url="",
    author="Simon Tegelid",
    author_email="simon.tegelid@niradynamics.se",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    entry_points={
        "console_scripts": [
            "hittaut=hittaut:main",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    install_requires=open("requirements.txt").readlines(),
)
