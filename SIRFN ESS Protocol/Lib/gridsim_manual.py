
import os
import gridsim

manual_info = {
    'name': os.path.splitext(os.path.basename(__file__))[0],
    'mode': 'Manual'
}

def gridsim_info():
    return manual_info

def params(info):
    info.param_add_value('gridsim.mode', manual_info['mode'])


class GridSim(gridsim.GridSim):

    def __init__(self, ts, params=None):
        gridsim.GridSim.__init__(self, ts, params)

        if ts.confirm('Please run the grid simulator profile.') is False:
            raise gridsim.GridSimError('Aborted grid simulation')
