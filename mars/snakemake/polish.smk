#
# MARS Assembly Polishing Workflow
# ----------------------------------------------------------------------
#
# Polishes an assembly and re-assesses the polished assembly quality.

pol_output_dir = output_dir + 'polish/'
pol_working_dir = working_dir + 'polish/'
pol_reports_dir = reports_dir + 'polish/'

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
        resource_filename("mars", "snakemake/envs/nanopolish.yaml")
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
        summary = expand(
            proc_reports_dir + '{basecaller}/sequencing_summary.txt',
            basecaller=config.get('basecaller'))
    output:
        rules.process.input.filtered[0] + '.index.readdb'
    params:
        fast5 = config.get('fast5_dir')
    conda:
        resource_filename("mars", "snakemake/envs/nanopolish.yaml")
    shell:
        "nanopolish index -d {params.fast5} -s {input.summary} {input.fastq}"
        
rule nanopolish_variants:
    input:
        contigs = rules.assemble.input,
        reads = rules.process.input.filtered,
        bam = rules.align_reads.output,
        index = rules.index_nanopolish.output
    output:
        directory(pol_working_dir + '{sample}/{assembler}/nanopolish/workspace')
    conda:
        resource_filename("mars", "snakemake/envs/nanopolish.yaml")
    threads:
        config.get('polisher_threads', 8)
    shell:
        """
        nanopolish_makerange.py {input.contigs} |\
        parallel --results {output} -P {threads} \
        nanopolish variants \
        --consensus \
        --outfile polished.{{1}}.vcf \
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
        pol_output_dir + '{sample}/{assembler}/nanopolish/polished_assembly.fasta'
    conda:
        resource_filename("mars", "snakemake/envs/nanopolish.yaml")
    shell:
        """
        nanopolish vcf2fasta -g {input.contigs} \
        {input.variants}/polished.*.vcf > {output}
        """

rule polish_medaka:
    input:
        contigs = rules.assemble.input,
        reads = rules.process.input.unfiltered,
    output:
        pol_output_dir + '{sample}/{assembler}/medaka/polished_assembly.fasta'
    threads:
        config.get('polisher_threads', 8)
    conda:
        resource_filename("mars", "snakemake/envs/medaka.yaml")
    shell:
        "medaka consensus -i {input.reads} -d {input.contigs} -o {output} -t {threads}"

rule polish:
    input:
        pol_output_dir + '{sample}/{assembler}/{polisher}/polished_assembly.fasta'

        
rule assess_polished_quast:
    input:
        reference=ref_genome,
        assembly=rules.polish.input
    output:
        directory(pol_reports_dir + '{sample}/{assembler}/{polisher}/quast')
    conda:
        resource_filename("mars", "snakemake/envs/quast.yaml")
    threads:
        config.get("quast_threads", 8)    
    shell:
        """
        quast {input} \
        -o {output} \
        -r {input.reference} \
        -t {threads}
        """

rule polish_all:
    input:
        assemblies = expand(
            rules.polish.input,
            assembler=config.get('assembler'),
            polisher=config.get('polisher'),
            sample=list(samples.sample_label)),
        reports = expand(
            rules.assess_polished_quast.output,
            assembler=config.get('assembler'),
            polisher=config.get('polisher'),
            sample=list(samples.sample_label))
