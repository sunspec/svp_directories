
import os
import pvsim

terrasas_info = {
    'name': os.path.splitext(os.path.basename(__file__))[0],
    'mode': 'TerraSAS'
}

def pvsim_info():
    return terrasas_info

def params(info):
    mode = terrasas_info['mode']
    info.param_add_value('pvsim.mode', mode)
    info.param_group('pvsim.terrasas', label='Ametek TerraSAS Parameters',
                     active='pvsim.mode',  active_value=[mode], glob=True)
    info.param('pvsim.terrasas.ipaddr', label='IP Address', default='192.168.0.167')
    info.param('pvsim.terrasas.pmp', label='EN50530 MPP Power (W)', default=3000.0)
    info.param('pvsim.terrasas.vmp', label='EN50530 MPP Voltage (V)', default=460.0)
    info.param('pvsim.terrasas.channel', label='TerraSAS channel', default=10,
               desc='Channels are a string, e.g., 1:4 or 1,2,4,5.')

    
class PVSim(pvsim.PVSim):

    def __init__(self, ts):
        pvsim.PVSim.__init__(self, ts)

        self.ts = ts
        self.tsas = None

        try:
            import terrasas

            self.ipaddr = ts.param_value('pvsim.terrasas.ipaddr')
            self.pmp = ts.param_value('pvsim.terrasas.pmp')
            self.vmp = ts.param_value('pvsim.terrasas.vmp')
            self.channel = ts.param_value('pvsim.terrasas.channel')
            self.irr_start = ts.param_value('pvsim.terrasas.irr_start')
            self.profile_name = None
            self.ts.log('Initializing PV Simulator with Pmp = %d and Vmp = %d.' % (self.pmp, self.vmp))
            self.tsas = terrasas.TerraSAS(ipaddr=self.ipaddr)
            self.tsas.scan()

            channel = self.tsas.channels[self.channel]
            if channel.profile_is_active():
                channel.profile_abort()

            # re-add EN50530 curve with active parameters
            self.tsas.curve_en50530(pmp=self.pmp, vmp=self.vmp)
            channel.curve_set(terrasas.EN_50530_CURVE)

        except Exception:
            if self.tsas is not None:
                self.tsas.close()
            raise

    def close(self):
        if self.tsas is not None:
            self.tsas.close()
            self.tsas = None

    def irradiance_set(self, irradiance=1000):
        if self.tsas is not None:
            c = self.channel
            if c is not None:
                channel = self.tsas.channels[c]
                channel.irradiance_set(irradiance=irradiance)
                self.ts.log('TerraSAS irradiance changed to %0.2f on channel %d.' % (irradiance, c))
            else:
                raise pvsim.PVSimError('Simulation irradiance not specified because there is no channel specified.')
        else:
            raise pvsim.PVSimError('Irradiance was not changed.')

    def profile_load(self, profile_name):
        if profile_name != 'None' and profile_name is not None:
            self.ts.log('Loading irradiance profile %s' % profile_name)
            self.profile_name = profile_name
            profiles = self.tsas.profiles_get()
            if profile_name not in profiles:
                self.tsas.profile(profile_name)

            if self.tsas is not None:
                c = self.channel
                if c is not None:
                    channel = self.tsas.channels[c]
                    channel.profile_set(profile_name)
                    self.ts.log('TerraSAS Profile is configured.')
                else:
                    raise pvsim.PVSimError('TerraSAS Profile could not be configured.')
            else:
                raise pvsim.PVSimError('TerraSAS Profile was not changed.')
        else:
            self.ts.log('No irradiance profile loaded')

    def power_on(self):
        if self.tsas is not None:
            c = self.channel
            if c is not None:
                channel = self.tsas.channels[c]
                # turn on output if off
                if not channel.output_is_on():
                    channel.output_set_on()
                self.ts.log('TerraSAS channel %d turned on' % c)
            else:
                raise pvsim.PVSimError('Simulation channel not specified')
        else:
            raise pvsim.PVSimError('Not initialized')

    def profile_start(self):
        if self.tsas is not None:
            profile_name = self.profile_name
            if profile_name != 'None' and profile_name is not None:
                c = self.channel
                if c is not None:
                    channel = self.tsas.channels[c]
                    channel.profile_start()
                    self.ts.log('Starting PV profile')
                else:
                    raise pvsim.PVSimError('Simulation channel not specified')
        else:
            raise pvsim.PVSimError('PV Sim not initialized')

if __name__ == "__main__":
    pass