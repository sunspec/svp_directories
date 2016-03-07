
import os
import das

manual_info = {
    'name': os.path.splitext(os.path.basename(__file__))[0],
    'mode': 'Manual'
}

def das_info():
    return manual_info

def params(info, group_name):
    gname = lambda name: group_name + '.' + name
    pname = lambda name: group_name + '.' + GROUP_NAME + '.' + name
    mode = manual_info['mode']
    info.param_add_value(gname('mode'), mode)

GROUP_NAME = 'manual'

class DAS(das.DAS):

    def __init__(self, ts, group_name):
        das.DAS.__init__(self, ts, group_name)

    def data_init(self):
        return None

    def trigger_init(self):
        return None
