import sys
import os
import glob
import importlib

das_modules = {}


def params(info, id=None, label='Data Acquisition System'):
    group_name = DAS_DEFAULT_ID
    if id is not None:
        group_name = group_name + '_' + str(id)
    print 'group_name = %s' % group_name
    name = lambda name: group_name + '.' + name
    info.param_group(group_name, label='%s Parameters' % label, glob=True)
    print 'name = %s' % name('mode')
    info.param(name('mode'), label='Mode', default='Manual', values=[])
    for mode, m in das_modules.iteritems():
        m.params(info, group_name=group_name)

DAS_DEFAULT_ID = 'das'


def das_init(ts, id=None):
    """
    Function to create specific das implementation instances.
    """
    group_name = DAS_DEFAULT_ID
    if id is not None:
        group_name = group_name + '_' + str(id)
    print 'run group_name = %s' % group_name
    mode = ts.param_value(group_name + '.' + 'mode')
    sim_module = das_modules.get(mode)
    if sim_module is not None:
        sim = sim_module.DAS(ts, group_name)
    else:
        raise DASError('Unknown data acquisition system mode: %s' % mode)

    return sim


class DASError(Exception):
    """
    Exception to wrap all das generated exceptions.
    """
    pass


class Data(object):

    def __getitem__(self, k):
        return self.__dict__[k]

    def __setitem__(self, k, v):
        self.__dict__[k] = v

    def __init__(self, ts):
        self.ts = ts
        self.values = {}

    def read(self):
        pass


class Trigger(object):

    def __init__(self, ts):
        self.ts = ts

    def on(self):
        pass

    def off(self):
        pass


class Waveform(object):

    def __init__(self, ts):
        self.ts = ts


TRIGGER_OFF = 0
TRIGGER_ON = 1


class DAS(object):
    """
    Template for grid simulator implementations. This class can be used as a base class or
    independent grid simulator classes can be created containing the methods contained in this class.
    """

    def __init__(self, ts, group_name):
        self.ts = ts
        self.group_name = group_name

    def data_init(self):
        return Data(self.ts)

    def config(self):
        """
        Perform any configuration for the simulation based on the previously
        provided parameters.
        """
        pass

    def open(self):
        """
        Open the communications resources associated with the grid simulator.
        """
        pass

    def close(self):
        """
        Close any open communications resources associated with the grid
        simulator.
        """
        pass

    def value_capture(self):
        pass

    def waveform_capture(self):
        pass

    def soft_trigger(self, state=None):
        pass

    def trigger_init(self):
        return Trigger(self.ts)

    def trigger(self):
        pass


def das_scan():
    global das_modules
    # scan all files in current directory that match das_*.py
    files = glob.glob(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'das_*.py'))
    for f in files:
        module_name = None
        try:
            module_name = os.path.splitext(os.path.basename(f))[0]
            m = importlib.import_module(module_name)
            if hasattr(m, 'das_info'):
                info = m.das_info()
                mode = info.get('mode')
                # place module in module dict
                if mode is not None:
                    das_modules[mode] = m
            else:
                if module_name is not None and module_name in sys.modules:
                    del sys.modules[module_name]
        except Exception, e:
            if module_name is not None and module_name in sys.modules:
                del sys.modules[module_name]
            raise DASError('Error scanning module %s: %s' % (module_name, str(e)))

# scan for das modules on import
das_scan()

if __name__ == "__main__":
    pass
