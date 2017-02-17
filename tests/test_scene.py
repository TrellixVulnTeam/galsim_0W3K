# Copyright (c) 2012-2016 by the GalSim developers team on GitHub
# https://github.com/GalSim-developers
#
# This file is part of GalSim: The modular galaxy image simulation toolkit.
# https://github.com/GalSim-developers/GalSim
#
# GalSim is free software: redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions, and the disclaimer given in the accompanying LICENSE
#    file.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions, and the disclaimer given in the documentation
#    and/or other materials provided with the distribution.
#

from __future__ import print_function
import os
import numpy as np
from galsim_test_helpers import *
import sys

try:
    import galsim
except ImportError:
    path, filename = os.path.split(__file__)
    sys.path.append(os.path.abspath(os.path.join(path, "..")))
    import galsim

path, filename = os.path.split(__file__)
datapath = os.path.abspath(os.path.join(path, "../examples/data/"))


@timer
def test_cosmos_basic():
    """Check some basic functionality of the COSMOSCatalog class."""
    # Note, there's not much here yet.   Could try to think of other tests that are more
    # interesting.

    # Initialize a COSMOSCatalog with all defaults.
    cat = galsim.COSMOSCatalog(file_name='real_galaxy_catalog_23.5_example.fits',
                               dir=datapath)
    # Initialize one that doesn't exclude failures.  It should be >= the previous one in length.
    cat2 = galsim.COSMOSCatalog(file_name='real_galaxy_catalog_23.5_example.fits',
                               dir=datapath, exclusion_level='none')
    assert cat2.nobjects>=cat.nobjects

    # Check for reasonable exceptions when initializing.
    try:
        # Can't find data (wrong directory).
        np.testing.assert_raises(IOError, galsim.COSMOSCatalog,
                                 file_name='real_galaxy_catalog_23.5_example.fits')
    except ImportError:
        print('The assert_raises tests require nose')

    # Try making galaxies
    gal_real = cat2.makeGalaxy(index=0,gal_type='real',chromatic=False)
    if not isinstance(gal_real, galsim.RealGalaxy):
        raise TypeError("COSMOS Catalog makeGalaxy routine does not return an instance of "
                        "'galsim.RealGalaxy'")

    gal_param = cat.makeGalaxy(index=10,gal_type='parametric',chromatic=True)
    if not isinstance(gal_param, galsim.ChromaticObject):
        raise TypeError("COSMOS Catalog makeGalaxy routine does not return an instance of "
                        "'galsim.ChromaticObject' for parametric galaxies")

    gal_real_list = cat.makeGalaxy(index=[3,6],gal_type='real',chromatic=False)
    for gal_real in gal_real_list:
        if not isinstance(gal_real, galsim.RealGalaxy):
            raise TypeError("COSMOS Catalog makeGalaxy routine does not return a list of instances "
                            "of 'galsim.RealGalaxy'")

    gal_param_list = cat.makeGalaxy(index=[4,7],gal_type='parametric',chromatic=False)
    for gal_param in gal_param_list:
        if not isinstance(gal_param, galsim.GSObject):
            raise TypeError("COSMOS Catalog makeGalaxy routine does not return a list of instances "
                            "of 'galsim.GSObect'")

    # Check for parametric catalog
    cat_param = galsim.COSMOSCatalog(file_name='real_galaxy_catalog_23.5_example_fits.fits',
                                     dir=datapath, use_real=False)

    # Try making galaxies
    gal = cat_param.makeGalaxy(index=1)
    if not isinstance(gal, galsim.GSObject):
        raise TypeError("COSMOS Catalog makeGalaxy routine does not return an instance of "
                        "'galsim.GSObject when loaded from a fits file.")

    gal_list = cat_param.makeGalaxy(index=[2,3])
    for gal in gal_list:
        if not isinstance(gal, galsim.GSObject):
            raise TypeError("COSMOS Catalog makeGalaxy routine does not return a list of instances "
                            "of 'galsim.GSObject when loaded from a fits file.")


@timer
def test_cosmos_fluxnorm():
    """Check for flux normalization properties of COSMOSCatalog class."""
    # Check that if we make a RealGalaxy catalog, and a COSMOSCatalog, and draw the real object, the
    # fluxes should match very well.  These correspond to 1s exposures.
    test_ind = 54
    rand_seed = 12345
    cat = galsim.COSMOSCatalog(file_name='real_galaxy_catalog_23.5_example.fits',
                               dir=datapath, exclusion_level='none')
    rgc = galsim.RealGalaxyCatalog(file_name='real_galaxy_catalog_23.5_example.fits',
                                   dir=datapath)
    final_psf = galsim.Airy(diam=1.2, lam=800.) # PSF twice as big as HST in F814W.
    gal1 = cat.makeGalaxy(test_ind, gal_type='real', rng=galsim.BaseDeviate(rand_seed))
    gal2 = galsim.RealGalaxy(rgc, index=test_ind, rng=galsim.BaseDeviate(rand_seed))
    gal1 = galsim.Convolve(gal1, final_psf)
    gal2 = galsim.Convolve(gal2, final_psf)
    im1 = gal1.drawImage(scale=0.05)
    im2 = gal2.drawImage(scale=0.05)

    # Then check that if we draw a parametric representation that is achromatic, that the flux
    # matches reasonably well (won't be exact because model isn't perfect).
    gal1_param = cat.makeGalaxy(test_ind, gal_type='parametric', chromatic=False)
    gal1_param_final = galsim.Convolve(gal1_param, final_psf)
    im1_param = gal1_param_final.drawImage(scale=0.05)

    # Then check the same for a chromatic parametric representation that is drawn into the same
    # band.
    bp_file = os.path.join(galsim.meta_data.share_dir, 'wfc_F814W.dat.gz')
    bandpass = galsim.Bandpass(bp_file, wave_type='ang').thin().withZeropoint(25.94)#34.19)
    gal1_chrom = cat.makeGalaxy(test_ind, gal_type='parametric', chromatic=True)
    gal1_chrom = galsim.Convolve(gal1_chrom, final_psf)
    im1_chrom = gal1_chrom.drawImage(bandpass, scale=0.05)

    ref_val = [im1.array.sum(), im1.array.sum(), im1.array.sum()]
    test_val = [im2.array.sum(), im1_param.array.sum(), im1_chrom.array.sum()]
    np.testing.assert_allclose(ref_val, test_val, rtol=0.1,
                               err_msg='Flux normalization problem in COSMOS galaxies')

    # Finally, check that the original COSMOS info is stored properly after transformations, for
    # both Sersic galaxies (like galaxy 0 in the catalog) and the one that is gal1_param above.
    gal0_param = cat.makeGalaxy(0, gal_type='parametric', chromatic=False)
    assert hasattr(gal0_param.shear(g1=0.05).original, 'index'), \
        'Sersic galaxy does not retain index information after transformation'
    assert hasattr(gal1_param.shear(g1=0.05).original, 'index'), \
        'Bulge+disk galaxy does not retain index information after transformation'


if __name__ == "__main__":
    test_cosmos_basic()
    test_cosmos_fluxnorm()
