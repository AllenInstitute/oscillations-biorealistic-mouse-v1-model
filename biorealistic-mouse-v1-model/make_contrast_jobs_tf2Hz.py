# %%

import json
import numpy as np
import argparse
import os
import make_osi_jobs as moj
import pathlib
import stimulus_trials as st

_default_core_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Making a cluster-ready contrast job files."
    )
    parser.add_argument("basedir", type=str)
    parser.add_argument("--filternet", action="store_true")
    parser.add_argument(
        "-m", "--modfile", type=str, default=None, help="The modulation file to use."
    )
    parser.add_argument(
        "--memory", type=int, default=20, help="The memory to use in GB."
    )
    parser.add_argument(
        "--network_option", type=str, default="plain", help="The network option."
    )
    parser.add_argument(
        "--core_dir", type=str, default=_default_core_dir,
        help="Path to a core network whose filternet/bkg outputs will be reused as LGN "
             "input for main-simulation jobs. Ignored when --filternet is set. "
             f"Default: {_default_core_dir}"
    )

    parser.add_argument(
        "--dt", type=float, default=0.1,
        help="Simulation time step (ms) for main-simulation configs; overrides the "
             "run.dt of the base config (config_templates use 0.25). Default: 0.1"
    )
    args = parser.parse_args()

    filternet_base = "$BASE_DIR" if args.filternet else args.core_dir

    if args.filternet:
        job_name = "contrasts_temporal_f2Hz"
    else:
        job_name = f"contrasts_temporal_f2Hz_{args.network_option}"

    filterdir = args.basedir + f"/filternet_{job_name}"
    if args.filternet:
        base_config = args.basedir + "/configs/config_filternet.json"
        outdir = filterdir
        configdir = args.basedir + f"/configs/filternet_{job_name}"
    else:
        base_config = args.basedir + "/configs/config_plain.json"
        outdir = args.basedir + f"/output_{job_name}"
        configdir = args.basedir + f"/configs/{job_name}"

    jobdir = args.basedir + "/jobs"
    logdir = args.basedir + "/jobs/logs"

    pathlib.Path(configdir).mkdir(parents=True, exist_ok=True)
    pathlib.Path(logdir).mkdir(parents=True, exist_ok=True)

    # take the base config file
    js = json.load(open(base_config))

    # define necessary elements
    stim_iter = st.ContrastStimulus()
    config_counts = 0
    for angle, contrast, trial in stim_iter:
        filterdir_indv = f"{filternet_base}/filternet_contrasts/angle{int(angle)}_contrast{contrast}_temporal_f2Hz_trial{trial}"
        outdir_indv = (
            f"$BASE_DIR/{job_name}/angle{int(angle)}_contrast{contrast}_temporal_f2Hz_trial{trial}"
        )

        js["manifest"]["$BASE_DIR"] = "${configdir}/../.."
        if args.filternet:
            js["inputs"]["LGN_spikes"]["theta"] = angle
            js["inputs"]["LGN_spikes"]["contrast"] = contrast
            js["inputs"]["LGN_spikes"]["trial"] = trial
            # important to match TF with Millman et al. 2020
            js["inputs"]["LGN_spikes"]["temporal_f"] = 2.0
            # randomize the phase for each trial
            js["inputs"]["LGN_spikes"]["phase"] = np.random.rand() * 360
            js["manifest"]["$OUTPUT_DIR"] = filterdir_indv
            config_name = configdir + f"/config_filternet_{config_counts}.json"
        else:  # main job
            js["manifest"]["$LGNINPUT_DIR"] = filterdir_indv
            js["manifest"]["$OUTPUT_DIR"] = outdir_indv
            js["run"]["dt"] = args.dt
            config_name = configdir + f"/config_{config_counts}.json"

            # change the edge file if not plain
            if args.network_option != "plain":
                js["networks"]["edges"][0][
                    "edges_file"
                ] = f"$NETWORK_DIR/v1_v1_edges_{args.network_option}.h5"
            # also change the bkg for TF checkpoint
            if any(
                [opt in args.network_option for opt in ["checkpoint", "noweightloss"]]
            ):
                js["networks"]["edges"][2][
                    "edges_file"
                ] = f"$NETWORK_DIR/bkg_v1_edges_{args.network_option}.h5"

            # if the config file contains background input, change the input file
            if "$BKGINPUT_DIR" in js["manifest"].keys():
                bkgdir_indv = f"{filternet_base}/bkg_contrasts/angle{int(angle)}_contrast{contrast}_trial{trial}"
                js["manifest"]["$BKGINPUT_DIR"] = bkgdir_indv
        config_counts += 1

        json.dump(js, open(config_name, "w"), indent=2)

    if args.filternet:
        moj.write_filternet_job(args.basedir, config_counts, job_name, args.memory)
    else:
        moj.write_job(args.basedir, config_counts, args.modfile, job_name, args.memory)
