from xml.etree import ElementTree as ET
import numpy as np
from openpnm.core import logging, Workspace
from openpnm.network import GenericNetwork
from openpnm.io import GenericIO
logger = logging.getLogger(__name__)
mgr = Workspace()


class VTK(GenericIO):
    r"""
    Class for writing a Vtp file to be read by ParaView

    """

    _TEMPLATE = '''
    <?xml version="1.0" ?>
    <VTKFile byte_order="LittleEndian" type="PolyData" version="0.1">
        <PolyData>
            <Piece NumberOfLines="0" NumberOfPoints="0">
                <Points>
                </Points>
                <Lines>
                </Lines>
                <PointData>
                </PointData>
                <CellData>
                </CellData>
            </Piece>
        </PolyData>
    </VTKFile>
    '''.strip()

    @classmethod
    def save(cls, simulation, filename='', phases=[]):
        r"""
        Save network and phase data to a single vtp file for visualizing in
        Paraview

        Parameters
        ----------
        simulation : OpenPNM Simulation Object
            The Simulation containing the data to be written

        filename : string, optional
            Filename to write data.  If no name is given the file is named
            after ther network

        phases : list, optional
            A list containing OpenPNM Phase object(s) containing data to be
            written

        """
        network = simulation.network

        if filename == '':
            filename = network.name
        if ~filename.endswith('.vtp'):
            filename = filename+'.vtp'

        root = ET.fromstring(VTK._TEMPLATE)
        objs = []
        if type(phases) != list:
            phases = [phases]
        for phase in phases:
            objs.append(phase)
        objs.append(network)

        am = {i: network[i] for i in
              network.props(deep=True) + network.labels()}
        for phase in phases:
            dict_ = {i+'|'+phase.name: phase[i] for i in
                     phase.props(mode=['all', 'deep']) + phase.labels()}
            am.update(dict_)

        key_list = list(sorted(am.keys()))
        points = network['pore.coords']
        pairs = network['throat.conns']

        num_points = np.shape(points)[0]
        num_throats = np.shape(pairs)[0]

        piece_node = root.find('PolyData').find('Piece')
        piece_node.set("NumberOfPoints", str(num_points))
        piece_node.set("NumberOfLines", str(num_throats))

        points_node = piece_node.find('Points')
        coords = VTK._array_to_element("coords", points.T.ravel('F'), n=3)
        points_node.append(coords)

        lines_node = piece_node.find('Lines')
        connectivity = VTK._array_to_element("connectivity", pairs)
        lines_node.append(connectivity)
        offsets = VTK._array_to_element("offsets", 2*np.arange(len(pairs))+2)
        lines_node.append(offsets)

        point_data_node = piece_node.find('PointData')
        for key in key_list:
            array = am[key]
            if array.dtype == np.bool:
                array = array.astype(int)
            if array.size != num_points:
                continue
            element = VTK._array_to_element(key, array)
            point_data_node.append(element)

        cell_data_node = piece_node.find('CellData')
        for key in key_list:
            array = am[key]
            if array.dtype == np.bool:
                array = array.astype(int)
            if array.size != num_throats:
                continue
            element = VTK._array_to_element(key, array)
            cell_data_node.append(element)

        tree = ET.ElementTree(root)
        tree.write(filename)

        # Make pretty
        with open(filename, 'r+') as f:
            string = f.read()
            string = string.replace('</DataArray>', '</DataArray>\n\t\t\t')
            f.seek(0)
            # consider adding header: '<?xml version="1.0"?>\n'+
            f.write(string)

    @classmethod
    def load(cls, filename, network=None, return_geometry=False):
        r"""
        Read in pore and throat data from a saved VTK file.

        Parameters
        ----------
        filename : string (optional)
            The name of the file containing the data to import.  The formatting
            of this file is outlined below.

        network : OpenPNM Network Object
            The Network object onto which the data should be loaded.  If no
            Network is supplied than one will be created and returned.

        return_geometry : Boolean
            If True, then all geometrical related properties are removed from
            the Network object and added to a GenericGeometry object.  In this
            case the method returns a tuple containing (network, geometry). If
            False (default) then the returned Network will contain all
            properties that were in the original file.  In this case, the user
            can call the ```split_geometry``` method explicitly to perform the
            separation.

        Returns
        -------
        If no Network object is supplied then one will be created and returned.

        If return_geometry is True, then a tuple is returned containing both
        the network and a geometry object.
        """
        net = {}

        filename = filename.rsplit('.', maxsplit=1)[0]
        tree = ET.parse(filename+'.vtp')
        piece_node = tree.find('PolyData').find('Piece')

        # Extract connectivity
        conn_element = piece_node.find('Lines').find('DataArray')
        array = VTK._element_to_array(conn_element, 2)
        net.update({'throat.conns': array})
        # Extract coordinates
        coord_element = piece_node.find('Points').find('DataArray')
        array = VTK._element_to_array(coord_element, 3)
        net.update({'pore.coords': array})

        # Extract pore data
        for item in piece_node.find('PointData').iter('DataArray'):
            key = item.get('Name')
            element = key.split('.')[0]
            array = VTK._element_to_array(item)
            propname = key.split('.')[1]
            net.update({element+'.'+propname: array})
        # Extract throat data
        for item in piece_node.find('CellData').iter('DataArray'):
            key = item.get('Name')
            element = key.split('.')[0]
            array = VTK._element_to_array(item)
            propname = key.split('.')[1]
            net.update({element+'.'+propname: array})

        if network is None:
            network = GenericNetwork()
        network = cls._update_network(network=network, net=net,
                                      return_geometry=return_geometry)
        return network

    @staticmethod
    def _array_to_element(name, array, n=1):
        dtype_map = {
            'int8': 'Int8',
            'int16': 'Int16',
            'int32': 'Int32',
            'int64': 'Int64',
            'uint8': 'UInt8',
            'uint16': 'UInt16',
            'uint32': 'UInt32',
            'uint64': 'UInt64',
            'float32': 'Float32',
            'float64': 'Float64',
            'str': 'String',
        }
        element = ET.Element('DataArray')
        element.set("Name", name)
        element.set("NumberOfComponents", str(n))
        element.set("type", dtype_map[str(array.dtype)])
        element.text = '\t'.join(map(str, array.ravel()))
        return element

    @staticmethod
    def _element_to_array(element, n=1):
        string = element.text
        dtype = element.get("type")
        array = np.fromstring(string, sep='\t')
        array = array.astype(dtype)
        if n is not 1:
            array = array.reshape(array.size//n, n)
        return array
