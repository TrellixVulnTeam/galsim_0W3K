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

import galsim
import math
import numpy as np
import logging

# The psf extra output type builds an Image of the PSF at the same locations as the galaxies.

# The code the actually draws the PSF on a postage stamp.
def DrawPSFStamp(psf, config, base, bounds, offset, method, logger):
    """
    Draw an image using the given psf profile.

    @returns the resulting image.
    """
    if 'draw_method' in config:
        method = galsim.config.ParseValue(config,'draw_method',base,str)[0]
        if method not in ['auto', 'fft', 'phot', 'real_space', 'no_pixel', 'sb']:
            raise AttributeError("Invalid draw_method: %s"%method)
    else:
        method = 'auto'

    wcs = base['wcs'].local(base['image_pos'])
    im = galsim.ImageF(bounds, wcs=wcs)
    im = psf.drawImage(image=im, offset=offset, method=method)

    if 'signal_to_noise' in config:
        if method == 'phot':
            raise NotImplementedError(
                "signal_to_noise option not implemented for draw_method = phot")

        if 'image' in base and 'noise' in base['image']:
            noise_var = galsim.config.CalculateNoiseVar(base)
        else:
            raise AttributeError("Need to specify noise level when using psf.signal_to_noise")

        sn_target = galsim.config.ParseValue(config, 'signal_to_noise', base, float)[0]

        sn_meas = math.sqrt( np.sum(im.array**2) / noise_var )
        flux = sn_target / sn_meas
        im *= flux

    return im


# The function to call at the end of building each stamp
from .extra import ExtraOutputBuilder
class ExtraPSFBuilder(ExtraOutputBuilder):
    """Build an image that draws the PSF at the same location as each object on the main image.

    This makes the most sense when the main image consists of non-overlapping stamps, such as
    a TiledImage, since you wouldn't typically want the PSF images to overlap.  But it just
    follows whatever pattern of stamp locations the main image has.
    """
    def processStamp(self, obj_num, config, base, logger):
        # If this doesn't exist, an appropriate exception will be raised.
        psf = base['psf']['current_val']
        draw_method = galsim.config.GetCurrentValue('stamp.draw_method',base,str)
        bounds = base['current_stamp'].bounds

        # Check if we should shift the psf:
        if 'shift' in config:
            # Special: output.psf.shift = 'galaxy' means use the galaxy shift.
            if config['shift'] == 'galaxy':
                # This shift value might be in either stamp or gal.
                if 'shift' in base['stamp']:
                    shift = galsim.config.GetCurrentValue('stamp.shift',base, galsim.PositionD)
                else:
                    # This will raise an appropriate error if there is no gal.shift or stamp.shift.
                    shift = galsim.config.GetCurrentValue('gal.shift',base, galsim.PositionD)
            else:
                shift = galsim.config.ParseValue(config, 'shift', base, galsim.PositionD)[0]
            if logger:
                logger.debug('obj %d: psf shift: %s',base['obj_num'],str(shift))
            psf = psf.shift(shift)

        # Start with the offset required just due to the stamp size/shape.
        offset = base['stamp_offset']
        # Check if we should apply any additional offset:
        if 'offset' in config:
            # Special: output.psf.offset = 'galaxy' means use the same offset as in the galaxy
            #          image, which is actually in config.stamp, not config.gal.
            if config['offset'] == 'galaxy':
                offset += galsim.config.GetCurrentValue('stamp.offset',base, galsim.PositionD)
            else:
                offset += galsim.config.ParseValue(config, 'offset', base, galsim.PositionD)[0]
            if logger:
                logger.debug('obj %d: psf offset: %s',base['obj_num'],str(offset))

        psf_im = DrawPSFStamp(psf,config,base,bounds,offset,draw_method,logger)
        if 'signal_to_noise' in config:
            galsim.config.AddNoise(base,psf_im,current_var=0,logger=logger)
        self.scratch[obj_num] = psf_im

    # The function to call at the end of building each image
    def processImage(self, index, obj_nums, config, base, logger):
        image = galsim.ImageF(base['image_bounds'], wcs=base['wcs'], init_value=0.)
        # Make sure to only use the stamps for objects in this image.
        for obj_num in obj_nums:
            stamp = self.scratch[obj_num]
            b = stamp.bounds & image.getBounds()
            if logger:
                logger.debug('image %d: psf image at b = %s = %s & %s',
                             base['image_num'],b,stamp.bounds,image.getBounds())
            if b.isDefined():
                # This next line is equivalent to:
                #    image[b] += stamp[b]
                # except that this doesn't work through the proxy.  We can only call methods
                # that don't start with _.  Hence using the more verbose form here.
                image.setSubImage(b, image.subImage(b) + stamp[b])
                if logger:
                    logger.debug('obj %d: added psf image to main image',base['obj_num'])
        self.data[index] = image


# Register this as a valid extra output
from .extra import RegisterExtraOutput
RegisterExtraOutput('psf', ExtraPSFBuilder())
