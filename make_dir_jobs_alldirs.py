# %%

"""
the goal is to make the cluter running as easy as possible, while permitting necessary
manipulations of the parameters.

Eventually, the command to run is like this
mpirun --oversubscribe -np 8 python run_filternet.py <config_file>
or
python run_pointnet.py -n 8 <config_file>
8 should be changed to an appropriate number of cores (using a big number may not be helpful)

These commands should be stored in the job file


Let's break down into steps

* Get the base config and identify parameters
* Write down config files for each operation (config file number should be a serial number)
* Write into a job file (single job files)

* I'd like to make this compatible with both filternet simulations and main simulations


"""

import json
import os
import numpy as np
import argparse
import pathlib

_default_core_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core")


def sbatch_boilerplate(file, logdir, config_counts, memory=32, jobs=1, threads=8):
    # 30 s simulations; the published runs used 24 h / 60 GB
    time = "24:00:00"

    file.write("#!/bin/bash\n")
    file.write("#SBATCH --mail-type=ALL\n")
    file.write("#SBATCH --mail-user=beatriz.herrera@alleninstitute.org\n")
    file.write("#SBATCH --partition=d3\n")
    # if full_memory:  # full model needs a lot of memory
    #     file.write("#SBATCH -N1 -c1 -n4\n")
    #     file.write("#SBATCH --mem-per-cpu=60G\n")
    #     file.write("#SBATCH -t2:00:00\n")
    # else:
    #     file.write("#SBATCH -N1 -c1 -n8\n")
    #     file.write("#SBATCH --mem-per-cpu=15G\n")
    #     file.write("#SBATCH -t1:00:00\n")
    file.write(f"#SBATCH -N1 -n1 -c{jobs * threads}\n")
    # file.write(f"#SBATCH --mem-per-cpu={memory}G\n")
    # now better to specify the total memory
    file.write(f"#SBATCH --mem={memory}G\n")
    file.write(f"#SBATCH -t{time}\n")

    file.write("#SBATCH --qos=d3\n")
    file.write(f"#SBATCH --output={logdir}/slurm-%A_%a.out\n")
    file.write(f"#SBATCH --error={logdir}/slurm-%A_%a.err\n")
    # array ID range includes both edges
    file.write(f"#SBATCH --array=0-{config_counts-1}\n\n")
    file.write(
        # "source /allen/programs/mindscope/workgroups/realistic-model/shinya.ito/activate_custom_nest_sdk_develop.sh\n"
        # "source /allen/programs/mindscope/workgroups/realistic-model/shinya.ito/miniconda3/bin/activate new_v1\n"
        'source "$(conda info --base)/etc/profile.d/conda.sh"\n'
        "conda activate osc-mouse-v1-model\n"
    )
    # file.write(
    #     "module use /allen/programs/braintv/workgroups/modelingsdk/modulefiles\n"
    # )
    # # activating double alpha version of nest.
    # file.write(
    #     "module load anaconda/22.10 cmake/3.25.2 gcc/10.1.0-centos7 openmpi/4.1.5-gcc10\n"
    # )
    # file.write(
    #     "conda activate /allen/programs/mindscope/workgroups/realistic-model/shinya.ito/miniconda3/envs/custom_nest\n"
    # )
    # file.write(
    #     "source /allen/programs/mindscope/workgroups/realistic-model/shinya.ito/custom_nest/nest-simulator-3.4/build/bin/nest_vars.sh\n"
    # )
    # old code
    # file.write("module load mpich/3.4.1-slurm\n")
    # file.write("module load conda/4.5.4\n")
    # f.write("module load nest/2.20.1-py37-slurm\n")
    # f.write("source activate v1_glif_modeling\n")
    # file.write("source activate bmtk-latest-py37-slurm\n")


def memory_jobs(basedir):
    if "full" in basedir:
        memory = 120
        jobs = 1
        threads = 8
    elif "forty" in basedir:
        memory = 60
        jobs = 1
        threads = 8
    elif ("core" in basedir) or ("twenty" in basedir):
        memory = 60
        jobs = 1
        threads = 8
    else:  # including small, tiny, etc.
        memory = 10
        jobs = 1
        threads = 8
    return memory, jobs, threads


def write_job(
    basedir, config_counts, modfile, network_folder="network", network_option="adjusted"
):
    configdir = basedir + "/configs/all8dir_10trials"
    jobdir = basedir + "/jobs"
    logdir = jobdir + "/logs"

    file_name = jobdir + "/all8dir_10trials"

    if network_folder != "network":
        file_name = jobdir + f"/all8dir_10trials_{network_folder}"
        configdir = configdir + f"_{network_folder}"

    if network_option != "adjusted":
        file_name += f"_{network_option}"
        configdir = configdir + f"_{network_option}"

    file_name += ".sh"

    with open(file_name, "w") as f:
        memory, jobs, threads = memory_jobs(basedir)
        # if "full" in basedir:
        #     memory = 60
        #     jobs = 4
        # elif "forty" in basedir:
        #     memory = 30
        #     jobs = 8
        # elif ("core" in basedir) or ("twenty" in basedir):
        #     memory = 15
        #     jobs = 8
        # else:  # including small, tiny, etc.
        #     memory = 4
        #     jobs = 8
        sbatch_boilerplate(
            f, logdir, config_counts, memory=memory, jobs=jobs, threads=threads
        )
        # f.write("module load nest/2.20.1-py37-slurm\n")

        config_array = configdir + "/config_$SLURM_ARRAY_TASK_ID.json"
        if modfile is not None:
            f.write(
                # f"srun --mpi=pmi2 python run_pointnet.py {config_array} -m {modfile}"
                # f"mpirun -np {jobs} python run_pointnet.py {config_array} -m {modfile}"
                f"python run_pointnet.py {config_array} -m {modfile} -n {threads}\n"
            )
        else:
            # f.write(f"srun --mpi=pmi2 python run_pointnet.py {config_array}")
            f.write(f"python run_pointnet.py {config_array} -n {threads}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Making a cluster-ready job file.")
    parser.add_argument("basedir", type=str)
    parser.add_argument("--network_folder", type=str, default="network")
    parser.add_argument("--network_option", type=str, default="adjusted")  # checkpoint
    parser.add_argument(
        "-m", "--modfile", type=str, default=None, help="The modulation file to use."
    )
    parser.add_argument(
        "--core_dir", type=str, default=_default_core_dir,
        help="Path to a core network whose concatenated 8-direction LGN/bkg inputs "
             "(filternet_8dir_10trials/8dir_trial<N>_lgn_spikes.h5 and "
             "bkg_8dir_10trials/bkg_spikes_250Hz_3s_trial<N>.h5, made by "
             "concat_dg_lgn_inputs.ipynb / concat_dg_bkg_inputs.ipynb) are used as input. "
             f"Default: {_default_core_dir}"
    )
    parser.add_argument(
        "--dt", type=float, default=0.1,
        help="Simulation time step (ms); overrides the run.dt of the base config "
             "(config_templates use 0.25). Default: 0.1"
    )
    args = parser.parse_args()

    filterdir = args.basedir + "/filternet_8dir_10trials"

    if args.network_folder == "network":
        base_config = (
            args.basedir + "/configs/config.json"
            if args.network_option == "adjusted"
            else args.basedir + "/configs/config_checkpoint.json"
        )
        outdir = "all8dir_10trials"
        configdir = args.basedir + "/configs/all8dir_10trials"
    else:
        base_config = (
            args.basedir + "/configs/config.json"
            if args.network_option == "adjusted"
            else args.basedir + "/configs/config_checkpoint.json"
        )
        outdir = "all8dir_10trials_" + args.network_folder
        configdir = args.basedir + "/configs/all8dir_10trials_" + args.network_folder

    outdir = outdir + f"_{args.network_option}"
    # print("outdir", outdir)
    configdir = configdir + f"_{args.network_option}"

    jobdir = args.basedir + "/jobs"
    logdir = args.basedir + "/jobs/logs"
    pathlib.Path(configdir).mkdir(parents=True, exist_ok=True)
    pathlib.Path(logdir).mkdir(parents=True, exist_ok=True)

    # take the base config file
    js = json.load(open(base_config))

    # define necessary elements
    trials = range(10)
    config_counts = 0

    filterdir_indv = f"{args.core_dir}/filternet_8dir_10trials"

    for trial in trials:
        outdir_indv = f"$BASE_DIR/{outdir}/trial{trial}"

        js["manifest"]["$BASE_DIR"] = "${configdir}/../.."

        if args.network_folder != "network":
            js["manifest"][
                "$NETWORK_DIR"
            ] = f"$BASE_DIR/network_{args.network_folder}"

        js["manifest"]["$LGNINPUT_DIR"] = filterdir_indv
        js["manifest"]["$OUTPUT_DIR"] = outdir_indv
        config_name = configdir + f"/config_{config_counts}.json"
        # if the config file contains background input, change the input file
        if "$BKGINPUT_DIR" in js["manifest"].keys():
            bkgdir_indv = (
                f"{args.core_dir}/bkg_8dir_10trials"
            )
            js["manifest"]["$BKGINPUT_DIR"] = bkgdir_indv

        js["run"]["duration"] = 30000.0 # 30 seconds
        js["run"]["dt"] = args.dt

        js["inputs"]["LGN_spikes"][
            "input_file"
        ] = f"$LGNINPUT_DIR/8dir_trial{trial}_lgn_spikes.h5"
        js["inputs"]["BKG_spikes"][
            "input_file"
        ] = f"$BKGINPUT_DIR/bkg_spikes_250Hz_3s_trial{trial}.h5"

        config_counts += 1

        json.dump(js, open(config_name, "w"), indent=2)

    write_job(
        args.basedir,
        config_counts,
        args.modfile,
        network_folder=args.network_folder,
        network_option=args.network_option,
    )
