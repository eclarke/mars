# MARS: MinION Assembly and Reporting System

Snakemake-based pipeline for quality control reporting and assembly (both _de novo_ and reference-based) from a MinION run.

## Installation

```bash
git clone https://github.com/eclarke/mars
cd mars
pip install .
```

## Usage

```bash
mars init my_project > config.yaml
nano config.yaml  # fill in relevant values
mars run --configfile config.yaml
```
