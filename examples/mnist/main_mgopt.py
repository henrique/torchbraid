#@HEADER
# ************************************************************************
# 
#                        Torchbraid v. 0.1
# 
# Copyright 2020 National Technology & Engineering Solutions of Sandia, LLC 
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, the U.S. 
# Government retains certain rights in this software.
# 
# Torchbraid is licensed under 3-clause BSD terms of use:
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
# 
# 3. Neither the name National Technology & Engineering Solutions of Sandia, 
# LLC nor the names of the contributors may be used to endorse or promote 
# products derived from this software without specific prior written permission.
# 
# Questions? Contact Eric C. Cyr (eccyr@sandia.gov)
# 
# ************************************************************************
#@HEADER

###
# Examples to compare TB+NI vs. TB+MG/Opt vs. TB+MG/Opt+Local
###
#
# TB+NI (no multilevel MGRIT)
# $ python3 main_mgopt.py --steps 8 --samp-ratio 0.1 --lp-fwd-cfactor 2 --lp-bwd-cfactor 2  --ni-levels 2 --lp-fwd-levels 1 --lp-bwd-levels 1 --mgopt-iter 0
#    ....
#    Train Epoch: 2 [0/5000 (0%)]        	Loss: 0.080145	Time Per Batch 0.074357
#    Train Epoch: 2 [500/5000 (10%)]     	Loss: 0.166830	Time Per Batch 0.073399
#    Train Epoch: 2 [1000/5000 (20%)]     	Loss: 0.291933	Time Per Batch 0.074495
#    Train Epoch: 2 [1500/5000 (30%)]     	Loss: 0.273469	Time Per Batch 0.074411
#    Train Epoch: 2 [2000/5000 (40%)]     	Loss: 0.237901	Time Per Batch 0.074258
#    Train Epoch: 2 [2500/5000 (50%)]     	Loss: 0.044225	Time Per Batch 0.075304
#    Train Epoch: 2 [3000/5000 (60%)]     	Loss: 0.450144	Time Per Batch 0.075509
#    Train Epoch: 2 [3500/5000 (70%)]     	Loss: 0.221938	Time Per Batch 0.075396
#    Train Epoch: 2 [4000/5000 (80%)]     	Loss: 0.170495	Time Per Batch 0.075297
#    Train Epoch: 2 [4500/5000 (90%)]     	Loss: 0.054780	Time Per Batch 0.075103
#    Train Epoch: 2 [5000/5000 (100%)]     	Loss: 0.529004	Time Per Batch 0.074992
#  
#    Test set: Average loss: 0.0107, Accuracy: 859/1000 (86%)
#
#
# TB+MG/Opt (Takes the above NI solver and adds 1 epoch of MG/Opt)  (no multilevel MGRIT)
# $ python3 main_mgopt.py --steps 12 --samp-ratio 0.1 --epochs 2 --mgopt-printlevel 1 --ni-levels 2 --mgopt-levels 2 --mgopt-nrelax-pre 2 --mgopt-nrelax-post 2 --lp-fwd-cfactor 2 --lp-bwd-cfactor 2 --lp-fwd-levels 1 --lp-bwd-levels 1 --lp-iters 1
#    ....
#    Train Epoch: 1 [50/5000 (1%)]     	Loss: 0.023389	Time Per Batch 0.780689
#    Train Epoch: 1 [550/5000 (11%)]     	Loss: 0.037635	Time Per Batch 0.781935
#    Train Epoch: 1 [1050/5000 (21%)]     	Loss: 0.171758	Time Per Batch 0.781161
#    Train Epoch: 1 [1550/5000 (31%)]     	Loss: 0.355388	Time Per Batch 0.781739
#    Train Epoch: 1 [2050/5000 (41%)]     	Loss: 0.286502	Time Per Batch 0.785055
#    Train Epoch: 1 [2550/5000 (51%)]     	Loss: 0.007334	Time Per Batch 0.787544
#    Train Epoch: 1 [3050/5000 (61%)]     	Loss: 0.472483	Time Per Batch 0.788244
#    Train Epoch: 1 [3550/5000 (71%)]     	Loss: 0.497987	Time Per Batch 0.788385
#    Train Epoch: 1 [4050/5000 (81%)]     	Loss: 0.550990	Time Per Batch 0.789357
#    Train Epoch: 1 [4550/5000 (91%)]     	Loss: 0.502712	Time Per Batch 0.794309
#    Train Epoch: 1 [5000/5000 (100%)]     	Loss: 1.374733	Time Per Batch 0.795855
#
#     Test set: Average loss: 0.0350, Accuracy: 830/1000 (83%)
#
#     Time per epoch: 8.04e+01 
#     Time per test:  8.51e-01 
#     Train Epoch: 2 [50/5000 (1%)]     	Loss: 0.735889	Time Per Batch 0.807446
#     Train Epoch: 2 [550/5000 (11%)]     	Loss: 0.490954	Time Per Batch 0.980087
#     Train Epoch: 2 [1050/5000 (21%)]     	Loss: 0.328517	Time Per Batch 0.899957
#     Train Epoch: 2 [1550/5000 (31%)]     	Loss: 0.291075	Time Per Batch 0.889309
#     Train Epoch: 2 [2050/5000 (41%)]     	Loss: 0.590438	Time Per Batch 0.907808
#     Train Epoch: 2 [2550/5000 (51%)]     	Loss: 0.002660	Time Per Batch 0.921411
#     Train Epoch: 2 [3050/5000 (61%)]     	Loss: 0.377914	Time Per Batch 0.933670
#     Train Epoch: 2 [3550/5000 (71%)]     	Loss: 0.170308	Time Per Batch 0.921680
#     Train Epoch: 2 [4050/5000 (81%)]     	Loss: 0.247056	Time Per Batch 0.947788
#     Train Epoch: 2 [4550/5000 (91%)]     	Loss: 0.700092	Time Per Batch 0.992239
#     Train Epoch: 2 [5000/5000 (100%)]     	Loss: 0.660585	Time Per Batch 1.025534
#
#     Test set: Average loss: 0.0316, Accuracy: 874/1000 (87%)
#
#
# TB+MG/Opt+Local (Takes the above NI solver and adds 2 epoch of MG/Opt with purely local relaxation on each level)
# $ python3 main_mgopt.py --steps 8 --samp-ratio 0.1 --epochs 2 --mgopt-printlevel 1 --ni-levels 2 --mgopt-levels 2 --mgopt-nrelax-pre 2 --mgopt-nrelax-post 2 --lp-fwd-cfactor 2 --lp-bwd-cfactor 2 --lp-fwd-levels 1 --lp-bwd-levels 1 --lp-fwd-finefcf --lp-bwd-finefcf --lp-fwd-relaxonlycg --lp-bwd-relaxonlycg --lp-fwd-finalrelax --lp-iters 1
#
# $ python3 main_mgopt.py --steps 12 --samp-ratio 0.1 --epochs 2 --mgopt-printlevel 1 --ni-levels 2 --mgopt-levels 2 --mgopt-nrelax-pre 2 --mgopt-nrelax-post 2 --lp-fwd-cfactor 2 --lp-bwd-cfactor 2 --lp-fwd-levels 1 --lp-bwd-levels 1 --lp-iters 1
#    ....
#
#

from __future__ import print_function
import numpy as np

import torch
from torchvision import datasets, transforms
from mpi4py import MPI
from mgopt import parse_args, mgopt_solver

def main():
  
  ##
  # Parse command line args (function defined above)
  args = parse_args()
  procs = MPI.COMM_WORLD.Get_size()
  rank  = MPI.COMM_WORLD.Get_rank()
  
  ##
  # Load training and testing data, while reducing the number of samples (if desired) for faster execution
  transform = transforms.Compose([transforms.ToTensor(),
                                  transforms.Normalize((0.1307,), (0.3081,))
                                 ])
  dataset = datasets.MNIST('./digit-data', download=False,transform=transform)
  train_size = int(50000*args.samp_ratio)
  test_size = int(10000*args.samp_ratio)
  #
  train_set = torch.utils.data.Subset(dataset,range(train_size))
  test_set  = torch.utils.data.Subset(dataset,range(train_size,train_size+test_size))
  #
  train_loader = torch.utils.data.DataLoader(train_set,batch_size=args.batch_size,shuffle=False)
  test_loader = torch.utils.data.DataLoader(test_set,batch_size=args.batch_size,shuffle=False)
  print("\nTraining setup:  Batch size:  " + str(args.batch_size) + "  Sample ratio:  " + str(args.samp_ratio) + "  MG/Opt Epochs:  " + str(args.epochs) )
  
  ##
  # Compute number of nested iteration steps, going from fine to coarse
  ni_steps = np.array([int(args.steps/(args.ni_rfactor**(args.ni_levels-i-1))) for i in range(args.ni_levels)])
  ni_steps = ni_steps[ ni_steps != 0 ]
  local_ni_steps = np.flip( np.array(ni_steps / procs, dtype=int) )
  print("\nNested iteration steps:  " + str(ni_steps))

  ##
  # Define ParNet parameters for each nested iteration level, starting from fine to coarse
  networks = [] 
  for lsteps in local_ni_steps: 
    networks.append( ('ParallelNet', {'channels'          : args.channels, 
                                      'local_steps'       : lsteps,
                                      'max_iters'         : args.lp_iters,
                                      'print_level'       : args.lp_print,
                                      'Tf'                : args.tf,
                                      'max_fwd_levels'    : args.lp_fwd_levels,
                                      'max_bwd_levels'    : args.lp_bwd_levels,
                                      'max_fwd_iters'     : args.lp_fwd_iters,
                                      'print_level'       : args.lp_print,
                                      'braid_print_level' : args.lp_braid_print,
                                      'fwd_cfactor'       : args.lp_fwd_cfactor,
                                      'bwd_cfactor'       : args.lp_bwd_cfactor,
                                      'fine_fwd_fcf'      : args.lp_fwd_finefcf,
                                      'fine_bwd_fcf'      : args.lp_bwd_finefcf,
                                      'fwd_nrelax'        : args.lp_fwd_nrelax_coarse,
                                      'bwd_nrelax'        : args.lp_bwd_nrelax_coarse,
                                      'skip_downcycle'    : not args.lp_use_downcycle,
                                      'fmg'               : args.lp_use_fmg,
                                      'fwd_relax_only_cg' : args.lp_fwd_relaxonlycg,
                                      'bwd_relax_only_cg' : args.lp_bwd_relaxonlycg,
                                      'CWt'               : args.lp_use_crelax_wt,
                                      'fwd_finalrelax'    : args.lp_fwd_finalrelax
                                      }))
                                 
  ##
  # Specify optimization routine on each level, starting from fine to coarse
  optims = [ ("pytorch_sgd", { 'lr':args.lr, 'momentum':0.9}) for i in range(len(ni_steps)) ]

  ##
  # Initialize MG/Opt solver with nested iteration 
  epochs = 2
  mgopt_printlevel = 1
  log_interval = args.log_interval
  mgopt = mgopt_solver()
  mgopt.initialize_with_nested_iteration(ni_steps, train_loader, test_loader,
          networks, epochs=epochs, log_interval=log_interval,
          mgopt_printlevel=mgopt_printlevel, optims=optims, seed=args.seed) 
   
  print(mgopt)
  mgopt.options_used()
  
  ##
  # Turn on for fixed-point test.  
  # Works when running  $$ python3 main_mgopt.py --samp-ratio 0.002 --lp-fwd-cfactor 2 --lp-bwd-cfactor 2 --mgopt-printlevel 3 --batch-size 1
  if False:
    import torch.nn as nn
    criterion = nn.CrossEntropyLoss()
    train_set = torch.utils.data.Subset(dataset, [1])
    train_loader = torch.utils.data.DataLoader(train_set,batch_size=1,shuffle=False)
    for (data,target) in train_loader:  pass
    model = mgopt.levels[0].model
    with torch.no_grad():
      model.eval()
      output = model(data)
      loss = model.compose(criterion, output, target)
    
    print("Doing fixed point test.  Loss on single training example should be zero: " + str(loss.item()))
    model.train()

  mgopt.levels[0].model.parallel_nn.setFwdNumRelax(0,level=0) # FCF-Relaxation on the fine grid for forward solve
  mgopt.levels[0].model.parallel_nn.setBwdNumRelax(0,level=0) # FCF-Relaxation on the fine grid for backward solve
  mgopt.levels[0].model.parallel_nn.setFwdFinalFCRelax()
  mgopt.levels[0].model.parallel_nn.setBwdRelaxOnlyCG(1)
  mgopt.levels[0].model.parallel_nn.setFwdRelaxOnlyCG(1)
  mgopt.levels[0].model.parallel_nn.setPrintLevel(2)
  
  ##
  # Run the MG/Opt solver
  #   Note: that we use the default restrict and interp options, but these can be modified on a per-level basis
  if( args.mgopt_iter > 0):
    epochs = args.epochs
    line_search = ('no_line_search', {'a' : 1.0})
    log_interval = args.log_interval
    mgopt_printlevel = args.mgopt_printlevel
    mgopt_iter = args.mgopt_iter
    mgopt_levels = args.mgopt_levels
    mgopt_tol=0
    nrelax_pre = args.mgopt_nrelax_pre
    nrelax_post = args.mgopt_nrelax_post
    nrelax_coarse = args.mgopt_nrelax_coarse
    mgopt.mgopt_solve(train_loader, test_loader, epochs=epochs,
            log_interval=log_interval, mgopt_tol=mgopt_tol,
            mgopt_iter=mgopt_iter, nrelax_pre=nrelax_pre,
            nrelax_post=nrelax_post, nrelax_coarse=nrelax_coarse,
            mgopt_printlevel=mgopt_printlevel, mgopt_levels=mgopt_levels,
            line_search=line_search)
   
    print(mgopt)
    mgopt.options_used()
  ##
  


if __name__ == '__main__':
  main()



