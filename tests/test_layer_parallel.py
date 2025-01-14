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

import torch
import torch.nn as nn
import torch.nn.functional as F
import unittest
import sys
import numpy as np
import statistics as stats

import torchbraid
import faulthandler

from torchbraid.utils import getDevice
from torchbraid.utils import LPBatchNorm2d

faulthandler.enable()

from mpi4py import MPI

class StateInitialGuess:
  def __init__(self, rank, x0):
    self.x0 = x0.clone()
    self.rank = rank
    self.mark = set()

  def getState(self, time):
    self.mark.add(time)
    return time*torch.ones(self.x0.shape).to(self.x0.device)

  def reduceMark(self, comm):
    my_rank = comm.Get_rank()
    num_proc = comm.Get_size()

    if my_rank == 0:
      marks = [self.mark]
      for i in range(1, num_proc):
        remote = comm.recv(source=i, tag=77)
        marks += [remote]
      return marks 
    else:
      comm.send(self.mark, dest=0, tag=77)
      return []
    

class LinearBlock(nn.Module):
  def __init__(self,dim=10):
    super(LinearBlock, self).__init__()

  def forward(self, x):
    return x
# end layer

class ExtraLinearBlock(nn.Module):
  def __init__(self,dim=10):
    super(ExtraLinearBlock, self).__init__()

  def forward(self, x, *args,**kwargs):
    assert len(args)==2
    assert args[0]=='horse'
    assert args[1]=='dog'

    assert len(kwargs)==3
    assert kwargs['a0']=='cat'
    assert kwargs['a1']=='monkey'
    assert kwargs['a2']=='donkey'
    return x
# end layer

class ReLUBlock(nn.Module):
  def __init__(self,dim=10,with_bn=False):
    super(ReLUBlock, self).__init__()
    self.lin = nn.Linear(dim, dim,bias=True)
    self.with_bn = with_bn

    w = 2.3*torch.ones(dim,dim)
    self.lin.weight = torch.nn.Parameter(w)

    b = -1.22*torch.ones(dim)
    self.lin.bias = torch.nn.Parameter(b)

    if with_bn:
      #self.bn = nn.BatchNorm1d(dim)
      self.bn = LPBatchNorm2d(dim)

  def forward(self, x):
    if self.with_bn:
      x = self.bn(x)
    return F.relu(self.lin(x))
# end layer

class ConvBlock(nn.Module):
  def __init__(self,dim,num_ch,with_bn=False):
    super(ConvBlock, self).__init__()
    self.lin = nn.Conv1d(num_ch,num_ch,kernel_size=3,padding=1,bias=False)

    # this is basically setup to be a laplacian
    self.lin.weight[...,0] = -1.0
    self.lin.weight[...,1] =  2.0
    self.lin.weight[...,2] = -1.0

  def forward(self, x):
    #return F.relu(self.lin(x))
    return self.lin(x)
# end layer

class TestTorchBraid(unittest.TestCase):

  def test_extra_linearNet_Exact(self):
    dim = 2
    basic_block = lambda: ExtraLinearBlock(dim)

    # figure out the whole GPU situation
    my_device,my_host = getDevice(MPI.COMM_WORLD) 

    x0 = torch.randn(5,dim) # forward initial cond

    x0 = x0.to(my_device)

    m = torchbraid.LayerParallel(MPI.COMM_WORLD,basic_block,3*MPI.COMM_WORLD.Get_size(),2.0,max_fwd_levels=1,max_bwd_levels=1,max_iters=1)
    m.setPrintLevel(0)
    m = m.to(my_device)

    MPI.COMM_WORLD.barrier()

    m(x0,'horse','dog',a0='cat',a1='monkey',a2='donkey')
  # end test_linearNet_Exact

  def test_linearNet_Exact(self):
    dim = 2
    basic_block = lambda: LinearBlock(dim)

    x0 = torch.randn(5,dim) # forward initial cond
    w0 = torch.randn(5,dim) # adjoint initial cond
    max_levels = 1
    max_iters = 1
    self.backForwardProp(dim,basic_block,x0,w0,max_levels,max_iters,test_tol=1e-16,prefix='linearNet_Exact')

    MPI.COMM_WORLD.barrier()
  # end test_linearNet_Exact

  def test_linearNet_Approx(self):
    dim = 2
    basic_block = lambda: LinearBlock(dim)

    x0 = torch.randn(5,dim) # forward initial cond
    w0 = torch.randn(5,dim) # adjoint initial cond
    max_levels = 3
    max_iters = 8
    self.backForwardProp(dim,basic_block,x0,w0,max_levels,max_iters,test_tol=1e-6,prefix='linearNet_Approx')

    MPI.COMM_WORLD.barrier()
  # end test_linearNet_Approx

  def test_reLUNet_Exact(self):
    dim = 2
    basic_block = lambda: ReLUBlock(dim)

    x0 = 12.0*torch.ones(5,dim) # forward initial cond
    w0 = 3.0*torch.ones(5,dim) # adjoint initial cond
    max_levels = 1
    max_iters = 1

    # this catch block, augments the 
    rank = MPI.COMM_WORLD.Get_rank()
    try:
      self.backForwardProp(dim,basic_block,x0,w0,max_levels,max_iters,test_tol=1e-16,prefix='reLUNet_Exact')
    except RuntimeError as err:
      raise RuntimeError("proc=%d) reLUNet_Exact..failure" % rank) from err

    MPI.COMM_WORLD.barrier()
  # end test_reLUNet_Exact

  def test_reLUNetBN_Exact(self):
    dim = 2
    basic_block = lambda: ReLUBlock(dim,True)

    torch.manual_seed(434442321)
    x0 = 1.0*torch.rand(5,dim) # forward initial cond
    w0 = 3.0*torch.ones(5,dim) # adjoint initial cond
    max_levels = 1
    max_iters = 1

    # this catch block, augments the 
    rank = MPI.COMM_WORLD.Get_rank()
    try:
      self.backForwardProp(dim,basic_block,x0,w0,max_levels,max_iters,test_tol=1e-16,prefix='reLUNetBN_Exact')
    except RuntimeError as err:
      raise RuntimeError("proc=%d) reLUNetBN_Exact..failure" % rank) from err

    MPI.COMM_WORLD.barrier()
  # end test_reLUNet_Exact

  def test_reLUNetBN_Approx(self):
    dim = 2
    basic_block = lambda: ReLUBlock(dim,True)

    torch.manual_seed(434442321)
    x0 = 1.0*torch.rand(5,dim) # forward initial cond
    w0 = 3.0*torch.ones(5,dim) # adjoint initial cond
    max_levels = 3
    max_iters = 8

    # this catch block, augments the 
    rank = MPI.COMM_WORLD.Get_rank()
    try:
      m_parallel,m_serial = self.backForwardProp(dim,basic_block,x0,w0,max_levels,max_iters,test_tol=1e-16,prefix='reLUNetBN_Approx')
    except RuntimeError as err:
      raise RuntimeError("proc=%d) reLUNetBN_Approx..failure" % rank) from err
 
    # evaluate more times to make sure the batchnorm is correct
    ########################################################

    # figure out the whole GPU situation
    my_device,my_host = getDevice(MPI.COMM_WORLD) 

    x0 = 1.0*torch.rand(5,dim,device=my_device) # forward initial cond
    w0 = 1.0*torch.rand(5,dim,device=my_device) # forward initial cond

    m_parallel.eval() # evaluation should result in no buffer changes
    y = m_parallel(x0)

    m_parallel.train()
    y = m_parallel(x0)
    y.backward(w0)

    if m_serial!=None:
      m_serial.train()
      m_serial(x0)

    # test the buffers
    parallel_buffers = self.copyBuffersToRoot(m_parallel,my_device)
    if rank==0:
      serial_buffers = list(m_serial.buffers())

      for s,p in zip(serial_buffers,parallel_buffers):
        if s.dtype==torch.bool: 
          continue
       
        self.assertTrue(torch.norm(s-p).item()/torch.norm(s).item() < 1.e-15)

  def test_convNet_Approx_coarse_ref(self):
    dim = 128
    num_ch = 1
    num_samp = 1
    basic_block = lambda: ConvBlock(dim,num_ch)

    u = torch.linspace(0.0,1.0,dim)
    x0 = torch.zeros(num_samp,num_ch,dim) # forward initial cond
    w0 = torch.zeros(num_samp,num_ch,dim) # adjoint initial cond
    for ch in range(num_ch):
      for samp in range(num_samp):
        x0[samp,ch,:] = torch.sin(2.0*np.pi*0.5*(ch+1.0)*(u-1.0/(samp+1.0)))
        w0[samp,ch,:] = torch.cos(2.0*np.pi*0.5*(ch+1.0)*(u-1.0/(samp+1.0))) 
    # build a relatively smooth initial guess

    max_levels = 2
    max_iters = 12

    def coarsen(x,level):
      return 0.5*(x[...,0::2]+x[...,1::2]).clone()
      # return x.clone()

    def refine(x,level):
      # this little bit of torch magic simply does injection (I'm not sure I can explain it)
      # I looked up "interleave" and pytorch and eventually came to this
      shape = list(x.shape)
      shape[-1] *= 2
      return torch.stack((x,x),dim=-1).view(shape).contiguous()
      # return x.clone()

    c = coarsen(x0,0)
    xi = refine(c,0)
    xc = coarsen(xi,0)
    self.assertTrue(torch.norm(xc-c)<1.0e-15) # sanity check

    # this catch block, augments the 
    rank = MPI.COMM_WORLD.Get_rank()
    try:
      #self.backForwardProp(dim,basic_block,x0,w0,max_levels,max_iters,test_tol=1e-6,prefix='reLUNet_Approx_coarse_ref',ref_pair=(coarsen,refine),check_grad=False,num_steps=12,print_level=3)
      pass
    except RuntimeError as err:
      raise RuntimeError("proc=%d) reLUNet_Exact..failure" % rank) from err

    MPI.COMM_WORLD.barrier()
  # end test_reLUNet_Exact

  def test_reLUNet_Approx(self):
    dim = 2
    basic_block = lambda: ReLUBlock(dim)

    x0 = 12.0*torch.ones(5,dim) # forward initial cond
    w0 = 3.0*torch.ones(5,dim) # adjoint initial cond
    max_levels = 3
    max_iters = 8
    # this catch block, augments the 
    rank = MPI.COMM_WORLD.Get_rank()
    try:
      self.backForwardProp(dim,basic_block,x0,w0,max_levels,max_iters,test_tol=1e-6,prefix='reLUNet_Approx')
    except RuntimeError as err:
      raise RuntimeError("proc=%d) reLUNet_Approx..failure" % rank) from err

    MPI.COMM_WORLD.barrier()
  # end test_reLUNet_Approx

  def test_reLUNet_Approx_InitialGuess(self):
    dim = 2
    basic_block = lambda: ReLUBlock(dim)

    x0 = 12.0*torch.ones(5, dim)
    w0 = 3.0*torch.ones(5, dim)
    max_levels = 3
    max_iters = 8
    rank = MPI.COMM_WORLD.Get_rank()
    try:
      self.backForwardProp(dim, basic_block, x0, w0, max_levels, max_iters, test_tol=1e-6, prefix='reLUNet_Approx', check_initial_guess=True, check_grad=False, num_steps=128)
    except RuntimeError as err:
      raise RuntimeError("proc=%d) reLUNet_Approx..failure" % rank) from err

    MPI.COMM_WORLD.barrier()


  def test_variableCFactor(self):
    basic_block = lambda: ReLUBlock(2)
    cfactor = {0: 4, 1: 3, 2: 2}

    # figure out the whole GPU situation
    my_device,my_host = getDevice(MPI.COMM_WORLD) 

    # this is the torchbraid class being tested 
    #######################################
    m = torchbraid.LayerParallel(MPI.COMM_WORLD,basic_block,144,Tf=2.0,max_fwd_levels=3,max_bwd_levels=3)
    m = m.to(my_device)
    m.setSkipDowncycle(False)
    m.setCFactor(cfactor)

    # test the getFineTimeIndex function (interrogates the app)
    #######################################

    fine_tidx = m.fwd_app.getFineTimeIndex(tidx=23,level=0)
    self.assertEqual(fine_tidx,23)

    fine_tidx = m.fwd_app.getFineTimeIndex(tidx=28,level=0)
    self.assertEqual(fine_tidx,28)
    
    fine_tidx = m.fwd_app.getFineTimeIndex(tidx=23,level=3)
    self.assertEqual(fine_tidx,23*cfactor[0]*cfactor[1]*cfactor[2])

    fine_tidx = m.fwd_app.getFineTimeIndex(tidx=23,level=1)
    self.assertEqual(fine_tidx,23*cfactor[0])

  def copyBuffersToRoot(self,m,device):
    comm     = m.getMPIComm()
    my_rank  = m.getMPIComm().Get_rank()
    num_proc = m.getMPIComm().Get_size()
 
    bn_mods = [l for l in m.modules() if isinstance(l,nn.BatchNorm1d) or isinstance(l,LPBatchNorm2d)]
    params = []
    for l in bn_mods:
      params.extend(list(l.buffers()))

    if len(params)==0:
      return params

    if my_rank==0:
      for i in range(1,num_proc):
        remote_p = comm.recv(source=i,tag=77)
        remote_p = [p.to(device) for p in remote_p]
        params.extend(remote_p)

      return params
    else:
      params_cpu = [p.cpu() for p in params]
      comm.send(params_cpu,dest=0,tag=77)
      return None
  # end copyParametersToRoot

  def copyParameterGradToRoot(self,m,device):
    comm     = m.getMPIComm()
    my_rank  = m.getMPIComm().Get_rank()
    num_proc = m.getMPIComm().Get_size()
 
    params = [p.grad for p in list(m.parameters())]

    if len(params)==0:
      return params

    if my_rank==0:
      for i in range(1,num_proc):
        remote_p = comm.recv(source=i,tag=77)
        remote_p = [p.to(device) for p in remote_p]
        params.extend(remote_p)

      return params
    else:
      params_cpu = [p.cpu() for p in params]
      comm.send(params_cpu,dest=0,tag=77)
      return None
  # end copyParametersToRoot

  def backForwardProp(self,dim, basic_block,x0,w0,max_levels,max_iters,test_tol,prefix,
                      ref_pair=None,check_grad=True,num_steps=4,print_level=0,check_initial_guess=False,extra_args=list(),extra_kwargs=dict()):
    Tf = 2.0
    cfactor = 2 

    # figure out the whole GPU situation
    my_device,my_host = getDevice(MPI.COMM_WORLD) 

    x0 = x0.to(my_device)
    w0 = w0.to(my_device)

    # this is the torchbraid class being tested 
    #######################################
    m = torchbraid.LayerParallel(MPI.COMM_WORLD,basic_block,num_steps*MPI.COMM_WORLD.Get_size(),Tf,max_fwd_levels=max_levels,max_bwd_levels=max_levels,max_iters=max_iters,spatial_ref_pair=ref_pair)
    m = m.to(my_device)
    m.setPrintLevel(print_level)
    m.setSkipDowncycle(False)
    m.setCFactor(cfactor)

    w0 = m.copyVectorFromRoot(w0)

    initial_guess = None
    if check_initial_guess:
      initial_guess = StateInitialGuess(m.getMPIComm().Get_rank(), x0)
    m.setFwdInitialGuess(initial_guess)

    # test the getFineTimeIndex function (interrogates the app)
    #######################################

    fine_tidx = m.fwd_app.getFineTimeIndex(tidx=23,level=0)
    self.assertEqual(fine_tidx,23)

    fine_tidx = m.fwd_app.getFineTimeIndex(tidx=28,level=0)
    self.assertEqual(fine_tidx,28)
    
    fine_tidx = m.fwd_app.getFineTimeIndex(tidx=28,level=3)
    self.assertEqual(fine_tidx,28*cfactor**3) 

    fine_tidx = m.fwd_app.getFineTimeIndex(tidx=23,level=3)
    self.assertEqual(fine_tidx,23*cfactor**3) 

    # this is the reference torch "solution"
    #######################################
    dt = Tf/num_steps
    f = m.buildSequentialOnRoot()
    if f is not None: # handle the cuda case
      f = f.to(my_device)

    # run forward/backward propgation

    # propogation with torchbraid
    #######################################
    xm = x0.clone()
    xm.requires_grad = check_grad

    m.train()
    wm = m(xm,*extra_args,**extra_kwargs)

    times,uvals = m.getFineTimePoints()

    # check that the number of points is correct...no other checks :(
    self.assertEqual(len(times),len(uvals),f'Processor={m.getMPIComm().Get_rank()}')

    if check_grad:
      wm.backward(w0)
      m_param_grad = self.copyParameterGradToRoot(m,my_device)

    wm = m.getFinalOnRoot(wm)

    # print time results
    timer_str = m.getTimersString() 

    # check the initial guess
    if initial_guess is not None:
      marks = initial_guess.reduceMark(m.getMPIComm())

    # check some values
    if m.getMPIComm().Get_rank()==0:

      if initial_guess is not None:
        mark = marks[0]
        for remote_mark in marks[1:]:
          mark.update(remote_mark)
        self.assertEqual(len(mark), int(m.getMPIComm().Get_size()*num_steps/cfactor))

      # this is too much to print out every test run, but I'd like to make sure the
      # code is execueted
      self.assertTrue(len(timer_str)>0)
 
      # propogation with torch
      #######################################
      xf = x0.clone()
      xf.requires_grad = check_grad
      
      f.train()
      wf = f(xf)
 
      # compare the solutions
      #######################################

      self.assertTrue(torch.norm(wm)>0.0)
      self.assertTrue(torch.norm(wf)>0.0)

      print('\n')
      print('%s: fwd error = %.6e' % (prefix,torch.norm(wm-wf)/torch.norm(wf)))

      self.assertTrue(torch.norm(wm-wf)/torch.norm(wf)<=test_tol)

      if check_grad:
        wf.backward(w0)
        print('%s: grad error = %.6e' % (prefix,torch.norm(xm.grad-xf.grad)/torch.norm(xf.grad)))
        self.assertTrue((torch.norm(xm.grad-xf.grad)/torch.norm(xf.grad))<=test_tol)
  
        param_errors = []
        for pf,pm_grad in zip(list(f.parameters()),m_param_grad):
          self.assertTrue(not pm_grad is None)

          # accumulate parameter errors for testing purposes
          param_errors += [(torch.norm(pf.grad-pm_grad)/torch.norm(pf.grad)).item()]

          # check the error conditions
          self.assertTrue(torch.norm(pf.grad-pm_grad)<=test_tol)
   
        if len(param_errors)>0:
          print('%s: p grad error (mean,stddev) = %.6e, %.6e' % (prefix,stats.mean(param_errors),stats.stdev(param_errors)))

      print('\n')
    elif initial_guess is not None:
      self.assertEqual(len(marks), 0)

    return m,f
  # forwardPropSerial

  import sys

def trace(frame, event, arg):
    print("%s, %s:%d" % (event, frame.f_code.co_filename, frame.f_lineno))
    return trace

#sys.settrace(trace)

if __name__ == '__main__':
  unittest.main()
