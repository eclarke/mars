# MARS: MinION Assembly and Reporting System

Snakemake-based pipeline for quality control reporting and assembly (both _de novo_ and reference-based) from a MinION run.

## Installation

```bash
git clone https://github.com/eclarke/mars
cd mars
pip install .
```

## Usage

### Init

MARS needs a sample sheet in tab-delimited format with at least a column titled `barcode`. Other columns
are currently ignored. Barcodes should be numbers between 1-12.

Additional run info can be encoded in the header in lines starting with '#'- these will be automatically parsed as key:value pairs and added to the configuration file. Here's an example:

```
# flowcell	FLO-MIN106
# kit		SQK-RBK004
# run_number	0
barcode sample_id
1       s1
2	s2
3	s3
```

Call `mars init` to generate a config file with your sample sheet and your desired output folder for the pipeline. Some values will be filled with placeholder values and may need to be updated (e.g. Canu memory requirements, location of fast5 files, etc). The config file contains explanatory comments for each option.

```bash
mars init --output_dir mars_output --samplesheet_fp samples.tsv > config.yaml
```

### Running

To run, just type

```bash
mars run config.yaml
```

Since MARS wraps a set of Snakemake workflows, you can pass any Snakemake options as you would normally, e.g:

```bash
mars run config.yaml --cores 12 --dry-run
```

