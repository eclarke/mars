# Thrax: MinION run processing and assembly

Snakemake-based pipeline for quality control and assembly (both _de novo_ and reference-based) from a MinION run.

## Installation

```
git clone https://github.com/eclarke/thrax
cd thrax
pip install .
```

## Usage

```
thrax init my_project > config.yaml
nano config.yaml  # fill in relevant values
thrax run --configfile config.yaml
```