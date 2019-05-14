# MARS: MinION Assembly and Reporting System

Snakemake-based pipeline for quality control reporting and assembly (both _de novo_ and reference-based) from a MinION run.

_Warning: very much in active development._

## Setup

### Requirements:

- conda
- python3
- `guppy` from Oxford Nanopore

### Installation

```bash
conda create -n mars python=3
conda activate mars
git clone https://github.com/eclarke/mars
cd mars
pip install .
```

## Usage

#### 01. Create a sample sheet

To begin, MARS needs a sample sheet in tab-delimited format with two columns: `barcode` and `sample_label`.
- `barcode` should contain only numbers between 1-96, and each barcode can only appear once.
- `sample_label` should contain no spaces and a sample label can appear multiple times.

MARS will yell at you if you violate either of these rules.
Other columns are currently ignored and can be used for whatever you want.
Any lines beginning with a '#' are considered comments and will be ignored.

> **Technical replicates:**
> If a sample was split among multiple barcodes, you can choose to give those barcodes the same sample label.
> MARS will pool the reads from all barcodes belonging to the same sample label during assembly steps.

> **Omitting samples:**
> You can omit samples from downstream steps by commenting out its line in the sample sheet (useful if it won't assemble, etc)

I've made a validating sample sheet template available [here](https://docs.google.com/spreadsheets/d/1KsxHezzwVZjvFzjsX4kHZ6y9_uGRNU3SoDTMNqmcNWs/edit?usp=sharing).
Choose File -> Make a copy... to save it to your own Drive for later use.
After filling it out, choose File -> Download as... -> Tab-separated values and transfer it to the server running MARS.


#### 02. Create a config file

Once you've created the sample sheet, use `mars init` to create an empty config file then edit it using your editor of choice:

```bash
mars init -c config.yaml
nano config.yaml
```

The config file contains many `key: value` pairs with a short description above each one.
To get started, fill out at least the `output_dir`, `fast5_dir`, `basecaller`, and `samplesheet_fp` options (making sure to remove the leading `#` on each), then save.

> **Config Validation:**
> Config options that end in `_dir` or `_fp` must be paths to valid directories or files, respectively.
> MARS will resolve any relative paths against the directory it's executed from, and stop if any paths besides `output_dir` do not exist.
> In addition, some config options' values must be numbers (as noted in the config file).
MARS will complain if they're not, saving you the headache of debugging some random Snakemake error down the line.

### 03. Running MARS

Running MARS is straightforward. Just type:

```bash
mars run config.yaml <workflow> [any Snakemake options]
```

where `workflow` is one of:

- `process_all`: basecalls, demultiplexes, and quality-controls reads into separate samples.
- `assemble_all`: assembles each sample using the specified assembler(s).
- `polish_all`: polishes each sample's assembly using the specified polisher(s).

MARS will give you a helpful error message if any of the config values required for the workflow are not specified in the config file. 
For instance, you need to specify which assemblers you want to use in order to run the `assemble_all` workflow.

> **Snakemake options**
> Since MARS calls Snakemake to execute each step, you can pass any Snakemake options to `mars run` and they will be transparently passed to Snakemake during execution.

### 04. Output files

- The final outputs from MARS go into `process`, `assemble`, or `polish` directories inside the directory specified by `output_dir`. 
- Reports (summaries, logs, etc) from each step go into similarly named directories inside the `reports` folder.
- Intermediate files are stored in similarly named directories inside the `workspace` folder (which can be safely deleted when the pipeline is finished.)

#### Process workflow:

- **Final outputs:** basecalled fastq files corresponding to each sample that have been quality-filtered and adapter-trimmed (in `process/`)
- **Reports:** basecalling and demultiplexing summary files, overall run quality reports (in `reports/process/nanoplot`) and per-barcode quality reports (in `reports/process/nanocomp`)

#### Assemble workflow:

- **Final outputs:** assembled contigs from each assembler chosen (in `assemble/[assembler]/[sample]/contigs.fa`) and the assembly graph, if available (in `assemble/[assembler]/contigs.gfa`)
- **Reports:** assembly quality reports from QUAST (in `reports/assemble/[assembler]/[sample]/quast/`)
