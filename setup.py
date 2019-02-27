from distutils.core import setup

setup(
    name="thrax",
    use_scm_version = True,
    setup_requires=['setuptools_scm'],
    packages=["thrax"],
    include_package_data=True,
    package_data={"thrax": [
        "thrax/data/config.schema.yaml",
        "thrax/data/snakemake/*.rules"]},
    entry_points={'console_scripts': [
        'thrax = thrax.command:main',
    ]}
)
