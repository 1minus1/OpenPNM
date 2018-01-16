import openpnm as op
import scipy as sp
ws = op.core.Workspace()
ws.settings['local_data'] = True

sp.random.seed(0)
pn = op.network.Cubic(shape=[15, 15, 15], spacing=0.0001, name='pn')
# pn.add_boundaries()

geom = op.geometry.StickAndBall(network=pn, pores=pn.Ps, throats=pn.Ts)
geom

water = op.phases.Water(network=pn)
water['throat.viscosity'] = water['pore.viscosity'][0]

phys_water = op.physics.GenericPhysics(network=pn, phase=water, geometry=geom)
mod = op.physics.models.hydraulic_conductance.hagen_poiseuille
phys_water.add_model(propname='throat.conductance',
                     model=mod, viscosity='throat.viscosity')
phys_water.regenerate_models()

alg = op.algorithms.FickianDiffusion(network=pn, phase=water)
alg.setup(conductance='throat.conductance', quantity='pore.mole_fraction')
alg.set_BC(pores=pn.pores('top'), bctype='dirichlet', bcvalues=0.5)
alg['pore.mole_fraction'] = 0
alg.set_BC(pores=pn.pores('bottom'), bctype='dirichlet',
           bcvalues=0.0)

rxn = op.algorithms.GenericReaction(network=pn, pores=[70, 71])
rxn['pore.k'] = 1e-1
rxn['pore.alpha'] = 3
rxn.add_model(propname='pore.rxn_rate',
              model=op.algorithms.models.standard_kinetics,
              quantity='pore.mole_fraction',
              prefactor='pore.k', exponent='pore.alpha')
rxn.settings['rate_model'] = 'pore.rxn_rate'
alg.set_source(source=rxn)

rxn2 = op.algorithms.GenericReaction(network=pn, pores=[50, 51])
rxn2.models = rxn.models.copy()
rxn2.settings['rate_model'] = 'pore.rxn_rate'
rxn2['pore.k'] = 1e-5
rxn2['pore.alpha'] = 1
alg.set_source(source=rxn2)

alg.run()

#op.io.VTK.save(simulation=pn.simulation, phases=[water])
