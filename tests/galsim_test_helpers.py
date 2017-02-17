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
import numpy as np
import os
import sys

try:
    import galsim
except ImportError:
    path, filename = os.path.split(__file__)
    sys.path.append(os.path.abspath(os.path.join(path, "..")))
    import galsim


# This file has some helper functions that are used by tests from multiple files to help
# avoid code duplication.

def gsobject_compare(obj1, obj2, conv=None, decimal=10):
    """Helper function to check that two GSObjects are equivalent
    """
    if conv:
        obj1 = galsim.Convolve([obj1,conv])
        obj2 = galsim.Convolve([obj2,conv])

    im1 = galsim.ImageD(16,16)
    im2 = galsim.ImageD(16,16)
    if isinstance(obj1,galsim.correlatednoise._BaseCorrelatedNoise):
        obj1.drawImage(scale=0.2, image=im1)
        obj2.drawImage(scale=0.2, image=im2)
    else:
        obj1.drawImage(scale=0.2, image=im1, method='no_pixel')
        obj2.drawImage(scale=0.2, image=im2, method='no_pixel')
    np.testing.assert_array_almost_equal(im1.array, im2.array, decimal=decimal)


def printval(image1, image2):
    print("New, saved array sizes: ", np.shape(image1.array), np.shape(image2.array))
    print("Sum of values: ", np.sum(image1.array), np.sum(image2.array))
    print("Minimum image value: ", np.min(image1.array), np.min(image2.array))
    print("Maximum image value: ", np.max(image1.array), np.max(image2.array))
    print("Peak location: ", image1.array.argmax(), image2.array.argmax())
    print("Moments Mx, My, Mxx, Myy, Mxy for new array: ")
    getmoments(image1)
    print("Moments Mx, My, Mxx, Myy, Mxy for saved array: ")
    getmoments(image2)
    #xcen = image2.array.shape[0]/2
    #ycen = image2.array.shape[1]/2
    #print("new image.center = ",image1.array[xcen-3:xcen+4,ycen-3:ycen+4])
    #print("saved image.center = ",image2.array[xcen-3:xcen+4,ycen-3:ycen+4])

    if False:
        import matplotlib.pylab as plt
        ax1 = plt.subplot(121)
        ax2 = plt.subplot(122)
        ax1.imshow(image1.array)
        ax2.imshow(image2.array)
        plt.show()

def getmoments(image):
    #print('shape = ',image.array.shape)
    #print('bounds = ',image.bounds)
    a = image.array.astype(float) # Use float for better accuracy calculations.
                                  # This matters more for numpy version <= 1.7
    xgrid, ygrid = np.meshgrid(np.arange(image.array.shape[1]) + image.getXMin(),
                               np.arange(image.array.shape[0]) + image.getYMin())
    mx = np.sum(xgrid * a) / np.sum(a)
    my = np.sum(ygrid * a) / np.sum(a)
    mxx = np.sum(((xgrid-mx)**2) * a) / np.sum(a)
    myy = np.sum(((ygrid-my)**2) * a) / np.sum(a)
    mxy = np.sum((xgrid-mx) * (ygrid-my) * a) / np.sum(a)

    print('      {0:<15.8g}  {1:<15.8g}  {2:<15.8g}  {3:<15.8g}  {4:<15.8g}'.format(
            mx-image.getXMin(), my-image.getYMin(), mxx, myy, mxy))
    return mx, my, mxx, myy, mxy

def convertToShear(e1,e2):
    # Convert a distortion (e1,e2) to a shear (g1,g2)
    import math
    e = math.sqrt(e1*e1 + e2*e2)
    g = math.tanh( 0.5 * math.atanh(e) )
    g1 = e1 * (g/e)
    g2 = e2 * (g/e)
    return (g1,g2)

def do_shoot(prof, img, name):
    # For photon shooting, we calculate the number of photons to use based on the target
    # accuracy we are shooting for.  (Pun intended.)
    # For each pixel,
    # uncertainty = sqrt(N_pix) * flux_photon = sqrt(N_tot * flux_pix / flux_tot) * flux_tot / N_tot
    #             = sqrt(flux_pix) * sqrt(flux_tot) / sqrt(N_tot)
    # This is largest for the brightest pixel.  So we use:
    # N = flux_max * flux_tot / photon_shoot_accuracy^2
    photon_shoot_accuracy = 2.e-3
    # The number of decimal places at which to test the photon shooting
    photon_decimal_test = 2

    test_flux = 1.8

    print('Start do_shoot')
    # Test photon shooting for a particular profile (given as prof).
    prof.drawImage(img)
    flux_max = img.array.max()
    print('prof.getFlux = ',prof.getFlux())
    print('flux_max = ',flux_max)
    flux_tot = img.array.sum()
    print('flux_tot = ',flux_tot)
    if flux_max > 1.:
        # Since the number of photons required for a given accuracy level (in terms of
        # number of decimal places), we rescale the comparison by the flux of the
        # brightest pixel.
        prof /= flux_max
        img /= flux_max
        # The formula for number of photons needed is:
        # nphot = flux_max * flux_tot / photon_shoot_accuracy**2
        # But since we rescaled the image by 1/flux_max, it becomes
        nphot = flux_tot / flux_max / photon_shoot_accuracy**2
    elif flux_max < 0.1:
        # If the max is very small, at least bring it up to 0.1, so we are testing something.
        scale = 0.1 / flux_max;
        print('scale = ',scale)
        prof *= scale
        img *= scale
        nphot = flux_max * flux_tot * scale * scale / photon_shoot_accuracy**2
    else:
        nphot = flux_max * flux_tot / photon_shoot_accuracy**2
    print('prof.getFlux => ',prof.getFlux())
    print('img.sum => ',img.array.sum())
    print('img.max => ',img.array.max())
    print('nphot = ',nphot)
    img2 = img.copy()

    # Use a deterministic random number generator so we don't fail tests because of rare flukes
    # in the random numbers.
    rng = galsim.UniformDeviate(12345)

    prof.drawImage(img2, n_photons=nphot, poisson_flux=False, rng=rng, method='phot')
    print('img2.sum => ',img2.array.sum())
    #printval(img2,img)
    np.testing.assert_array_almost_equal(
            img2.array, img.array, photon_decimal_test,
            err_msg="Photon shooting for %s disagrees with expected result"%name)

    # Test normalization
    dx = img.scale
    # Test with a large image to make sure we capture enough of the flux
    # even for slow convergers like Airy (which needs a _very_ large image) or Sersic.
    if 'Airy' in name:
        img = galsim.ImageD(2048,2048, scale=dx)
    elif 'Sersic' in name or 'DeVauc' in name or 'Spergel' in name:
        img = galsim.ImageD(512,512, scale=dx)
    else:
        img = galsim.ImageD(128,128, scale=dx)
    prof = prof.withFlux(test_flux)
    prof.drawImage(img)
    print('img.sum = ',img.array.sum(),'  cf. ',test_flux)
    np.testing.assert_almost_equal(img.array.sum(), test_flux, 4,
            err_msg="Flux normalization for %s disagrees with expected result"%name)

    scale = test_flux / flux_tot # from above
    nphot *= scale * scale
    print('nphot -> ',nphot)
    if 'InterpolatedImage' in name:
        nphot *= 10
        print('nphot -> ',nphot)
    prof.drawImage(img, n_photons=nphot, poisson_flux=False, rng=rng, method='phot')
    print('img.sum = ',img.array.sum(),'  cf. ',test_flux)
    np.testing.assert_almost_equal(img.array.sum(), test_flux, photon_decimal_test,
            err_msg="Photon shooting normalization for %s disagrees with expected result"%name)


def do_kvalue(prof, im1, name):
    """Test that the k-space values are consistent with the real-space values by drawing the
    profile directly (without any convolution, so using fillXValues) and convolved by a tiny
    Gaussian (effectively a delta function).
    """

    prof.drawImage(im1, method='no_pixel')

    delta = galsim.Gaussian(sigma = 1.e-8)
    conv = galsim.Convolve([prof,delta])
    im2 = conv.drawImage(im1.copy(), method='no_pixel')
    printval(im1,im2)
    np.testing.assert_array_almost_equal(
            im2.array, im1.array, 3,
            err_msg = name +
            " convolved with a delta function is inconsistent with real-space image.")

def radial_integrate(prof, minr, maxr):
    """A simple helper that calculates int 2pi r f(r) dr, from rmin to rmax
       for an axially symmetric profile.
    """
    assert prof.isAxisymmetric()
    # In this tight loop, it is worth optimizing away the parse_pos_args step.
    # It makes a rather significant difference in the running time of this function.
    # (I.e., use prof.SBProfile.xValue() instead of prof.xValue() )
    f = lambda r: 2 * np.pi * r * prof.SBProfile.xValue(galsim.PositionD(r,0))
    return galsim.integ.int1d(f, minr, maxr)

# A short helper function to test pickling of noise objects
def drawNoise(noise):
    im = galsim.ImageD(10,10)
    im.addNoise(noise)
    return im.array.astype(np.float32).tolist()


def do_pickle(obj1, func = lambda x : x, irreprable=False):
    """Check that the object is picklable.  Also that it has basic == and != functionality.
    """
    from numbers import Integral, Real, Complex
    try:
        import cPickle as pickle
    except:
        import pickle
    import copy
    # In case the repr uses these:
    from numpy import array, int16, int32, float32, float64, ndarray
    try:
        import astropy.io.fits
        from distutils.version import LooseVersion
        if LooseVersion(astropy.__version__) < LooseVersion('1.0.6'):
            irreprable = True
    except:
        import pyfits
    print('Try pickling ',obj1)

    #print('pickled obj1 = ',pickle.dumps(obj1))
    obj2 = pickle.loads(pickle.dumps(obj1))
    assert obj2 is not obj1
    #print('obj1 = ',repr(obj1))
    #print('obj2 = ',repr(obj2))
    f1 = func(obj1)
    f2 = func(obj2)
    #print('func(obj1) = ',repr(f1))
    #print('func(obj2) = ',repr(f2))
    assert f1 == f2

    # Test the hash values are equal for two equivalent objects.
    from collections import Hashable
    if isinstance(obj1, Hashable):
        #print('hash = ',hash(obj1),hash(obj2))
        assert hash(obj1) == hash(obj2)

    obj3 = copy.copy(obj1)
    assert obj3 is not obj1
    random = hasattr(obj1, 'rng') or isinstance(obj1, galsim.BaseDeviate) or 'rng' in repr(obj1)
    if not random:  # Things with an rng attribute won't be identical on copy.
        f3 = func(obj3)
        assert f3 == f1
    elif isinstance(obj1, galsim.BaseDeviate):
        f1 = func(obj1)  # But BaseDeviates will be ok.  Just need to remake f1.
        f3 = func(obj3)
        assert f3 == f1

    obj4 = copy.deepcopy(obj1)
    assert obj4 is not obj1
    f4 = func(obj4)
    if random: f1 = func(obj1)
    #print('func(obj1) = ',repr(f1))
    #print('func(obj4) = ',repr(f4))
    assert f4 == f1  # But everything should be identical with deepcopy.

    # Also test that the repr is an accurate representation of the object.
    # The gold standard is that eval(repr(obj)) == obj.  So check that here as well.
    # A few objects we don't expect to work this way in GalSim, either because their repr strings
    # are truncated or because they include floating point numbers with truncated precision.  For
    # these, we just exit here.
    if irreprable: return

    try:
        # It turns out that random deviates will still be successfully constructed even with a
        # truncated repr string.  They will just be the 'wrong' random deviates.  So look for that
        # here and just raise an exception to skip this test and get out of the try block.
        if random:
            raise TypeError
        # A further complication is that the default numpy print options do not have sufficient
        # precision for the eval string to exactly reproduce the original object.  So we temporarily
        # bump up the numpy print precision.
        with galsim.utilities.printoptions(precision=18):
            #print('repr = ',repr(obj1))
            obj5 = eval(repr(obj1))
    except:
        pass
    else:
        #print('obj1 = ',repr(obj1))
        #print('obj5 = ',repr(obj5))
        f5 = func(obj5)
        if random: f1 = func(obj1)
        #print('func(obj1) = ',repr(f1))
        #print('func(obj5) = ',repr(f5))
        assert f5 == f1, "func(obj1) = %r\nfunc(obj5) = %r"%(f1, f5)

    # Try perturbing obj1 pickling arguments and verify that inequality results.
    # Generally, only objects pickled with __getinitargs__, i.e. old-style classes, reveal
    # anything about what construction attributes may be important to check for assessing equality.
    # (Even in this case, it's possible that an argument supplied by __getinitargs__ isn't actually
    # important for assessing equality, though this doesn't appear to be the case for GalSim so
    # far.)  Our strategy below is to loop through all arguments returned by __getinitargs__ and
    # attempt to perturb them a bit after inferring their type, and checking that the object
    # constructed with the perturbed argument list then compares inequally to the original object.

    # import sys
    try:
        args = obj1.__getinitargs__()
    except:
        pass
    else:
        classname = type(obj1).__name__
        for i in range(len(args)):
            #print("Attempting arg {0}\n".format(i))
            newargs = list(args)
            if isinstance(args[i], bool):
                newargs[i] = not args[i]
            elif isinstance(args[i], Integral):
                newargs[i] = args[i] + 2
            elif isinstance(args[i], Real):
                newargs[i] = args[i] * 1.01 + 0.01
            elif isinstance(args[i], Complex):
                newargs[i] = args[i] * (1.01 + 0.01j) + (0.99 - 0.01j)
            elif isinstance(args[i], ndarray):
                newargs[i] = args[i] * 1.01 + 0.01
            elif isinstance(args[i], galsim.GSParams):
                newargs[i] = galsim.GSParams(folding_threshold=5.1e-3, maxk_threshold=1.1e-3)
            elif args[i] is None:
                continue
            else:
                #print("Unknown type: {0}\n".format(args[i]))
                continue
            with galsim.utilities.printoptions(precision=18, threshold=1e6):
                try:
                    obj6 = eval('galsim.' + classname + repr(tuple(newargs)))
                except:
                    try:
                        obj6 = eval('galsim._galsim.' + classname + repr(tuple(newargs)))
                    except:
                        raise TypeError("{0} not `eval`able!".format(
                                classname + repr(tuple(newargs))))
                else:
                    assert obj1 != obj6
                    #print("SUCCESS\n")


def all_obj_diff(objs):
    """ Helper function that verifies that each element in `objs` is unique and, if hashable,
    produces a unique hash."""

    from collections import Hashable
    # Check that all objects are unique.
    # Would like to use `assert len(objs) == len(set(objs))` here, but this requires that the
    # elements of objs are hashable (and that they have unique hashes!, which is what we're trying
    # to test!.  So instead, we just loop over all combinations.
    for i, obji in enumerate(objs):
        # Could probably start the next loop at `i+1`, but we start at 0 for completeness
        # (and to verify a != b implies b != a)
        for j, objj in enumerate(objs):
            if i == j:
                continue
            assert obji != objj, ("Found equivalent objects {0} == {1} at indices {2} and {3}"
                                  .format(obji, objj, i, j))

    # Now check that all hashes are unique (if the items are hashable).
    if not isinstance(objs[0], Hashable):
        return
    hashes = [hash(obj) for obj in objs]
    try:
        assert len(hashes) == len(set(hashes))
    except AssertionError as e:
        try:
            # Only valid in 2.7, but only needed if we have an error to provide more information.
            from collections import Counter
        except ImportError:
            raise e
        for k, v in Counter(hashes).items():
            if v <= 1:
                continue
            print("Found multiple equivalent object hashes:")
            for i, obj in enumerate(objs):
                if hash(obj) == k:
                    print(i, repr(obj))
        raise e


def funcname():
    import inspect
    return inspect.stack()[1][3]


def timer(f):
    import functools

    @functools.wraps(f)
    def f2(*args, **kwargs):
        import time
        import inspect
        t0 = time.time()
        result = f(*args, **kwargs)
        t1 = time.time()
        fname = inspect.stack()[1][4][0].split('(')[0].strip()
        print('time for %s = %.2f' % (fname, t1-t0))
        return result
    return f2
