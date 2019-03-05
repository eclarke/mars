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
mars init --output_dir mars_output --samplesheet_fp samples.tsv > config.yaml
mars run config.yaml
```
