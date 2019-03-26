#
# MARS Assembly Polishing Workflow
# ----------------------------------------------------------------------
#
# Polishes an assembly and re-assesses the polished assembly quality.

pol_output_dir = output_dir + 'polish/'
pol_working_dir = working_dir + 'polish/'
pol_report_dir = report_dir + 'polish/'

rule align_reads:
    input:
        contigs = rules.assemble.input,
        reads = rules.process.input.filtered
    output:
        pol_working_dir + '{sample}/{assembler}/sorted.bam'        
    params:
        tmp = pol_working_dir + '{sample}/{assembler}/reads.tmp'
    threads:
        config.get('minimap2_threads', 8)
    conda:
        resource_filename("mars", "snakemake/envs/assembling.yaml")
    shell:
        """
        minimap2 -ax map-ont -t {threads} {input.contigs} {input.reads} |\
        samtools sort -o {output} -T {params.tmp} -
        samtools index {output}
        """

rule index_nanopolish:
    '''
    Builds the Nanopolish index from the fastq and fast5 files.
    '''
    input:
        fastq = rules.process.input.filtered,
        summary = proc_report_dir + '{basecaller}/sequencing_summary.txt'
    output:
        rules.process.input.filtered[0] + '.index.readdb'
    params:
        fast5 = config.get('fast5_dir'),
        nanopolish_path = config.get('nanopolish_path', 'nanopolish')
    message:
        "Be sure you're running a version of Nanopolish built from the repo, not Conda (e.g. > v0.11.0)"
    conda:
        resource_filename("mars", "snakemake/envs/polishing.yaml")
    shell:
        "{params.nanopolish_path} index -d {params.fast5} -s {input.summary} {input.fastq}"
        
rule nanopolish_variants:
    input:
        contigs = rules.assemble.input,
        reads = rules.process.input.filtered,
        bam = rules.align_reads.output,
        index = rules.index_nanopolish.output
    output:
        directory(pol_working_dir + '{sample}/{assembler}/nanopolish.workspace')
    conda:
        resource_filename("mars", "snakemake/envs/polishing.yaml")
    threads:
        config.get('nanopolish_threads', 8)
    shell:
        """
        python $CONDA_PREFIX/bin/nanopolish_makerange.py {input.contigs} |\
        parallel --results {output} -P {threads} \
        nanopolish variants \
        --consensus \
        --outfile {output}/polished.{{1}}.vcf \
        --window {{1}} \
        --reads {input.reads} \
        --bam {input.bam} \
        --genome {input.contigs}
        """

rule nanopolish_vcf2fasta:
    input:
        contigs = rules.assemble.input,
        variants = rules.nanopolish_variants.output
    output:
        pol_output_dir + '{sample}/{assembler}/polished_assembly.fasta'
    conda:
        resource_filename("mars", "snakemake/envs/polishing.yaml")
    shell:
        """
        nanopolish vcf2fasta -g {input.contigs} \
        {input.variants}/polished.*.vcf > {output}
        """

rule assess_polished_quast:
    input:
        rules.nanopolish_vcf2fasta.output
    output:
        directory(pol_reports_dir + '{sample}/{assembler}/quast')
    conda:
        resource_filename("mars", "snakemake/envs/assembling.yaml")
    threads:
        config.get("quast_threads", 8)    
    shell:
        """
        quast {input} \
        -o {output} \
        -r {config[ref_genome_fp]} \
        -g {config[ref_genome_features_fp]} \
        -t {threads}
        """
    
rule polish:
    input:
        rules.nanopolish_vcf2fasta.output

rule polish_all:
    input:
        assemblies = expand(
            rules.polish.input,
            assembler=config.get('assembler', ''),
            sample=list(samples.sample_label)),
        reports = expand(
            rules.assess_assembled_quast.output,
            assembler=config.get('assembler', ''),
            sample=list(samples.sample_label))
