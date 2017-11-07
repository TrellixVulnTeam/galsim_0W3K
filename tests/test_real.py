# Copyright (c) 2012-2017 by the GalSim developers team on GitHub
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
import numpy as np
import os
import sys

from galsim_test_helpers import *

try:
    import galsim
except ImportError:
    path, filename = os.path.split(__file__)
    sys.path.append(os.path.abspath(os.path.join(path, "..")))
    import galsim

# set up any necessary info for tests
### Note: changes to either of the tests below might require regeneration of the catalog and image
### files that are saved here.  Modify with care!!!
image_dir = './real_comparison_images'
catalog_file = 'test_catalog.fits'

ind_fake = 1 # index of mock galaxy (Gaussian) in catalog
fake_gal_fwhm = 0.7 # arcsec
fake_gal_shear1 = 0.29 # shear representing intrinsic shape component 1
fake_gal_shear2 = -0.21 # shear representing intrinsic shape component 2; note non-round, to detect
              # possible issues with x<->y or others that might not show up using circular galaxy
fake_gal_flux = 1000.0
fake_gal_orig_PSF_fwhm = 0.1 # arcsec
fake_gal_orig_PSF_shear1 = 0.0
fake_gal_orig_PSF_shear2 = -0.07

targ_pixel_scale = [0.18, 0.25] # arcsec
targ_PSF_fwhm = [0.7, 1.0] # arcsec
targ_PSF_shear1 = [-0.03, 0.0]
targ_PSF_shear2 = [0.05, -0.08]
targ_applied_shear1 = 0.06
targ_applied_shear2 = -0.04

sigma_to_fwhm = 2.0*np.sqrt(2.0*np.log(2.0)) # multiply sigma by this to get FWHM for Gaussian
fwhm_to_sigma = 1.0/sigma_to_fwhm

ind_real = 0 # index of real galaxy in catalog
shera_file = 'real_comparison_images/shera_result.fits'
shera_target_PSF_file = 'real_comparison_images/shera_target_PSF.fits'
shera_target_pixel_scale = 0.24
shera_target_flux = 1000.0

# some helper functions
def ellip_to_moments(e1, e2, sigma):
    a_val = (1.0 + e1) / (1.0 - e1)
    b_val = np.sqrt(a_val - (0.5*(1.0+a_val)*e2)**2)
    mxx = a_val * (sigma**2) / b_val
    myy = (sigma**2) / b_val
    mxy = 0.5 * e2 * (mxx + myy)
    return mxx, myy, mxy

def moments_to_ellip(mxx, myy, mxy):
    e1 = (mxx - myy) / (mxx + myy)
    e2 = 2*mxy / (mxx + myy)
    sig = (mxx*myy - mxy**2)**(0.25)
    return e1, e2, sig


@timer
def test_real_galaxy_ideal():
    """Test accuracy of various calculations with fake Gaussian RealGalaxy vs. ideal expectations"""
    # read in faked Gaussian RealGalaxy from file
    rgc = galsim.RealGalaxyCatalog(catalog_file, dir=image_dir)
    rg = galsim.RealGalaxy(rgc, index=ind_fake)
    # as a side note, make sure it behaves okay given a legit RNG and a bad RNG
    # or when trying to specify the galaxy too many ways
    rg_1 = galsim.RealGalaxy(rgc, index = ind_fake, rng = galsim.BaseDeviate(1234))
    rg_2 = galsim.RealGalaxy(rgc, random=True)
    try:
        np.testing.assert_raises(TypeError, galsim.RealGalaxy, rgc, index=ind_fake, rng='foo')
        np.testing.assert_raises(AttributeError, galsim.RealGalaxy, rgc, index=ind_fake, id=0)
        np.testing.assert_raises(AttributeError, galsim.RealGalaxy, rgc, index=ind_fake, random=True)
        np.testing.assert_raises(AttributeError, galsim.RealGalaxy, rgc, id=0, random=True)
        np.testing.assert_raises(AttributeError, galsim.RealGalaxy, rgc)
    except ImportError:
        print('The assert_raises tests require nose')
    # Different RNGs give different random galaxies.
    rg_3 = galsim.RealGalaxy(rgc, random=True, rng=galsim.BaseDeviate(12345))
    rg_4 = galsim.RealGalaxy(rgc, random=True, rng=galsim.BaseDeviate(67890))
    assert rg_3.index != rg_4.index, 'Different seeds did not give different random objects!'

    check_basic(rg, "RealGalaxy", approx_maxsb=True)
    check_basic(rg_1, "RealGalaxy", approx_maxsb=True)
    check_basic(rg_2, "RealGalaxy", approx_maxsb=True)

    do_pickle(rgc, lambda x: [ x.getGal(ind_fake), x.getPSF(ind_fake),
                               x.getNoiseProperties(ind_fake) ])
    do_pickle(rgc, lambda x: drawNoise(x.getNoise(ind_fake,rng=galsim.BaseDeviate(123))))
    do_pickle(rgc)
    do_pickle(rg, lambda x: [ x.gal_image, x.psf_image, repr(x.noise),
                              x.original_psf.flux, x.original_gal.flux, x.flux ])
    do_pickle(rg, lambda x: x.drawImage(nx=20, ny=20, scale=0.7))
    do_pickle(rg_1, lambda x: x.drawImage(nx=20, ny=20, scale=0.7))
    do_pickle(rg)
    do_pickle(rg_1)

    ## for the generation of the ideal right answer, we need to add the intrinsic shape of the
    ## galaxy and the lensing shear using the rule for addition of distortions which is ugly, but oh
    ## well:
    (d1, d2) = galsim.utilities.g1g2_to_e1e2(fake_gal_shear1, fake_gal_shear2)
    (d1app, d2app) = galsim.utilities.g1g2_to_e1e2(targ_applied_shear1, targ_applied_shear2)
    denom = 1.0 + d1*d1app + d2*d2app
    dapp_sq = d1app**2 + d2app**2
    d1tot = (d1 + d1app + d2app/dapp_sq*(1.0 - np.sqrt(1.0-dapp_sq))*(d2*d1app - d1*d2app))/denom
    d2tot = (d2 + d2app + d1app/dapp_sq*(1.0 - np.sqrt(1.0-dapp_sq))*(d1*d2app - d2*d1app))/denom

    # convolve with a range of Gaussians, with and without shear (note, for this test all the
    # original and target ePSFs are Gaussian - there's no separate pixel response so that everything
    # can be calculated analytically)
    for tps in targ_pixel_scale:
        for tpf in targ_PSF_fwhm:
            for tps1 in targ_PSF_shear1:
                for tps2 in targ_PSF_shear2:
                    print('tps,tpf,tps1,tps2 = ',tps,tpf,tps1,tps2)
                    # make target PSF
                    targ_PSF = galsim.Gaussian(fwhm = tpf).shear(g1=tps1, g2=tps2)
                    # simulate image
                    tmp_gal = rg.withFlux(fake_gal_flux).shear(g1=targ_applied_shear1,
                                                               g2=targ_applied_shear2)
                    final_tmp_gal = galsim.Convolve(targ_PSF, tmp_gal)
                    sim_image = final_tmp_gal.drawImage(scale=tps, method='no_pixel')
                    # galaxy sigma, in units of pixels on the final image
                    sigma_ideal = (fake_gal_fwhm/tps)*fwhm_to_sigma
                    # compute analytically the expected galaxy moments:
                    mxx_gal, myy_gal, mxy_gal = ellip_to_moments(d1tot, d2tot, sigma_ideal)
                    # compute analytically the expected PSF moments:
                    targ_PSF_e1, targ_PSF_e2 = galsim.utilities.g1g2_to_e1e2(tps1, tps2)
                    targ_PSF_sigma = (tpf/tps)*fwhm_to_sigma
                    mxx_PSF, myy_PSF, mxy_PSF = ellip_to_moments(
                            targ_PSF_e1, targ_PSF_e2, targ_PSF_sigma)
                    # get expected e1, e2, sigma for the PSF-convolved image
                    tot_e1, tot_e2, tot_sigma = moments_to_ellip(
                            mxx_gal+mxx_PSF, myy_gal+myy_PSF, mxy_gal+mxy_PSF)

                    # compare with images that are expected
                    expected_gaussian = galsim.Gaussian(
                            flux = fake_gal_flux, sigma = tps*tot_sigma)
                    expected_gaussian = expected_gaussian.shear(e1 = tot_e1, e2 = tot_e2)
                    expected_image = galsim.ImageD(
                            sim_image.array.shape[0], sim_image.array.shape[1])
                    expected_gaussian.drawImage(expected_image, scale=tps, method='no_pixel')
                    printval(expected_image,sim_image)
                    np.testing.assert_array_almost_equal(
                        sim_image.array, expected_image.array, decimal = 3,
                        err_msg = "Error in comparison of ideal Gaussian RealGalaxy calculations")


@timer
def test_real_galaxy_saved():
    """Test accuracy of various calculations with real RealGalaxy vs. stored SHERA result"""
    # read in real RealGalaxy from file
    # rgc = galsim.RealGalaxyCatalog(catalog_file, dir=image_dir)
    # This is an alternate way to give the directory -- as part of the catalog file name.
    full_catalog_file = os.path.join(image_dir,catalog_file)
    rgc = galsim.RealGalaxyCatalog(full_catalog_file)
    rg = galsim.RealGalaxy(rgc, index=ind_real)

    # read in expected result for some shear
    shera_image = galsim.fits.read(shera_file)
    shera_target_PSF_image = galsim.fits.read(shera_target_PSF_file)
    shera_target_PSF_image.scale = shera_target_pixel_scale

    # simulate the same galaxy with GalSim
    tmp_gal = rg.withFlux(shera_target_flux).shear(g1=targ_applied_shear1,
                                                   g2=targ_applied_shear2)
    tmp_psf = galsim.InterpolatedImage(shera_target_PSF_image)
    tmp_gal = galsim.Convolve(tmp_gal, tmp_psf)
    sim_image = tmp_gal.drawImage(scale=shera_target_pixel_scale, method='no_pixel')

    # there are centroid issues when comparing Shera vs. SBProfile outputs, so compare 2nd moments
    # instead of images
    sbp_res = sim_image.FindAdaptiveMom()
    shera_res = shera_image.FindAdaptiveMom()

    np.testing.assert_almost_equal(sbp_res.observed_shape.e1,
                                   shera_res.observed_shape.e1, 2,
                                   err_msg = "Error in comparison with SHERA result: e1")
    np.testing.assert_almost_equal(sbp_res.observed_shape.e2,
                                   shera_res.observed_shape.e2, 2,
                                   err_msg = "Error in comparison with SHERA result: e2")
    np.testing.assert_almost_equal(sbp_res.moments_sigma, shera_res.moments_sigma, 2,
                                   err_msg = "Error in comparison with SHERA result: sigma")

    check_basic(rg, "RealGalaxy", approx_maxsb=True)

    # Check picklability
    do_pickle(rgc, lambda x: [ x.getGal(ind_real), x.getPSF(ind_real),
                               x.getNoiseProperties(ind_real) ])
    do_pickle(rgc, lambda x: drawNoise(x.getNoise(ind_real,rng=galsim.BaseDeviate(123))))
    do_pickle(rg, lambda x: galsim.Convolve([x,galsim.Gaussian(sigma=1.7)]).drawImage(
                                nx=20, ny=20, scale=0.7))
    do_pickle(rgc)
    do_pickle(rg)


@timer
def test_ne():
    """ Check that inequality works as expected."""
    rgc = galsim.RealGalaxyCatalog(catalog_file, dir=image_dir)
    gsp = galsim.GSParams(folding_threshold=1.1e-3)

    gals = [galsim.RealGalaxy(rgc, index=0),
            galsim.RealGalaxy(rgc, index=1),
            galsim.RealGalaxy(rgc, index=0, x_interpolant='Linear'),
            galsim.RealGalaxy(rgc, index=0, k_interpolant='Linear'),
            galsim.RealGalaxy(rgc, index=0, flux=1.1),
            galsim.RealGalaxy(rgc, index=0, pad_factor=1.1),
            galsim.RealGalaxy(rgc, index=0, noise_pad_size=5.0),
            galsim.RealGalaxy(rgc, index=0, gsparams=gsp)]
    all_obj_diff(gals)
    for gal in gals:
        do_pickle(gal)

@timer
def test_noise():
    """Check consistency of noise-related routines."""
    # The RealGalaxyCatalog.getNoise() routine should be tested to ensure consistency of results
    # with the getNoiseProperties() routine.  The former cannot be used across processes, but might
    # be used when running on a single processor, so we should make sure it gives proper output.
    # Need to use a real RealGalaxyCatalog with non-trivial noise correlation function.
    real_gal_dir = os.path.join('..','examples','data')
    real_gal_cat = 'real_galaxy_catalog_23.5_example.fits'
    real_cat = galsim.RealGalaxyCatalog(
        dir=real_gal_dir, file_name=real_gal_cat, preload=True)

    test_seed=987654
    test_index = 17
    cf_1 = real_cat.getNoise(test_index, rng=galsim.BaseDeviate(test_seed))
    im_2, pix_scale_2, var_2 = real_cat.getNoiseProperties(test_index)
    # Check the variance:
    var_1 = cf_1.getVariance()
    assert var_1==var_2,'Inconsistent noise variance from getNoise and getNoiseProperties'
    # Check the image:
    ii = galsim.InterpolatedImage(im_2, normalization='sb', calculate_stepk=False,
                                  calculate_maxk=False, x_interpolant='linear')
    cf_2 = galsim.correlatednoise._BaseCorrelatedNoise(galsim.BaseDeviate(test_seed), ii, im_2.wcs)
    cf_2 = cf_2.withVariance(var_2)
    assert cf_1==cf_2,'Inconsistent noise properties from getNoise and getNoiseProperties'

if __name__ == "__main__":
    test_real_galaxy_ideal()
    test_real_galaxy_saved()
    test_ne()
    test_noise()
