import scipy as _sp
import pandas as _pd
from openpnm.core import logging
logger = logging.getLogger(__name__)


class Pandas():

    @staticmethod
    def get_data_frames(simulation, phases=[]):
        r"""
        Convert the Network (and optionally Phase) data to Pandas DataFrames.

        Parameters
        ----------
        simulation : OpenPNM Simulation Object
            The simulation containing the data to be stored

        phases : list of OpenPNM Phase Objects
            The data on each supplied phase will be added to the CSV file

        Returns
        -------
        A dict containing 2 Pandas DataFrames with 'pore' and 'throat' data in
        each.
        """
        network = simulation.network

        if type(phases) is not list:  # Ensure it's a list
            phases = [phases]

        # Initialize pore and throat data dictionary with conns and coords
        pdata = {}
        tdata = {}

        # Gather list of prop names from network and geometries
        pprops = set(network.props(element='pore', deep=True) +
                     network.labels(element='pore'))
        tprops = set(network.props(element='throat', deep=True) +
                     network.labels(element='throat'))

        # Select data from network and geometries using keys
        for item in pprops:
            pdata.update({item: network[item]})
        for item in tprops:
            tdata.update({item: network[item]})

        # Gather list of prop names from phases and physics
        for phase in phases:
            # Gather list of prop names
            pprops = set(phase.props(element='pore', mode=['all', 'deep']) +
                         phase.labels(element='pore'))
            tprops = set(phase.props(element='throat', mode=['all', 'deep']) +
                         phase.labels(element='throat'))
            # Add props to tdata and pdata
            for item in pprops:
                pdata.update({item+'|'+phase.name: phase[item]})
            for item in tprops:
                tdata.update({item+'|'+phase.name: phase[item]})

        # Scan data and convert non-1d arrays to strings
        for item in list(pdata.keys()):
            if _sp.shape(pdata[item]) != (network.Np,):
                array = pdata.pop(item)
                temp = _sp.empty((_sp.shape(array)[0], ), dtype=object)
                for row in range(temp.shape[0]):
                    temp[row] = str(array[row, :]).strip('[]')
                pdata.update({item: temp})

        for item in list(tdata.keys()):
            if _sp.shape(tdata[item]) != (network.Nt,):
                array = tdata.pop(item)
                temp = _sp.empty((_sp.shape(array)[0], ), dtype=object)
                for row in range(temp.shape[0]):
                    temp[row] = str(array[row, :]).strip('[]')
                tdata.update({item: temp})

        data = {'pore.DataFrame': _pd.DataFrame.from_dict(pdata),
                'throat.DataFrame': _pd.DataFrame.from_dict(tdata)}

        return data
