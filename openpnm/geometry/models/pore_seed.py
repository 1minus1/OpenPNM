# -*- coding: utf-8 -*-
r"""
===============================================================================
pore_seed -- Methods for generating fields of values for use as seeds in
statistical pore size distributions
===============================================================================

"""
from . import misc as _misc
import scipy as _sp
from openpnm.core import logging
_logger = logging.getLogger(__name__)


def random(target, seed=None, num_range=[0, 1]):
    return _misc.random(target, element='pore', seed=seed, num_range=num_range)


random.__doc__ = _misc.random.__doc__


def spatially_correlated(target, weights=None, strel=None):
    r"""
    Generates pore seeds that are spatailly correlated with their neighbors.

    Parameters
    ----------
    target : OpenPNM Object
        The object which this model is associated with. This controls the
        length of the calculated array, and also provides access to other
        necessary properties.

    weights : list of ints, optional
        The [Nx,Ny,Nz] distances (in number of pores) in each direction that
        should be correlated.

    strel : array_like, optional (in place of weights)
        The option allows full control over the spatial correlation pattern by
        specifying the structuring element to be used in the convolution.

        The array should be a 3D array containing the strength of correlations
        in each direction.  Nonzero values indicate the strength, direction
        and extent of correlations.  The following would achieve a basic
        correlation in the z-direction:

        strel = sp.array([[[0, 0, 0], [0, 0, 0], [0, 0, 0]], \
                          [[0, 0, 0], [1, 1, 1], [0, 0, 0]], \
                          [[0, 0, 0], [0, 0, 0], [0, 0, 0]]])

    Notes
    -----
    This approach uses image convolution to replace each pore seed in the
    geoemtry with a weighted average of those around it.  It then converts the
    new seeds back to a random distribution by assuming they new seeds are
    normally distributed.

    Because is uses image analysis tools, it only works on Cubic networks.

    This is the appproached used by Gostick et al [2]_ to create an anistropic
    gas diffusion layer for fuel cell electrodes.

    References
    ----------
    .. [2] J. Gostick et al, Pore network modeling of fibrous gas diffusion
           layers for polymer electrolyte membrane fuel cells. J Power Sources
           v173, pp277–290 (2007)

    Examples
    --------
    >>> import OpenPNM
    >>> pn = OpenPNM.Network.Cubic(shape=[50, 50, 50])
    >>> geom = OpenPNM.Geometry.GenericGeometry(network=pn,
    ...                                         pores=pn.Ps,
    ...                                         throats=pn.Ts)
    >>> mod = OpenPNM.Geometry.models.pore_seed.spatially_correlated
    >>> geom.add_model(propname='pore.seed',
    ...                model=mod,
    ...                weights=[2, 2, 2])
    >>> im = pn.asarray(geom['pore.seed'])

    Visualizing the end result can be done with:

        ```matplotlib.pyplot.imshow(im[:, 25, :],interpolation='none')```

    """
    import scipy.ndimage as spim
    network = target.simulation.network
    # The following will only work on Cubic networks
    x = network._shape[0]
    y = network._shape[1]
    z = network._shape[2]
    im = _sp.rand(x, y, z)
    if strel is None:  # Then generate a strel
        if sum(weights) == 0:
            # If weights of 0 are sent, then skip everything and return rands.
            return im.flatten()
        w = _sp.array(weights)
        strel = _sp.zeros(w*2+1)
        strel[:, w[1], w[2]] = 1
        strel[w[0], :, w[2]] = 1
        strel[w[0], w[1], :] = 1
    im = spim.convolve(im, strel)
    # Convolution is no longer randomly distributed, so fit a gaussian
    # and find it's seeds
    im = (im - _sp.mean(im))/_sp.std(im)
    im = 1/2*_sp.special.erfc(-im/_sp.sqrt(2))
    values = im.flatten()
    values = values[network.pores(target.name)]
    return values


def location_adjusted(target, image=None):
    r"""
    Use a greyscale image to adjust randomly generated seed values based on
    their location within the image.

    Parameters
    ----------
    target : OpenPNM Object
        The object which this model is associated with. This controls the
        length of the calculated array, and also provides access to other
        necessary properties.

    image : ndarray (3-dimensional)
        values between 0.0 and 1.0 which are used to scale the seed number.

    Notes
    ----------
    The shape of the image reflects the relative position of the pore in the
    geometry. The image shape does not have to equal the domain shape.
    For example passing in a [2, 2, 2] image divides the domain into equal
    eigths and if ``image[0, 0, 0] == 0.5`` the pores in the bottom front left
    section have their seed values halved.

    Examples
    ----------
    >>> import OpenPNM
    >>> pn = OpenPNM.Network.Cubic(shape=[6,6,6])
    >>> geom = OpenPNM.Geometry.GenericGeometry(network=pn, pores=pn.Ps,
    ...                                         throats=pn.Ts)
    >>> import numpy as np
    >>> im = np.ones([3,3,3])
    >>> im[:,:,0] = 0.5
    >>> im[:,:,1] = 0.75
    >>> model = OpenPNM.Geometry.models.pore_seed.location_adjusted
    >>> geom.add_model(propname='pore.seed', model=model, image=im)
    """
    # Generate the random seed values
    network = target.simulation.network
    value = _sp.random.rand(target.num_pores(),)
    if image is not None:
        if _sp.any(image < 0) or _sp.any(image > 1):
            _logger.warning('The image must only contain values between 0.0 '
                            'and 1.0, the image has been ignored')
        elif _sp.shape(_sp.shape(image))[0] != 3:
            _logger.warning('The image shape must be 3-dimensional, ' +
                            'the image has been ignored')
        else:
            coords = network["pore.coords"][network.pores(target.name)]
            # Find the upper and lower limits of the network coordinates
            x_min = coords[:, 0].min()
            x_max = coords[:, 0].max()
            y_min = coords[:, 1].min()
            y_max = coords[:, 1].max()
            z_min = coords[:, 2].min()
            z_max = coords[:, 2].max()
            # Get the shape of the probability array
            image_max_ind = _sp.asarray(_sp.shape(image))-[1, 1, 1]
            # Compute the relative coordinates to inspect the image array
            rel_coords = coords.copy()
            rel_coords -= [x_min, y_min, z_min]
            rel_coords /= [x_max-x_min, y_max-y_min, z_max-z_min]
            rel_coords *= image_max_ind
            rel_coords = _sp.around(rel_coords, 0).astype(int)
            # Now we have transformed the relative coordinate to point to
            # indices of the image array, collect the adjusting value for each
            # coordinate
            adjust = []
            for i, j, k in rel_coords:
                adjust.append(image[i][j][k])
            # Apply the adjustment to the random values setting local limits
            value *= _sp.asarray(adjust)

    return value