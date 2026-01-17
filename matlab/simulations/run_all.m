%% Run all MATLAB simulations

fprintf('Running orbit propagation...\n');
run('matlab/simulations/orbit_propagation.m');

fprintf('Running attitude detumble...\n');
run('matlab/simulations/attitude_detumble.m');

fprintf('Running power budget...\n');
run('matlab/simulations/power_budget.m');

fprintf('Running link budget...\n');
run('matlab/simulations/link_budget.m');

fprintf('All MATLAB simulations complete.\n');
