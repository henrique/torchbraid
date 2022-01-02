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
#
# ----- Example Script -----

# export FWD_ITER=3
# export BWD_ITER=2
# export DIFF=0.0001
# export ACT=relu
# 
# mpirun -n 4 python ./main_lp.py --steps 32 --lp-fwd-cfactor 4 --lp-bwd-cfactor 4 --epochs=8 --seed 2069923971 --lp-fwd-iters ${FWD_ITER} --lp-fwd-levels -1 --lp-bwd-levels -1 --lp-iters ${BWD_ITER} --batch-size 100 --tf 5.0 --log-interval 5 --diff-scale ${DIFF} --activation ${ACT} --samp-ratio 0.1 --channels 8
#
# ----- Output -----
# Using Tiny ImageNet...
# 
# Namespace(seed=2069923971, log_interval=5, steps=32, channels=8, tf=5.0, diff_scale=0.0001, activation='relu', batch_size=100, epochs=8, samp_ratio=0.1, lr=0.01, lp_fwd_levels=2, lp_bwd_levels=2, lp_iters=2, lp_fwd_iters=2, lp_print=0, lp_braid_print=0, lp_fwd_cfactor=4, lp_bwd_cfactor=4, lp_fwd_nrelax_coarse=1, lp_bwd_nrelax_coarse=1, lp_fwd_finefcf=False, lp_bwd_finefcf=False, lp_fwd_finalrelax=False, lp_use_downcycle=False, lp_use_fmg=False, lp_bwd_relaxonlycg=0, lp_fwd_relaxonlycg=0, lp_use_crelax_wt=1.0)
# 
# Training setup:  Batch size:  100  Sample ratio:  0.1  Epochs:  8
# Train Epoch:  1 [   100/  8800]	Loss: 5.374e+00	Time Per Batch 1.002954/1.048842 - F 2/6.47e+03, B 2/2.76e-05
# Train Epoch:  1 [   600/  8800]	Loss: 3.100e+00	Time Per Batch 0.984198/1.075165 - F 2/1.43e+03, B 2/1.18e-05
# Train Epoch:  1 [  1100/  8800]	Loss: 2.920e+00	Time Per Batch 0.995636/1.064048 - F 2/1.25e+03, B 2/8.23e-06
# Train Epoch:  1 [  1600/  8800]	Loss: 3.079e+00	Time Per Batch 0.997011/1.057520 - F 2/1.35e+03, B 2/1.17e-05




from __future__ import print_function
import numpy as np

import sys

import torch
import torch.nn as nn
import torch.optim as optim
import statistics               as stats

from torchvision import datasets, transforms
from mpi4py import MPI
from utils import parse_args, ParallelNet
from timeit import default_timer as timer

from torchbraid.utils import MeanInitialGuessStorage

def root_print(rank,s):
  if rank==0:
    print(s)

def train(rank,args,model,train_loader,optimizer,epoch,compose,mig_storage):
  log_interval = args.log_interval
  torch.enable_grad()

  model.train()
  criterion = nn.CrossEntropyLoss()
  total_time = 0.0
  total_time_fp = 0.0
  total_time_bp = 0.0
  total_time_cm = 0.0

  switched = False
  format_str = 'Train Epoch: {:2d} [{:6d}/{:6d}]\tLoss: {:.3e}\tTime Per Batch {:.6f}/{:.6f} - F{:2d}/{:.2e}, B{:2d}/{:.2e}'
  total_data = 0

  default_fwd_iters = model.parallel_nn.getFwdMaxIters();
  default_bwd_iters = model.parallel_nn.getBwdMaxIters();

  cumulative_start_time = timer()
  for batch_idx,(data,target) in enumerate(train_loader):

    #root_print(rank,f'EPOCH={epoch} FORWARD')
    start_time = timer()

    #if epoch>1:
    #  model.parallel_nn.setFwdInitialGuess(mig_storage.initialGuess(target))

    # compute forward
    optimizer.zero_grad()
    start_time_fp = timer()
    output = model(data)
    total_time_fp += timer()-start_time_fp

    fwd_itr, fwd_res = model.getFwdStats()

    # incorporate the average
    times,states = model.parallel_nn.getFineTimePoints()
    for t,state in zip(times,states):
      mig_storage.addState(t,state.tensors(),target)

    # compute loss
    start_time_cm = timer()
    if len(output.shape)==1:
      output = torch.unsqueeze(output,0)
    loss = compose(criterion,output,target)
    total_time_cm += timer()-start_time_cm

    # compute gradient
    #root_print(rank,f'EPOCH={epoch} BACKWARD')
    start_time_bp = timer()
    loss.backward()
    total_time_bp += timer()-start_time_bp

    bwd_itr, bwd_res = model.getBwdStats()

    # take step
    stop_time = timer()
    optimizer.step()

    total_data    += len(data)
    total_time    += stop_time-start_time

    cumulative_stop_time = timer()
    cumulative_time = (cumulative_stop_time-cumulative_start_time) 

    if fwd_res>1e1:
      model.parallel_nn.setFwdMaxIters(model.parallel_nn.getFwdMaxIters()+1)
      root_print(rank,f'  updated fwd iters = {model.parallel_nn.getFwdMaxIters()}')
    if bwd_res>1e0:
      model.parallel_nn.setBwdMaxIters(model.parallel_nn.getBwdMaxIters()+1)
      root_print(rank,f'  updated bwd iters = {model.parallel_nn.getBwdMaxIters()}')
      

    if batch_idx % log_interval == 0:
        root_print(rank,format_str.format(
                        epoch, 
                        total_data,
                        len(train_loader.dataset), 
                        loss.item(),
                        total_time/(batch_idx+1.0),
                        cumulative_time/(batch_idx+1.0),
                        fwd_itr,fwd_res,
                        bwd_itr,bwd_res
                        ))

  model.parallel_nn.setFwdMaxIters(default_fwd_iters)
  model.parallel_nn.setBwdMaxIters(default_bwd_iters)

  root_print(rank,(format_str+', fp={:.6f}, cm={:.6f}, bp={:.6f}').format(
                  epoch, 
                  len(train_loader.dataset),
                  len(train_loader.dataset), 
                  loss.item(),
                  total_time/(batch_idx+1.0),
                  cumulative_time/(batch_idx+1.0),
                  fwd_itr,fwd_res,
                  bwd_itr,bwd_res,
                  total_time_fp/len(train_loader.dataset),
                  total_time_cm/len(train_loader.dataset),
                  total_time_bp/len(train_loader.dataset),
                  ))

def test(rank,model,test_loader,epoch,compose,prefix=''):
  model.eval()
  correct = 0
  criterion = nn.CrossEntropyLoss()
  total_time = 0.0
  root_print(rank,f'EPOCH={epoch} TEST')

  default_fwd_iters = model.parallel_nn.getFwdMaxIters();
  model.parallel_nn.setFwdMaxIters(10)

  with torch.no_grad():
    for data,target in test_loader:
      start_time = timer()


      # evaluate inference
      output = model(data)

      if len(output.shape)==1:
        output = torch.unsqueeze(output,0)

      # compute the number of solutions
      pred = compose(output.argmax, dim=1, keepdim=True)
      stop_time = timer()

      total_time += stop_time-start_time

      # only accumulate the correct values on the root
      if rank==0:
        correct += pred.eq(target.view_as(pred)).sum().item()

  model.parallel_nn.setFwdMaxIters(default_fwd_iters)

  root_print(rank,'{}Test set epoch {:2d}: Accuracy: {}/{} ({:.0f}%)\tTime Per Batch {:.6f}'.format(
      prefix,
      epoch,
      correct, len(test_loader.dataset),
      100. * correct / len(test_loader.dataset),
      total_time/len(test_loader.dataset)))


  return 100. * correct / len(test_loader.dataset)

def main():
  
  ##
  # Parse command line args (function defined above)
  args = parse_args(mgopt_on=False)
  procs = MPI.COMM_WORLD.Get_size()
  rank  = MPI.COMM_WORLD.Get_rank()

  local_steps = int(args.steps/procs)

  ##
  # Load training and testing data, while reducing the number of samples (if desired) for faster execution
  transform = transforms.Compose([transforms.ToTensor(),
                                  transforms.Normalize((0.1307,), (0.3081,))
                                 ])
  ##
  # Load Tiny ImageNet
  if rank==0:
    print('Using Tiny ImageNet...\n')
    print(args)
  ##


  # Load datasets
  traindir = './tiny-imagenet-200/new_train'
  valdir = './tiny-imagenet-200/new_test'
  normalize = transforms.Normalize(mean=[0.4914, 0.4822, 0.4465],
                                   std=[0.2023, 0.1994, 0.2010])
  train_dataset = datasets.ImageFolder(traindir,
      transforms.Compose([
          # transforms.RandomResizedCrop(56),
          # transforms.RandomHorizontalFlip(),
          # transforms.Resize(64),
          transforms.RandomCrop(64, padding=4),
          transforms.RandomHorizontalFlip(),
          transforms.ToTensor(),
          normalize, transforms.RandomErasing(0.25) ]))
  test_dataset = datasets.ImageFolder(valdir, transforms.Compose([
                                      transforms.Resize(64),
                                      transforms.ToTensor(),
                                      normalize ])) 

  # Trim datasets 
  train_size = int(88000*args.samp_ratio)
  test_size = int(22000*args.samp_ratio)
  #
  train_dataset = torch.utils.data.Subset(train_dataset, range(train_size))
  test_dataset  = torch.utils.data.Subset(test_dataset, range(test_size))

  # Create data loaders
  train_loader = torch.utils.data.DataLoader(train_dataset,
          batch_size=args.batch_size, shuffle=True,
          pin_memory=True)
  test_loader = torch.utils.data.DataLoader(test_dataset,
          batch_size=args.batch_size, shuffle=False,
          pin_memory=True)
  if rank==0:
    print("\nTraining setup:  Batch size:  " + str(args.batch_size) + "  Sample ratio:  " + str(args.samp_ratio) + "  Epochs:  " + str(args.epochs) )

  ##
  # Define ParNet parameters for each nested iteration level, starting from fine to coarse
  network = {                 'channels'          : args.channels, 
                              'local_steps'       : local_steps,
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
                              'fwd_finalrelax'    : args.lp_fwd_finalrelax,
                              'diff_scale'        : args.diff_scale,
                              'activation'        : args.activation
                      }

  ##
  # Initialize MG/Opt solver with nested iteration 
  epochs = args.epochs
  log_interval = args.log_interval

  model = ParallelNet(**network)

  optimizer = optim.Adam(model.parameters(), lr=args.lr)
  compose = model.compose

  epoch_times = []
  test_times = []

  mig_storage = MeanInitialGuessStorage(class_count=200,average_weight=0.1)

  for epoch in range(1, args.epochs + 1):
    start_time = timer()
    train(rank,args, model, train_loader, optimizer, epoch,compose,mig_storage)
    end_time = timer()
    epoch_times += [end_time-start_time]

    start_time = timer()
    test(rank,model, test_loader,epoch,compose)
    end_time = timer()
    test_times += [end_time-start_time]  

  root_print(rank,'TIME PER EPOCH: %.2e (1 std dev %.2e)' % (stats.mean(epoch_times),stats.stdev(epoch_times)))
  root_print(rank,'TIME PER TEST:  %.2e (1 std dev %.2e)' % (stats.mean(test_times), stats.stdev(test_times)))
  
if __name__ == '__main__':
  main()
