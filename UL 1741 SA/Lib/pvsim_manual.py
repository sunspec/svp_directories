
import os
import pvsim

manual_info = {
    'name': os.path.splitext(os.path.basename(__file__))[0],
    'mode': 'Manual'
}

def pvsim_info():
    return manual_info

def params(info):
    info.param_add_value('pvsim.mode', manual_info['mode'])

class PVSim(pvsim.PVSim):

    def __init__(self, ts):
        pvsim.PVSim.__init__(self, ts)

    def irradiance_set(self, irradiance=1000):
        if self.ts.confirm('Please change the irradiance to %0.1f W/m^2.' % irradiance) is False:
            raise pvsim.PVSimError('Aborted PV simulation')

    def power_on(self):
        if self.ts.confirm('Please turn on PV simulator to give EUT DC power.') is False:
            raise pvsim.PVSimError('Aborted PV simulation')

    def profile_start(self):
        if self.ts.confirm('Please run the PV simulator profile.') is False:
            raise pvsim.PVSimError('Aborted PV simulation')

if __name__ == "__main__":
    pass

