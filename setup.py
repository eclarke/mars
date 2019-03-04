from setuptools import setup
#from distutils.core import setup

setup(
    name="mars",
    setup_requires=['setuptools_scm'],
    packages=["mars"],
    use_scm_version = True,
    include_package_data=True,
    package_data={"mars": [
        "mars/data/config.schema.yaml",
        "mars/snakemake/*.rules",
        "mars/snakemake/envs/*.yaml"
    ]},
    entry_points={'console_scripts': [
        'mars = mars.command:main',
    ]}
)
