#!/usr/bin/env python2.6
import base64
import cPickle as pickle
import json
import math
import os
import paramiko
import threading

from remote_worker import RemoteWorker
from remote_task_thread import RemoteTaskThread

from qjam.msg.task_msg import TaskMsg
from qjam.common.reducing import default_reduce

class Master(object):
  def __init__(self, remote_workers):
    if not isinstance(remote_workers, list):
      raise TypeError, 'remote_workers parameter must be of type list'

    if len(remote_workers) == 0:
      raise ValueError, 'list of workers cannot be empty'

    for worker in remote_workers:
      if not isinstance(worker, RemoteWorker):
        exc_msg = '''elements in the parameter list, remote_workers,
                     must be of type RemoteWorker'''
        raise TypeErrer, exc_msg

    self.__workers = remote_workers

  def run(self, module, params=None, dataset=None):
    self.__thread_pool = []

    len_workers = len(self.__workers)

    if dataset:
      dataset.slice_size_is(1)
      if len(dataset) > len_workers:
        slice_size = int(math.ceil(float(len(dataset)) / len_workers))
        dataset.slice_size_is(slice_size)

    for i,worker in enumerate(self.__workers):
      if dataset:
        if i >= len(dataset):
          break
        worker_slice = dataset.slice(i)
        # TODO: resize make slice_size the desired chunk size
        task_msg = TaskMsg(module, params, worker_slice)
      else:
        task_msg = TaskMsg(module, params, None)

      thread = RemoteTaskThread(worker, task_msg)
      self.__thread_pool.append(thread)
      thread.start()

    for thread in self.__thread_pool:
      thread.join()

    results = []
    for thread in self.__thread_pool:
      results.append(thread.result())

    try:
      reducefn = module.reduce
    except AttributeError:
      reducefn = default_reduce

    return reduce(reducefn, results)
