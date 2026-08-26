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
    time = "72:00:00" #if (jobs * threads) <= 4 else "5:00:00"

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
        "source /allen/programs/mindscope/workgroups/realistic-model/shinya.ito/miniconda3/bin/activate new_v1\n"
        # "source /allen/programs/mindscope/workgroups/realistic-model/beatriz.herrera/miniconda3/bin/activate osc-biorealistic-v1-model\n"
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
        memory = 30
        jobs = 1
        threads = 8
    else:  # including small, tiny, etc.
        memory = 10
        jobs = 1
        threads = 8
    return memory, jobs, threads


def write_job(
    basedir,
    movie_name,
    config_counts,
    modfile,
    network_folder="network",
    network_option="adjusted",
):
    configdir = basedir + f"/configs/{movie_name}_10trials"
    jobdir = basedir + "/jobs"
    logdir = jobdir + "/logs"

    file_name = jobdir + f"/{movie_name}_10trials"
    if network_folder != "network":
        file_name += f"_{network_folder}"
        configdir = configdir + f"_{network_folder}"

    if network_option != "adjusted":
        file_name += f"_{network_option}"
        configdir += f"_{network_option}"

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
                f"python run_pointnet.py {config_array} -m {modfile} -n {threads}"
            )
        else:
            # f.write(f"srun --mpi=pmi2 python run_pointnet.py {config_array}")
            f.write(f"python run_pointnet.py {config_array} -n {threads}")


def write_filternet_job(basedir, movie_name, config_counts):
    configdir = basedir + f"/configs/filternet_{movie_name}_10trials"
    jobdir = basedir + "/jobs"
    logdir = jobdir + "/logs"

    with open(jobdir + f"/filternet_{movie_name}_10trials.sh", "w") as f:
        sbatch_boilerplate(f, logdir, config_counts)
        memory, jobs, cores = memory_jobs(basedir)
        # f.write("module load nest/2.20.1-py37-slurm\n")

        config_array = configdir + "/config_filternet_$SLURM_ARRAY_TASK_ID.json"
        # f.write(f"srun --mpi=pmi2 python run_filternet.py {config_array}")
        f.write(
            f"mpirun -np {jobs * cores} python run_filternet.py {config_array}"
        )
        # f.write(f"mpirun -np {jobs * cores} python run_filternet.py {config_array}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Making a cluster-ready job file.")
    parser.add_argument("basedir", type=str)
    parser.add_argument(
        "movie_name", type=str, choices=["natural_movie_one", "natural_movie_two"]
    )
    parser.add_argument("--filternet", action="store_true")
    parser.add_argument("--network_folder", type=str, default="network")
    parser.add_argument(
        "--network_option", type=str, default="checkpoint"
    )  # adjusted, checkpoint, plain
    parser.add_argument(
        "-m", "--modfile", type=str, default=None, help="The modulation file to use."
    )
    parser.add_argument(
        "--core_dir", type=str, default=_default_core_dir,
        help="Path to a core network whose filternet/bkg outputs will be reused as LGN "
             "input for main-simulation jobs. Ignored when --filternet is set. "
             f"Default: {_default_core_dir}"
    )
    args = parser.parse_args()

    filternet_base = "$BASE_DIR" if args.filternet else args.core_dir

    filterdir = args.basedir + f"/filternet_{args.movie_name}_10trials"
    if args.filternet:
        base_config = args.basedir + f"/configs/config_filternet_{args.movie_name}.json"
        outdir = filterdir
        configdir = args.basedir + f"/configs/filternet_{args.movie_name}_10trials"
    else:
        if args.network_folder == "network":
            base_config = (
                args.basedir + "/configs/config.json"
                if args.network_option == "adjusted"
                else args.basedir + "/configs/config_checkpoint.json"
            )
            outdir = f"{args.movie_name}_10trials"
            configdir = args.basedir + f"/configs/{args.movie_name}_10trials"
        else:
            base_config = (
                args.basedir + "/configs/config.json"
                if args.network_option == "adjusted"
                else args.basedir + "/configs/config_checkpoint.json"
            )
            outdir = f"{args.movie_name}_10trials_" + args.network_folder
            configdir = (
                args.basedir + f"/configs/{args.movie_name}_10trials_" + args.network_folder
            )

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

    for set in range(1, 9):
        for trial in trials:
            filterdir_indv = f"{filternet_base}/filternet_{args.movie_name}_10trials/set{set}_trial{trial}"
            outdir_indv = f"$BASE_DIR/{outdir}/set{set}_trial{trial}"
            js["manifest"]["$BASE_DIR"] = "${configdir}/../.."
            if args.network_folder != "network":
                js["manifest"][
                    "$NETWORK_DIR"
                ] = f"$BASE_DIR/network_{args.network_folder}"
            if args.filternet:
                js["inputs"]["LGN_spikes"][
                    "data_file"
                ] = f"$BASE_DIR/movies/{args.movie_name}.3s.120x240.set{set}.npz"
                js["inputs"]["LGN_spikes"]["trial"] = trial
                js["manifest"]["$OUTPUT_DIR"] = filterdir_indv
                config_name = configdir + f"/config_filternet_{config_counts}.json"
            else:  # main job
                js["manifest"]["$LGNINPUT_DIR"] = filterdir_indv
                js["manifest"]["$OUTPUT_DIR"] = outdir_indv
                config_name = configdir + f"/config_{config_counts}.json"
                # if the config file contains background input, change the input file
                if "$BKGINPUT_DIR" in js["manifest"].keys():
                    bkgdir_indv = f"{filternet_base}/bkg"
                    # f"{filternet_base}/bkg_{args.movie_name}_10trials/freq{freq}_trial{trial}"
                    js["manifest"]["$BKGINPUT_DIR"] = bkgdir_indv
            config_counts += 1

            json.dump(js, open(config_name, "w"), indent=2)

    if args.filternet:
        write_filternet_job(args.basedir, args.movie_name, config_counts)
    else:
        write_job(
            args.basedir,
            args.movie_name,
            config_counts,
            args.modfile,
            network_folder=args.network_folder,
            network_option=args.network_option,
        )
