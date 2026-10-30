#!/bin/bash

# total_neurons = 296991
# core_neurons = 66652
python parallel_training_testing_allen_vscode.py --neurons 66652 --seq_len 500 --loss_core_radius 200 --plot_core_radius 200 --delays 0,0 --train_recurrent --osi_loss_method 'crowd_osi' --osi_cost 10 --rate_cost 10000 --voltage_cost 1 --recurrent_weight_regularization 1 --sync_cost 0.3 --learning_rate 0.001 --n_runs 20 --n_epochs 50 --steps_per_epoch 25 --train_noise --data_dir 'GLIF_network_L6-syn-as-L4-syn' --results_dir 'Simulation_results_L6-syn-as-L4-syn' --synaptic_data_dir 'synaptic_data_L6-syn-as-L4-syn'
# --restore_from 'Simulation_results/v1_66652/b_z2kv/Best_model/checkpoint'
# To train a model variant, point --synaptic_data_dir at that variant's folder
# (create it manually by copying tau_basis.npy + basis_function_weights.csv from
# the pipeline's tf_props_<variant>/), e.g.:
# --synaptic_data_dir 'synaptic_data_L4-Sst2e-as-L6' --data_dir 'GLIF_network_L4-Sst2e-as-L6'
