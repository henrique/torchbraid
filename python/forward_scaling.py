import torch
import torch.nn as nn
import torch.nn.functional as F

import torchbraid
import time

import getopt,sys
import argparse

from mpi4py import MPI

# only print on rank==0
def root_print(rank,s):
  if rank==0:
    print(s)

class BasicBlock(nn.Module):
  def __init__(self,channels):
    super(BasicBlock, self).__init__()
    ker_width = 3
    self.conv1 = nn.Conv2d(channels,channels,ker_width,padding=1)
    self.conv2 = nn.Conv2d(channels,channels,ker_width,padding=1)

  def __del__(self):
    pass

  def forward(self, x):
    return F.relu(self.conv2(F.relu(self.conv1(x))))
# end layer

class ODEBlock(nn.Module):
  def __init__(self,layer,dt):
    super(ODEBlock, self).__init__()

    self.dt = dt
    self.layer = layer

  def forward(self, x):
    return x + self.dt*self.layer(x)

def build_block_with_dim(channels):
  b = BasicBlock(channels)
  return b

# some default input arguments
###########################################

comm = MPI.COMM_WORLD
my_rank   = comm.Get_rank()
last_rank = comm.Get_size()-1

# some default input arguments
###########################################
max_levels      = 3
max_iters       = 1
local_num_steps = 5
num_steps       = int(local_num_steps*comm.Get_size())
channels        = 16
images          = 10
image_size      = 256
Tf              = 2.0
run_serial      = False
print_level     = 0
nrelax          = 1
cfactor         = 2

# parse the input arguments
###########################################

parser = argparse.ArgumentParser()
parser.add_argument("steps",type=int,help="total numbere of steps, must be product of proc count (p=%d)" % comm.Get_size())
parser.add_argument("--levels",    type=int,  default=max_levels,   help="maximum number of Layer-Parallel levels")
parser.add_argument("--iters",     type=int,   default=max_iters,   help="maximum number of Layer-Parallel iterations")
parser.add_argument("--channels",  type=int,   default=channels,    help="number of convolutional channels")
parser.add_argument("--images",    type=int,   default=images,      help="number of images")
parser.add_argument("--pxwidth",   type=int,   default=image_size,  help="Width/height of images in pixels")
parser.add_argument("--verbosity", type=int,   default=print_level, help="The verbosity level, 0 - little, 3 - lots")
parser.add_argument("--cfactor",   type=int,   default=cfactor,     help="The coarsening factor")
parser.add_argument("--nrelax",    type=int,   default=nrelax,      help="The number of relaxation sweeps")
parser.add_argument("--tf",        type=float, default=Tf,          help="final time for ODE")
parser.add_argument("--serial",  default=run_serial, action="store_true", help="Run the serial version (1 processor only)")
args = parser.parse_args()

# the number of steps is not valid, then return
if not args.steps % comm.Get_size()==0:
  if my_rank==0:
    print('error in <steps> argument, must be a multiple of proc count: %d' % comm.Get_size())
    parser.print_help()
  sys.exit(0)
# end if not args.steps

if args.serial==True and comm.Get_size()!=1:
  if my_rank==0:
    print('The <--serial> optional argument, can only be run in serial (proc count: %d)' % comm.Get_size())
    parser.print_help()
  sys.exit(0)
# end if not args.steps
   
# determine the number of steps
num_steps       = args.steps
local_num_steps = int(num_steps/comm.Get_size())

if args.levels:    max_levels  = args.levels
if args.iters:     max_iters   = args.iters
if args.channels:  channels    = args.channels
if args.images:    images      = args.images
if args.pxwidth:   image_size  = args.pxwidth
if args.verbosity: print_level = args.verbosity
if args.cfactor:   cfactor     = args.cfactor
if args.nrelax :   nrelax      = args.nrelax
if args.tf:        Tf          = args.tf
if args.serial:    run_serial  = args.serial

# build the neural network
###########################################

# define the neural network parameters
basic_block = lambda: build_block_with_dim(channels)

# build parallel information
dt        = Tf/num_steps

# do forward propagation (in parallel)
x = torch.randn(images,channels,image_size,image_size) 

root_print(my_rank,'Number of steps: %d' % num_steps)
if run_serial:
  root_print(my_rank,'Running PyTorch: %d' % comm.Get_size())
  layers = [basic_block() for i in range(num_steps)]
  serial_nn = torch.nn.Sequential(*layers)
  t0 = time.time()
  y_serial = serial_nn(x)
  tf = time.time()
else:
  root_print(my_rank,'Running TorchBraid: %d' % comm.Get_size())
  # build the parallel neural network
  parallel_nn   = torchbraid.Model(comm,basic_block,local_num_steps,Tf,max_levels=max_levels,max_iters=max_iters)
  parallel_nn.setPrintLevel(print_level)
  parallel_nn.setCFactor(cfactor)
  parallel_nn.setNumRelax(nrelax)

  t0 = time.time()
  y_parallel = parallel_nn(x)
  comm.barrier()
  tf = time.time()

  comm.barrier()
# end if not run_serial

root_print(my_rank,'Run  Time: %.6e' % (tf-t0))