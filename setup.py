from distutils.core import setup

setup(
    name="mars",
    setup_requires=['setuptools_scm'],
    packages=["mars"],
    use_scm_version = {"root": ".", "relative_to": __file__},
    include_package_data=True,
    package_data={"mars": [
        "mars/data/config.schema.yaml",
        "mars/data/snakemake/*.rules"]},
    entry_points={'console_scripts': [
        'mars = mars.command:main',
    ]}
)
