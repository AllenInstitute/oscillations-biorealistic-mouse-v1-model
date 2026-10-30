import subprocess
import json
import os
import argparse
# import numpy as np
# import tensorflow as tf
# import tensorflow as tf
from v1_model_utils import toolkit
# # script_path = "bash d

# Create argument parser
parser = argparse.ArgumentParser()

# Define arguments
parser.add_argument('--task_name', default='drifting_gratings_firing_rates_distr', type=str)
parser.add_argument('--data_dir', default='GLIF_network', type=str)
parser.add_argument('--results_dir', default='Simulation_results', type=str)
parser.add_argument('--synaptic_data_dir', default='synaptic_data', type=str,
                    help='Directory with tau_basis.npy and basis_function_weights.csv; '
                         'use synaptic_data_<variant> for a model variant')
parser.add_argument('--restore_from', default='', type=str)
parser.add_argument('--comment', default='', type=str)
parser.add_argument('--delays', default='100,0', type=str)
parser.add_argument('--scale', default='2,2', type=str)
parser.add_argument('--dtype', default='float32', type=str)

parser.add_argument('--optimizer', default='adam', type=str)
parser.add_argument('--learning_rate', default=0.001, type=float)
parser.add_argument('--rate_cost', default=100., type=float) #100
parser.add_argument('--voltage_cost', default=1., type=float)
parser.add_argument('--sync_cost', default=1., type=float)
parser.add_argument('--osi_cost', default=1., type=float)
parser.add_argument('--osi_loss_subtraction_ratio', default=0., type=float)
parser.add_argument('--osi_loss_method', default='crowd_osi', type=str)

parser.add_argument('--dampening_factor', default=0.1, type=float)
parser.add_argument('--recurrent_dampening_factor', default=0.1, type=float)
# parser.add_argument('--dampening_factor', default=0.5, type=float)
# parser.add_argument('--recurrent_dampening_factor', default=0.5, type=float)
parser.add_argument('--input_weight_scale', default=1.0, type=float)
parser.add_argument('--gauss_std', default=0.3, type=float)
parser.add_argument('--recurrent_weight_regularization', default=0.0, type=float)
parser.add_argument('--recurrent_weight_regularizer_type', default="mean", type=str)
parser.add_argument('--voltage_penalty_mode', default='range', type=str)
parser.add_argument('--lr_scale', default=1.0, type=float)
# parser.add_argument('--input_f0', default=0.2, type=float)
parser.add_argument('--temporal_f', default=2.0, type=float)
parser.add_argument('--max_time', default=-1, type=float)
parser.add_argument('--loss_core_radius', default=400.0, type=float)
parser.add_argument('--plot_core_radius', default=400.0, type=float)

parser.add_argument('--n_runs', default=1, type=int) # number of runs with n_epochs each, with an osi/dsi evaluation after each
parser.add_argument('--n_epochs', default=50, type=int)
parser.add_argument('--batch_size', default=1, type=int)
parser.add_argument('--neurons', default=0, type=int)
parser.add_argument('--steps_per_epoch', default=20, type=int)
parser.add_argument('--val_steps', default=1, type=int)

parser.add_argument('--n_input', default=17400, type=int)
parser.add_argument('--seq_len', default=600, type=int)
# parser.add_argument('--n_cues', default=3, type=int)
# parser.add_argument('--recall_duration', default=40, type=int)
parser.add_argument('--cue_duration', default=40, type=int)
# parser.add_argument('--interval_duration', default=40, type=int)
# parser.add_argument('--examples_in_epoch', default=32, type=int)
# parser.add_argument('--validation_examples', default=16, type=int)
parser.add_argument('--seed', default=3000, type=int)
parser.add_argument('--neurons_per_output', default=16, type=int)
parser.add_argument('--fano_samples', default=500, type=int)

# parser.add_argument('--float16', default=False, action='store_true')
# parser.add_argument('--caching', default=True, action='store_true')
parser.add_argument('--caching', dest='caching', action='store_true')
parser.add_argument('--nocaching', dest='caching', action='store_false')
parser.set_defaults(caching=True)

parser.add_argument('--core_only', default=False, action='store_true')
parser.add_argument('--core_loss', default=False, action='store_true')
parser.add_argument('--hard_reset', default=False, action='store_true')

parser.add_argument('--train_recurrent', default=False, action='store_true')
parser.add_argument('--train_recurrent_per_type', default=False, action='store_true')
parser.add_argument('--train_input', default=False, action='store_true')
parser.add_argument('--train_noise', default=False, action='store_true')

parser.add_argument('--connected_selection', default=True, action='store_true')
parser.add_argument('--neuron_output', default=False, action='store_true')

# parser.add_argument('--visualize_test', default=False, action='store_true')
parser.add_argument('--pseudo_gauss', default=False, action='store_true')
parser.add_argument('--bmtk_compat_lgn', default=True, action='store_true')
parser.add_argument('--reset_every_step', default=False, action='store_true')
parser.add_argument('--spontaneous_training', default=False, action='store_true')
parser.add_argument('--random_weights', default=False, action='store_true')
parser.add_argument('--uniform_weights', default=False, action='store_true')
parser.add_argument('--gradient_checkpointing', default=False, action='store_true')
parser.add_argument('--rotation', default='ccw', type=str)
parser.add_argument('--print_only', default=False, action='store_true', help='Only print the commands without submitting them')
parser.add_argument('--neuropixels_df', default='Neuropixels_data/v1_OSI_DSI_DF.csv', type=str, help='File name of the Neuropixels DataFrame for OSI/DSI analysis')


def run_command_locally(command, print_only=False, output_file=None, error_file=None):
    """ 
    Run a command locally instead of submitting to SLURM.
    If print_only is True, just print the command without running.
    """
    if print_only:
        print("\n=== COMMAND ===")
        print(command)
        return None
    
    # Create output directories if they don't exist
    if output_file:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
    if error_file:
        os.makedirs(os.path.dirname(error_file), exist_ok=True)
    
    # Run the command locally
    print(f"\n=== Running: {command} ===")
    
    # Open output files if specified
    stdout_handle = open(output_file, 'w') if output_file else None
    stderr_handle = open(error_file, 'w') if error_file else None
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Warning: Command exited with code {result.returncode}")
        else:
            print(f"Completed successfully")
            
        return result.returncode
    
    finally:
        if stdout_handle:
            stdout_handle.close()
        if stderr_handle:
            stderr_handle.close()

def main():                
    # Initialize the flags and customize the simulation main characteristics
    flags = parser.parse_args()
        
    # Get the neurons of each column of the network
    v1_neurons = flags.neurons

    # Save the configuration of the model based on the main features
    flag_str = f'v1_{v1_neurons}'
    for name, value in vars(flags).items():
        if value != parser.get_default(name) and name in ['n_input', 'core_only', 'connected_selection', 'random_weights', 'uniform_weights']:
            flag_str += f'_{name}_{value}'

    # Define flag string as the second part of results_path
    results_dir = f'{flags.results_dir}/{flag_str}'
    os.makedirs(results_dir, exist_ok=True)
    print('Simulation results path: ', results_dir)
    # Save the flags configuration as a dictionary in a JSON file
    with open(os.path.join(results_dir, 'flags_config.json'), 'w') as fp:
        json.dump(vars(flags), fp)

    # Generate a ticker for the current simulation
    sim_name = toolkit.get_random_identifier('b_')
    logdir = os.path.join(results_dir, sim_name)
    print(f'> Results for {flags.task_name} will be stored in:\n {logdir} \n')

    # Define the training and evaluation script calls for local execution
    training_script = "python -u multi_training_single_gpu_split.py " 
    evaluation_script = "python -u osi_dsi_estimator.py " 

    # initial_benchmark_model = '/home/jgalvan/Desktop/Neurocoding/V1_GLIF_model/Simulation_results/v1_30000/b_3jo7/Best_model'
    initial_benchmark_model = ''

    # Append each flag to the string
    for name, value in vars(flags).items():
        # if value != parser.get_default(name) and name in ['learning_rate', 'rate_cost', 'voltage_cost', 'osi_cost', 'temporal_f', 'n_input', 'seq_len']:
        # if value != parser.get_default(name):
        if name not in ['seed', 'print_only']: 
            if type(value) == bool and value == False:
                training_script += f"--no{name} "
                evaluation_script += f"--no{name} "
            elif type(value) == bool and value == True:
                training_script += f"--{name} "
                evaluation_script += f"--{name} "
            else:
                training_script += f"--{name} {value} "
                evaluation_script += f"--{name} {value} "

    # Initial OSI/DSI test
    print("\n" + "="*80)
    print("Running Initial Evaluation")
    print("="*80)
    
    if initial_benchmark_model:
        initial_evaluation_cmd = evaluation_script + f"--seed {flags.seed} --ckpt_dir {logdir}  --run_session {-1} --restore_from {initial_benchmark_model}"
    else:
        initial_evaluation_cmd = evaluation_script + f"--seed {flags.seed} --ckpt_dir {logdir}  --run_session {-1}"

    run_command_locally(
        initial_evaluation_cmd,
        flags.print_only,
        output_file=f"Out/{sim_name}_{v1_neurons}_initial_test.out",
        error_file=f"Error/{sim_name}_{v1_neurons}_initial_test.err"
    )

    # Run training and evaluation sequentially in a loop
    for i in range(flags.n_runs):
        print("\n" + "="*80)
        print(f"Run {i+1}/{flags.n_runs}: Training")
        print("="*80)
        
        # Build training command
        if i == 0 and initial_benchmark_model:
            training_cmd = training_script + f"--seed {flags.seed + i} --ckpt_dir {logdir} --run_session {i} --restore_from {initial_benchmark_model}"
        else:
            training_cmd = training_script + f"--seed {flags.seed + i} --ckpt_dir {logdir} --run_session {i}"
        
        # Run training
        return_code = run_command_locally(
            training_cmd,
            flags.print_only,
            output_file=f"Out/{sim_name}_{v1_neurons}_train_{i}.out",
            error_file=f"Error/{sim_name}_{v1_neurons}_train_{i}.err"
        )
        
        if not flags.print_only and return_code != 0:
            print(f"\nWarning: Training run {i} failed with return code {return_code}")
            print("Continuing with next run...\n")
        
        # Run evaluation after training (if n_runs > 1)
        if flags.n_runs > 1:
            print("\n" + "="*80)
            print(f"Run {i+1}/{flags.n_runs}: Evaluation")
            print("="*80)
            
            evaluation_cmd = evaluation_script + f"--seed {flags.seed + i} --ckpt_dir {logdir} --restore_from 'Intermediate_checkpoints' --run_session {i}"
            
            return_code = run_command_locally(
                evaluation_cmd,
                flags.print_only,
                output_file=f"Out/{sim_name}_{v1_neurons}_test_{i}.out",
                error_file=f"Error/{sim_name}_{v1_neurons}_test_{i}.err"
            )
            
            if not flags.print_only and return_code != 0:
                print(f"\nWarning: Evaluation run {i} failed with return code {return_code}\n")

    # Final evaluation with the best model
    print("\n" + "="*80)
    print("Running Final Evaluation with Best Model")
    print("="*80)
    
    final_evaluation_cmd = evaluation_script + f"--seed {flags.seed + flags.n_runs - 1} --ckpt_dir {logdir} --restore_from 'Best_model' --run_session {flags.n_runs - 1}"
    
    run_command_locally(
        final_evaluation_cmd,
        flags.print_only,
        output_file=f"Out/{sim_name}_{v1_neurons}_test_final.out",
        error_file=f"Error/{sim_name}_{v1_neurons}_test_final.err"
    )

    if flags.print_only:
        print("\n" + "="*80)
        print("COMMANDS WERE ONLY PRINTED, NOT EXECUTED")
        print("="*80 + "\n")
    else:
        print("\n" + "="*80)
        print("All training and evaluation runs completed!")
        print(f"Results saved to: {logdir}")
        print("="*80 + "\n")


if __name__ == '__main__':
    main()
