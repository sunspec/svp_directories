"""
Copyright (c) 2015, Sandia National Labs and SunSpec Alliance
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer.

Redistributions in binary form must reproduce the above copyright notice, this
list of conditions and the following disclaimer in the documentation and/or
other materials provided with the distribution.

Neither the names of the Sandia National Labs and SunSpec Alliance nor the names of its
contributors may be used to endorse or promote products derived from
this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

Written by Sandia National Laboratories, Loggerware, and SunSpec Alliance
"""


import os

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

class Data(object):

    def __getitem__(self, k):
        return self.__dict__[k]

    def __setitem__(self, k, v):
        self.__dict__[k] = v

    def extract_points(self, points_str):
        x = points_str.replace(' ', '_').replace('][', ' ').strip('[]').split()
        for p in x:
            if p.find(',') != -1:
                return p.split(',')

    def __init__(self, dsm_id=None, data_file=DATA_FILE, points_file=POINTS_FILE, points=None):

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

        s = 'dsm_data:\n'
        for k, v in dsm_points.iteritems():
            s += '  %s: %s\n' % (v, self[v])
        return s


class Trigger(object):

    def __init__(self, filename=TRIGGER_FILE):

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


class WfmTrigger(object):

    def __init__(self, ts, filename=WFM_TRIGGER_FILE):

        self.filename = filename
        self.on_error_count = 0
        self.on_last_error = ''
        self.off_error_count = 0
        self.off_last_error = ''
        self.ts = ts

    def trigger(self, wfmtrigger_params=None):

        if wfmtrigger_params is not None:
            try:
                # Formatting for the file:
                # Sampling rate, e.g., 24.5e3
                # Pretrigger (sec), e.g., 0
                # Post-trigger (sec), e.g., 1.000
                # Trigger Level, e.g., 3.000
                # Hysteresis/Window, e.g., 10.000e-3
                # Time Limit (sec), e.g., 90
                # Condition, e.g., Falling Edge, Rising Edge, Above Level, Below Level, When Inside Window, When Outside Window
                # Trigger Channel, e.g., DC_Voltage_1
                # Channels to Acquire, e.g.,
                # AC_Voltage_1
                # DC_Voltage_2
                # DC_Voltage_1

                f = open(self.filename, 'w')
                f.write("%s\n" % wfmtrigger_params.get('trigsamplingrate'))
                f.write("%s\n" % wfmtrigger_params.get('pretrig'))
                f.write("%s\n" % wfmtrigger_params.get('posttrig'))
                f.write("%s\n" % wfmtrigger_params.get('trigval'))
                f.write("%s\n" % wfmtrigger_params.get('trighyswindow'))
                f.write("%s\n" % wfmtrigger_params.get('trigtimeout'))
                f.write("%s\n" % wfmtrigger_params.get('trigcondition'))
                f.write("%s\n" % wfmtrigger_params.get('trigchannel'))
                collectedchans = wfmtrigger_params.get('trigacqchannels')
                formattedchans = collectedchans.replace(", ", "\n")
                formattedchans = formattedchans.replace(",", "\n")
                f.write("%s" % formattedchans)
                f.close()
            except Exception, e:
                self.on_error_count += 1
                self.on_last_error = str(e)

    def getfilename(self):

        try:
            import glob
            return max(glob.iglob('C:\python_dsm\*.[Ww][Ff][Mm]'), key=os.path.getctime)  #fix with os.path.sep
        except Exception, e:
            self.off_error_count += 1
            self.off_last_error = str(e)

    def read_file(self, wfmname):

        try:
            from collections import defaultdict
            columns = defaultdict(list)  # each value in each column is appended to a list

            import csv
            with open(wfmname, 'r') as f:
                reader = csv.reader(f, delimiter='\t')
                reader.next()
                for row in reader:
                    for (j, v) in enumerate(row):
                        columns[j].append(v)

            wfmtime = [float(i) for i in columns[0]]
            ac_voltage = [float(i) for i in columns[1]]
            ac_current = [float(i) for i in columns[2]]

            if len(columns) > 3:
                daq_trig = [float(i) for i in columns[3]]
                return wfmtime, ac_voltage, ac_current, daq_trig
            else:
                return wfmtime, ac_voltage, ac_current

        except Exception, e:
            self.off_error_count += 1
            self.off_last_error = ('%s - Waveform file is likely corrupted or wasn\'t created properly' % str(e))

    def move_file_to_results(self, wfmname, results_dir, delete_original):

        try:
            import shutil
            #results_dir = os.path.dirname(__file__)[:-7] + 'Results' + os.path.sep
            if delete_original == 'Yes':
                shutil.move(wfmname, results_dir)
            else:
                shutil.copy(wfmname, results_dir)
        except Exception, e:
            self.off_error_count += 1
            self.off_last_error = str(e)

    def save_file_to_results(self, wfmtime, ac_current, ac_voltage):

        try:
            import csv
            import time
            with open('VRT' + str(time.time()) + '.csv', 'w') as csvfile:
                fieldnames = ['Time', 'Current', 'Voltage']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow({'first_name': 'Baked', 'last_name': 'Beans'})

        except Exception, e:
            self.off_error_count += 1
            self.off_last_error = str(e)

if __name__ == "__main__":

    d = Data(data_file=DATA_FILE, points_file=POINTS_FILE)
    d.read()
    print d
    print d.ac_pf, d.trigger

    '''
    t = Trigger()
    t.on()
    #t.off()
    print t.on_error_count, t.on_last_error
    '''


