# --------------------------------------------------------
# THOR
# Licensed under The MIT License
# Written by Axel Sauer (axel.sauer@tum.de)
# --------------------------------------------------------

from os.path import dirname, abspath
import torch
from thor.trackers.THOR_modules.wrapper import THOR_SiamFC, THOR_SiamRPN, THOR_SiamMask

from pathlib import Path

# SiamFC import
from thor.trackers.SiamFC.net import SiamFC
from thor.trackers.SiamFC.siamfc import SiamFC_init, SiamFC_track

# SiamRPN Imports
from thor.trackers.SiamRPN.net import SiamRPN
from thor.trackers.SiamRPN.siamrpn import SiamRPN_init, SiamRPN_track

# SiamMask Imports
from thor.trackers.SiamMask.net import SiamMaskCustom
from thor.trackers.SiamMask.siammask import SiamMask_init, SiamMask_track
from thor.trackers.SiamMask.utils.load_helper import load_pretrain
import numpy as np

from torch.utils.tensorboard import SummaryWriter

class Tracker():
    def __init__(self):
        use_cuda = torch.cuda.is_available()
        self.device = torch.device("cuda" if use_cuda else "cpu")
        self.mask = False
        self.temp_mem = None

    def init_func(self, im, pos, sz):
        raise NotImplementedError

    def track_func(self, state, im):
        raise NotImplementedError

    def setup(self, im, target_pos, target_sz):
        state = self.init_func(im, target_pos, target_sz)
        self.temp_mem.setup(im, target_pos, target_sz)
        return state

    def track(self, im, state, i):
        state = self.track_func(state, im)
        self.temp_mem.update(im, state['crop'], state['target_pos'], state['target_sz'], i)
        return state

    def track_no_update(self, im, state,i=0, lt=False):
        state = self.track_func(state, im,i=i,lt=lt)
        return state
    
    def update_mem(self, im, state, i):
        return self.temp_mem.update(im, state['crop'], state['target_pos'], state['target_sz'], i)


class SiamFC_Tracker(Tracker):
    def __init__(self, cfg):
        super(SiamFC_Tracker, self).__init__()
        self.cfg = cfg

        # setting up the tracker
        model_path = dirname(abspath(__file__)) + '/SiamFC/model.pth'
        model = SiamFC()
        model.load_state_dict(torch.load(model_path))
        self.model = model.eval().to(self.device)

        # set up template memory
        self.temp_mem = THOR_SiamFC(cfg=cfg['THOR'], net=self.model)

    def init_func(self, im, pos, sz):
        return SiamFC_init(im, pos, sz, self.cfg['tracker'])

    def track_func(self, state, im):
        return SiamFC_track(state, im, self.temp_mem)

class SiamRPN_Tracker(Tracker):
    def __init__(self, cfg):
        super(SiamRPN_Tracker, self).__init__()
        self.cfg = cfg

        # setting up the model
        model_path = dirname(abspath(__file__)) + '/SiamRPN/model.pth'
        model = SiamRPN()
        model.load_state_dict(torch.load(model_path, map_location=('cpu'
                   if str(self.device) == 'cpu' else None)))
        self.model = model.eval().to(self.device)

        # set up template memory
        self.temp_mem = THOR_SiamRPN(cfg=cfg['THOR'], net=self.model)

    def init_func(self, im, pos, sz):
        return SiamRPN_init(im, pos, sz, self.cfg['tracker'])

    def track_func(self, state, im):
        return SiamRPN_track(state, im, self.temp_mem)

class SiamMask_Tracker(Tracker):
    def __init__(self, cfg):
        super(SiamMask_Tracker, self).__init__()
        self.cfg = cfg
        self.mask = True

        # setting up the model
        model_path = dirname(abspath(__file__)) + '/SiamMask/model.pth'
        model = SiamMaskCustom(anchors=cfg['anchors'])
        model = load_pretrain(model, model_path)

        self.model = model.eval().to(self.device)

        # set up template memory
        self.temp_mem = THOR_SiamMask(cfg=cfg['THOR'], net=self.model)

    def init_func(self, im, pos, sz):
        return SiamMask_init(im, pos, sz, self.model, self.cfg['tracker'])

    def track_func(self, state, im,i=0,lt=False,):
        return SiamMask_track(state, im, self.temp_mem,i=i,lt=lt)
