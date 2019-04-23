#=====================================================#
# MARS/assemble: Bacterial Genome Assembly Workflow   #
#=====================================================#

from pkg_resources import resource_filename
from pathlib import Path

from mars import padded_barcodes

localrules: assemble, assemble_all

asm_output_dir = output_dir + 'assemble/'
asm_working_dir = working_dir + 'assemble/'
asm_reports_dir = reports_dir + 'assemble/'

rule create_ref_sketch:
    '''Creates a mash sketch of all provided reference genomes.'''
    output:
        asm_working_dir + 'reference_genomes.msh'
    params:
        k = config.get('mash_k_size', 32),
        ref_dir = config.get('ref_genomes_dir')
    threads:
        config.get('mash_threads', 8)
    conda:
        resource_filename("mars", "snakemake/envs/mash.yaml")
    shell:        
        """
        mash sketch -k {params.k} -p {threads} -o {output} {params.ref_dir}/*
        """

rule calc_ref_dist_mash:
    '''
    Calculates the minhash (mash) distance of the filtered reads
    to all the provided reference genomes.
    '''
    input:
        sketch = rules.create_ref_sketch.output,
        reads = rules.process.input.filtered
    output:
        asm_reports_dir + '{sample}/mash_distance_to_ref_genomes.tsv'
    threads:
        config.get('mash_threads', 1)
    conda:
        resource_filename("mars", "snakemake/envs/mash.yaml")
    shell:
        """
        mash dist -p {threads} {input.sketch} {input.reads} |\
        sort -t$'\t' -k3 -n > {output}
        """

checkpoint mark_ref_genome:
    '''
    Writes the name of the closest reference genome to a flag file 
    for downstream rules. 
    '''
    input:
        rules.calc_ref_dist_mash.output
    output:
        directory(asm_working_dir + '{sample}/ref_genome')
    shell:
        """
        mkdir -p {output} &&
        ref=$(basename $(head -1 {input} | cut -f1)) &&
        touch {output}/$ref
        """

def ref_genome(wc):
    '''Returns the location of the ref genome in the ref genome directory'''
    ref_dir = checkpoints.mark_ref_genome.get(**wc).output[0]
    refs = [p.name for p in Path(ref_dir).glob("*.f*")]
    return expand(config.get('ref_genomes_dir') + '/{ref}', ref=refs)

rule assemble_canu:
    input:
        rules.process.input.filtered
    output:
        asm_output_dir + '{sample}/canu/assembly.fasta'
    params:
        contigs = asm_working_dir + '{sample}/canu/canu.contigs.fasta',
        out_dir = asm_working_dir + '{sample}/canu',
        genome_size = config.get('ref_genome_size', 0)
    resources:
        mem_mb = config.get('canu_max_mem', 0)
    threads:
        config.get('assembler_threads', 4)
    conda:
        resource_filename("mars", "snakemake/envs/canu.yaml")
    shell:
        """
        canu -p canu -d {params.out_dir} \
        genomeSize={params.genome_size} \
        correctedErrorRate=0.16 \
        useGrid=false maxMemory={resources.mem_mb}M maxThreads={threads} \
        stopOnReadQuality=false \
        -nanopore-raw {input} && \
        cp {params.contigs} {output}
        """        

rule assemble_unicycler:
    input:
        rules.process.input.filtered
    output:
        fasta = asm_output_dir + '{sample}/unicycler/assembly.fasta',
        gfa = asm_output_dir + '{sample}/unicycler/assembly.gfa',
    threads:
        config.get('assembler_threads', 8)
    params:
        out_dir = asm_working_dir + '{sample}/unicycler',
        mode = config.get("unicycler_mode", "normal")
    conda:
        resource_filename("mars", "snakemake/envs/unicycler.yaml")
    shell:
        """
        unicycler -l {input} -o {params.out_dir} -t {threads} \
        --mode {params.mode} &&\
        cp {params.out_dir}/assembly.fasta {output.fasta} &&\
        cp {params.out_dir}/assembly.gfa {output.gfa}
        """

rule assemble_rebaler:
    input:
        reference = ref_genome,
        reads = rules.process.input.filtered
    output:
        asm_output_dir + '{sample}/rebaler/assembly.fasta'
    threads:
        config.get('assembler_threads', 8)
    conda:
        resource_filename("mars", "snakemake/envs/rebaler.yaml")
    shell:
        "rebaler -t {threads} {input.reference} {input.reads} > {output}"

rule assemble_flye:
    input:
        reference = ref_genome,
        reads = rules.process.input.unfiltered
    output:
        assembly = asm_output_dir + '{sample}/flye/assembly.fasta',
        graph = asm_output_dir + '{sample}/flye/assembly_graph.gfa',
        contig_info = asm_reports_dir + '{sample}/flye/assembly_info.txt'
    params:
        genome_size = config.get('ref_genome_size'),
        out_dir = asm_output_dir + '{sample}/flye',
        iterations = config.get('flye_polish_iterations', 1)
    conda:
        resource_filename("mars", "snakemake/envs/flye.yaml")
    threads:
        config.get("assembler_threads", 8)
    shell:
        """
        GENOME_SIZE=$(wc -c {input.reference} | cut -f1 -d' ') &&
        flye \
        --nano-raw {input.reads} \
        --genome-size $GENOME_SIZE \
        --out-dir {params.out_dir} \
        --threads {threads} \
        --iterations {params.iterations} &&
        cp {params.out_dir}/assembly_info.txt {output.contig_info}
        """

rule assemble:
    input: asm_output_dir + '{sample}/{assembler}/assembly.fasta'
        
rule assess_assembled_quast:
    input:
        reference=ref_genome,
        assembly=rules.assemble.input
    output:
        directory(asm_reports_dir + '{sample}/{assembler}/quast')
    conda:
        resource_filename("mars", "snakemake/envs/quast.yaml")
    threads:
        config.get("assembler_threads", 8)    
    shell:
        """
        quast {input.assembly} \
        -o {output} \
        -r {input.reference} \
        -t {threads}
        """

rule assemble_all:
    input:
        assemblies = expand(
            rules.assemble.input,
            assembler=config.get('assembler', ''),
            sample=list(samples.sample_label)),
        reports = expand(
            rules.assess_assembled_quast.output,
            assembler=config.get('assembler', ''),
            sample=list(samples.sample_label))


