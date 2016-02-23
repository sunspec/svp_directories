"""
  Copyright (c) 2015, SunSpec Alliance
  All Rights Reserved

  Software created under the SunSpec Alliance - Sandia National Laboratories CRADA 1831.00
"""


import sys
import os
import glob
import importlib

pvsim_modules = {}

def params(info):
    info.param_group('pvsim', label='PV Simulator Parameters', glob=True)
    info.param('pvsim.mode', label='PV Simulation Mode', default='Manual', values=[])
    for mode, m in pvsim_modules.iteritems():
        m.params(info)

def pvsim_init(ts):
    """
    Function to create specific grid simulator implementation instances.

    Each supported grid simulator type should have an entry in the 'mode' parameter conditional.
    Module import for the simulator is done within the conditional so modules only need to be
    present if used.
    """
    mode = ts.param_value('pvsim.mode')
    sim_module = pvsim_modules.get(mode)
    if sim_module is not None:
        sim = sim_module.PVSim(ts)
    else:
        raise PVSimError('Unknown PV simulation mode: %s' % mode)

    return sim

class PVSimError(Exception):
    pass

class PVSim(object):

    def __init__(self, ts, params=None):
        self.ts = ts

    def close(self):
        pass

    def irradiance_set(self, irradiance=1000):
        pass

    def profile_load(self, profile_name):
        # use pv_profiles.py to create profile
        pass

    def power_on(self):
        pass

    def profile_start(self):
        pass


def pvsim_scan():
    global pvsim_modules
    # scan all files in current directory that match gridsim_*.py
    files = glob.glob(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'pvsim_*.py'))
    for f in files:
        module_name = None
        try:
            module_name = os.path.splitext(os.path.basename(f))[0]
            m = importlib.import_module(module_name)
            if hasattr(m, 'pvsim_info'):
                info = m.pvsim_info()
                mode = info.get('mode')
                # place module in module dict
                if mode is not None:
                    pvsim_modules[mode] = m
            else:
                if module_name is not None and module_name in sys.modules:
                    del sys.modules[module_name]
        except Exception, e:
            if module_name is not None and module_name in sys.modules:
                del sys.modules[module_name]
            raise PVSimError('Error scanning module %s: %s' % (module_name, str(e)))

# scan for gridsim modules on import
pvsim_scan()


if __name__ == "__main__":
    pass