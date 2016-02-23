import os
import das

sandia_info = {
    'name': os.path.splitext(os.path.basename(__file__))[0],
    'mode': 'Sandia DSM'
}

def das_info():
    return sandia_info

def params(info, group_name=None):
    gname = lambda name: group_name + '.' + name
    pname = lambda name: group_name + '.' + GROUP_NAME + '.' + name
    mode = sandia_info['mode']
    info.param_add_value(gname('mode'), mode)
    info.param_group(gname(GROUP_NAME), label='%s Parameters' % mode,
                     active=gname('mode'),  active_value=mode, glob=True)
    info.param(pname('dsm_method'), label='Data Acquisition Method', default='Sandia LabView DSM',
               values=['Sandia LabView DSM', 'TCP Stream for Sandia LabView DSM'],
               desc='Each lab will have different data acquisition methods. Sandia passes the data from the DAQ '
                    'to python by writing the values locally or collecting them over the local TCP network.')
    info.param(pname('das_comp'), label='Data Acquisition Computer', default='10 Node',
               values=['10 Node', 'DAS 3', 'DAS 5', 'DAS 8'],
               active=pname('dsm_method'), active_value=['Sandia LabView DSM'],
               desc='Selection of the data acquisition system (if there are multiple options).')
    info.param(pname('node'), label='Node at Sandia - Used to ID DAQ channel', default=10, active=pname('das_comp'),
               active_value=['10 Node'],
               desc='Selection of the EUT which will be used for the test (Sandia specific).')

GROUP_NAME = 'sandia'

PATH = 'C:\\python_dsm\\'
POINTS_FILE = 'C:\\python_dsm\\channels.txt'
DATA_FILE = 'C:\\python_dsm\\data.txt'
TRIGGER_FILE = 'C:\\python_dsm\\trigger.txt'
WFM_TRIGGER_FILE = 'C:\\python_dsm\\waveform trigger.txt'

# Data channels for Node 1
dsm_points_1 = {
    'time': 'time',
    'dc_voltage_1': 'dc_voltage',
    'dc_current_1': 'dc_current',
    'ac_voltage_1': 'ac_voltage',
    'ac_current_1': 'ac_current',
    'dc1_watts': 'dc_watts',
    'ac1_va': 'ac_va',
    'ac1_watts': 'ac_watts',
    'ac1_vars': 'ac_vars',
    'ac1_freq': 'ac_freq',
    'ac_1_pf': 'ac_pf',
    'pythontrigger': 'trigger',
    'ametek_trigger': 'ametek_trigger'
}

# Data channels for Node 2
dsm_points_2 = {
    'time': 'time',
    'dc_voltage_2': 'dc_voltage',
    'dc_current_2': 'dc_current',
    'ac_voltage_2': 'ac_voltage',
    'ac_current_2': 'ac_current',
    'dc2_watts': 'dc_watts',
    'ac2_va': 'ac_va',
    'ac2_watts': 'ac_watts',
    'ac2_vars': 'ac_vars',
    'ac1_freq': 'ac_freq',
    'ac_2_pf': 'ac_pf',
    'pythontrigger': 'trigger',
    'ametek_trigger': 'ametek_trigger'
}

# Data channels for Node 3
dsm_points_3 = {
    'time': 'time',
    'dc_voltage_3': 'dc_voltage',
    'dc_current_3': 'dc_current',
    'ac_voltage_3': 'ac_voltage',
    'ac_current_3': 'ac_current',
    'dc3_watts': 'dc_watts',
    'ac3_va': 'ac_va',
    'ac3_watts': 'ac_watts',
    'ac3_vars': 'ac_vars',
    'ac1_freq': 'ac_freq',
    'ac_3_pf': 'ac_pf',
    'pythontrigger': 'trigger',
    'ametek_trigger': 'ametek_trigger'
}

# Data channels for Node 4
dsm_points_4 = {
    'time': 'time',
    'dc_voltage_4': 'dc_voltage',
    'dc_current_4': 'dc_current',
    'ac_voltage_4': 'ac_voltage',
    'ac_current_4': 'ac_current',
    'dc4_watts': 'dc_watts',
    'ac4_va': 'ac_va',
    'ac4_watts': 'ac_watts',
    'ac4_vars': 'ac_vars',
    'ac1_freq': 'ac_freq',
    'ac_4_pf': 'ac_pf',
    'pythontrigger': 'trigger',
    'ametek_trigger': 'ametek_trigger'
}

# Data channels for Node 5
dsm_points_5 = {
    'time': 'time',
    'dc_voltage_5': 'dc_voltage',
    'dc_current_5': 'dc_current',
    'ac_voltage_5': 'ac_voltage',
    'ac_current_5': 'ac_current',
    'dc5_watts': 'dc_watts',
    'ac5_va': 'ac_va',
    'ac5_watts': 'ac_watts',
    'ac5_vars': 'ac_vars',
    'ac1_freq': 'ac_freq',
    'ac_5_pf': 'ac_pf',
    'pythontrigger': 'trigger',
    'ametek_trigger': 'ametek_trigger'
}

# Data channels for Node 6
dsm_points_6 = {
    'time': 'time',
    'dc_voltage_6': 'dc_voltage',
    'dc_current_6': 'dc_current',
    'ac_voltage_6': 'ac_voltage',
    'ac_current_6': 'ac_current',
    'dc6_watts': 'dc_watts',
    'ac6_va': 'ac_va',
    'ac6_watts': 'ac_watts',
    'ac6_vars': 'ac_vars',
    'ac6_freq': 'ac_freq',
    'ac_6_pf': 'ac_pf',
    'pythontrigger': 'trigger',
    'ametek_trigger': 'ametek_trigger'
}

# Data channels for Node 7
dsm_points_7 = {
    'time': 'time',
    'dc_voltage_7': 'dc_voltage',
    'dc_current_7': 'dc_current',
    'ac_voltage_7': 'ac_voltage',
    'ac_current_7': 'ac_current',
    'dc7_watts': 'dc_watts',
    'ac7_va': 'ac_va',
    'ac7_watts': 'ac_watts',
    'ac7_vars': 'ac_vars',
    'ac6_freq': 'ac_freq',
    'ac_7_pf': 'ac_pf',
    'pythontrigger': 'trigger',
    'ametek_trigger': 'ametek_trigger'
}

# Data channels for Node 8
dsm_points_8 = {
    'time': 'time',
    'dc_voltage_8': 'dc_voltage',
    'dc_current_8': 'dc_current',
    'ac_voltage_8': 'ac_voltage',
    'ac_current_8': 'ac_current',
    'dc8_watts': 'dc_watts',
    'ac8_va': 'ac_va',
    'ac8_watts': 'ac_watts',
    'ac8_vars': 'ac_vars',
    'ac6_freq': 'ac_freq',
    'ac_8_pf': 'ac_pf',
    'pythontrigger': 'trigger',
    'ametek_trigger': 'ametek_trigger'
}

# Data channels for Node 9
dsm_points_9 = {
    'time': 'time',
    'dc_voltage_9': 'dc_voltage',
    'dc_current_9': 'dc_current',
    'ac_voltage_9': 'ac_voltage',
    'ac_current_9': 'ac_current',
    'dc9_watts': 'dc_watts',
    'ac9_va': 'ac_va',
    'ac9_watts': 'ac_watts',
    'ac9_vars': 'ac_vars',
    'ac6_freq': 'ac_freq',
    'ac_9_pf': 'ac_pf',
    'pythontrigger': 'trigger',
    'ametek_trigger': 'ametek_trigger'
}

# Data channels for Node 10
dsm_points_10 = {
    'time': 'time',
    'dc_voltage_10': 'dc_voltage',
    'dc_current_10': 'dc_current',
    'ac_voltage_10': 'ac_voltage',
    'ac_current_10': 'ac_current',
    'dc10_watts': 'dc_watts',
    'ac10_va': 'ac_va',
    'ac10_watts': 'ac_watts',
    'ac10_vars': 'ac_vars',
    'ac6_freq': 'ac_freq',
    'ac_10_pf': 'ac_pf',
    'pythontrigger': 'trigger',
    'ametek_trigger': 'ametek_trigger'
}

dsm_points_map = {
    '1': dsm_points_1,
    '2': dsm_points_2,
    '3': dsm_points_3,
    '4': dsm_points_4,
    '5': dsm_points_5,
    '6': dsm_points_6,
    '7': dsm_points_7,
    '8': dsm_points_8,
    '9': dsm_points_9,
    '10': dsm_points_10
}

class Data(das.Data):

    def extract_points(self, points_str):
        x = points_str.replace(' ', '_').replace('][', ' ').strip('[]').split()
        for p in x:
            if p.find(',') != -1:
                return p.split(',')

    def __init__(self, ts, dsm_id=None, data_file=DATA_FILE, points_file=POINTS_FILE, points=None):
        das.Data.__init__(self, ts)
        self._data_file = data_file
        self._points = points
        self._points_map = dsm_points_map.get(str(dsm_id), dsm_points_10)
        self.read_error_count = 0
        self.read_last_error = ''

        if self._points is None:
            self._points = []
            if points_file is not None:
                f = open(points_file)
                channels = f.read()
                f.close()
                self._points = self.extract_points(channels)

        for p in self._points:
            point_name = self._points_map.get(p)
            if point_name is not None:
                self[point_name] = None

    def read(self):
        try:
            f = open(self._data_file)
            data = f.read()
            f.close()
            points = self.extract_points(data)
            if len(points) == len(self._points):
                for i in range(len(self._points)):
                    # get normalized name
                    point_name = self._points_map.get(self._points[i])
                    if point_name is not None:
                        self[point_name] = float(points[i])

        except Exception, e:
            self.read_error_count += 1
            self.read_last_error = str(e)

    def __str__(self):
        '''
        s = 'dsm_data:\n'
        for k, v in dsm_points.iteritems():
            s += '  %s: %s\n' % (v, self[v])
        return s
        '''
        pass


class Trigger(das.Trigger):

    def __init__(self, ts, filename=TRIGGER_FILE):
        das.Trigger.__init__(self, ts)
        self.filename = filename
        self.on_error_count = 0
        self.on_last_error = ''
        self.off_error_count = 0
        self.off_last_error = ''

    def on(self):
        try:
            f = open(self.filename, 'w')
            # f.write('trigger')
            f.close()
        except Exception, e:
            self.on_error_count += 1
            self.on_last_error = str(e)

    def off(self):
        try:
            os.remove(self.filename)
        except Exception, e:
            self.off_error_count += 1
            self.off_last_error = str(e)


class DAS(das.DAS):
    """
    Template for grid simulator implementations. This class can be used as a base class or
    independent grid simulator classes can be created containing the methods contained in this class.
    """

    def __init__(self, ts, group_name):
        das.DAS.__init__(self, ts, group_name)
        self.ts.log('dsm_method = %s' % self.param_value('dsm_method'))

    def param_value(self, name):
        return self.ts.param_value(self.group_name + '.' + GROUP_NAME + '.' + name)

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

    def trigger_init(self):
        return Trigger(self.ts)

    def trigger(self, state=None):
        pass

if __name__ == "__main__":
    pass

