#!/usr/bin/env python2
#
# Copyright (C) 2012 Tuomas Jormola <tj@solitudo.net>
#
# Licensed under the terms of the GNU General Public License 2.0
# Full license text is available at http://www.gnu.org/licenses/gpl-2.0.html
#
# Generate @ocram's picons sets.
#
# Required dependencies:
#
# pgmagick http://bitbucket.org/hhatto/pgmagick
# python-progressbar http://code.google.com/p/python-progressbar/
#
# On Debian/Ubuntu based operating systems these can be installed by
# installing the packages
#
# python-pgmagick python-progressbar
#


import os, os.path
import re
import sys
import math
import argparse
from pgmagick import Image, Geometry, GravityType, CompositeOperator
from progressbar import ProgressBar, SimpleProgress, Percentage, ETA

LOGO_DIR_DEFAULT = './picons'
BACKGROUND_DIR_DEFAULT = './backgrounds'
OUT_DIR_DEFAULT = './ocram-picons'
FORCE_DEFAULT = False

class PIconImageBase(object):
    image = None

    def save(self, filename):
        self.image.write(filename)

    def close(self):
        self.image = None

class PIconImageFromFile(PIconImageBase):
    filename = None
    def __init__(self, filename):
        self.filename = filename

    def open(self):
        if self.image != None:
            return
        self.image = Image(self.filename)

class PIconImageFromImage(PIconImageBase):
    def __init__(self, image):
        self.image = image

class PIcon(PIconImageFromImage):
    pass

class PIconLogo(PIconImageFromFile):
    pass

class PIconBackground(PIconImageFromFile):
    # This magic number comes from the specification at
    # https://github.com/ocram/picons/blob/35d2094d277b5c59818f64d5dbeb66a5076a6c58/README.md
    BORDER_RATIO = 15.0/256

    type = None
    variation = None

    def __init__(self, filename, type, variation):
        super(PIconBackground, self).__init__(filename)
        self.type = type
        self.variation = variation

    # resize and merge an overlay item over the background image
    def merge_overlay(self, overlay):
        self.open()
        overlay.open()
        background_image = Image(self.image)
        # remove any transparent areas around the logo
        overlay_image = Image(Geometry(overlay.image.size().width() + 2, overlay.image.size().height() + 2), 'transparent')
        overlay_image.composite(overlay.image, GravityType.CenterGravity, CompositeOperator.OverCompositeOp)
        overlay_image.trim()
        border_width = int(math.ceil(background_image.size().width() * PIconBackground.BORDER_RATIO))
        overlay_image.zoom(Geometry(background_image.size().width() - (border_width * 2), background_image.size().height() - (border_width * 2)))
        # we need to calculate exact position since we get 1-pixel error
        # if the height of the logo is odd and using GravityType.CenterGravity
        if overlay_image.size().width() + (2 * border_width) == background_image.size().width():
            x = border_width
            y = int(math.ceil((background_image.size().height() / 2.0) - (overlay_image.size().height() / 2.0)))
        else:
            x = int(math.ceil((background_image.size().width() / 2.0) - (overlay_image.size().width() / 2.0)))
            y = border_width
        background_image.composite(overlay_image, x, y, CompositeOperator.OverCompositeOp)
        return PIcon(background_image)

class PIcons():
    def __init__(self, logo_dir = LOGO_DIR_DEFAULT,
            background_dir = BACKGROUND_DIR_DEFAULT,
            out_dir = OUT_DIR_DEFAULT,
            requested_background_types = None,
            requested_background_variations = None,
            requested_logos = None,
            force = FORCE_DEFAULT):

        self.force = force
        # check output directory
        if not os.path.isdir(out_dir):
            try:
                os.makedirs(out_dir)
            except EnvironmentError as err:
                sys.exit('ERROR: Failed to create output directory %s: %s' % (out_dir, os.strerror(err.errno)))
        if not os.access(out_dir, os.W_OK):
            sys.exit('ERROR: Output directory %s not writable' % out_dir)
        self.out_dir = out_dir

        # check background directory
        if not os.path.isdir(background_dir):
            sys.exit('ERROR: Background directory %s not found' % background_dir)
        if not os.access(background_dir, os.R_OK):
            sys.exit('ERROR: Background directory %s not readable' % background_dir)

        # handle background types and variations
        def flatten(a):
            if a != None:
                return set([i for s in map(lambda x: re.split('\s*,\s*', x), a) for i in s])
            else:
                return []
        def add_png(f):
            if not f.endswith('.png'):
                f += '.png'
            return f
        def remove_png(f):
            return re.sub('\.png$', '', f)
        requested_background_types = flatten(requested_background_types)
        requested_background_types = flatten(requested_background_types)
        requested_background_variations = map(remove_png, flatten(requested_background_variations))
        background_types = []
        # find background types under background directory
        detected_background_types = []
        for background_dir_file in os.listdir(background_dir):
            if not os.path.isdir(os.path.join(background_dir, background_dir_file)):
                continue
            detected_background_types.append(background_dir_file)
        if len(requested_background_types) == 0:
            background_types = detected_background_types
        else:
            # verify given background types
            for requested_background_type in requested_background_types:
                if requested_background_type in detected_background_types and os.access(os.path.join(background_dir, requested_background_type), os.R_OK):
                    background_types.append(requested_background_type)
                else:
                    print >> sys.stderr, 'WARNING: Background type %s not found or readable, ignoring' % requested_background_type
        if len(background_types) == 0:
            sys.exit('ERROR: No valid background types found')
        # build backgrounds from types and variations for each type
        background_data = {}
        for background_type in background_types:
            detected_background_variations = map(remove_png, filter(lambda f: os.path.isfile(os.path.join(background_dir, background_type, f)) and f.endswith('.png'), os.listdir(os.path.join(background_dir, background_type))))
            background_variations = []
            if len(requested_background_variations) == 0:
                background_variations = detected_background_variations
            else:
                # verify given background variations for this background type
                for requested_background_variation in requested_background_variations:
                    if requested_background_variation in detected_background_variations and os.access(add_png(os.path.join(background_dir, background_type, requested_background_variation)), os.R_OK):
                        background_variations.append(requested_background_variation)
                    else:
                        print >> sys.stderr, 'WARNING: Background variation %s for background type %s not found for readable, ignoring' % (requested_background_variation, background_type)
            if len(background_variations) == 0:
                print >> sys.stderr, 'WARNING: No valid background variations found for background type %s, ignoring' % background_type
                continue
            background_data[background_type] = background_variations
        if len(background_data) == 0:
            sys.exit('ERROR: No valid backgrounds found')
        self.backgrounds = []
        for background_type in background_data.iterkeys():
            for background_variation in background_data[background_type]:
                background_file = add_png(os.path.join(background_dir, background_type, background_variation))
                self.backgrounds.append(PIconBackground(background_file, background_type, background_variation))

        # handle logos

        # check logo directory
        if not os.path.isdir(logo_dir):
            sys.exit('ERROR: Logo directory %s not found' % logo_dir)
        if not os.access(background_dir, os.R_OK):
            sys.exit('ERROR: Logo directory %s not readable' % logo_dir)

        requested_logos = map(add_png, flatten(requested_logos))
        logos = []
        # find logos under logo directory
        detected_logos = filter(lambda f: not os.path.islink(os.path.join(logo_dir, f)) and os.path.isfile(os.path.join(logo_dir, f)) and f.endswith('.png'), os.listdir(logo_dir))
        if len(requested_logos) == 0:
            logos = detected_logos
        else:
            # verify given logos
            for requested_logo in requested_logos:
                if requested_logo in detected_logos and os.access(os.path.join(logo_dir, requested_logo), os.R_OK):
                    logos.append(requested_logo)
                else:
                    print >> sys.stderr, 'WARNING: Logo %s not found or readable, ignoring' % requested_logo
        if len(logos) == 0:
            sys.exit('ERROR: No valid logos found')
        self.logos = []
        for logo in logos:
            self.logos.append(PIconLogo(os.path.join(logo_dir, logo)))

    def generate(self):
        def format_background(background):
            return 'picons-{:s}-{:s}'.format(background.type.lower(), background.variation)

        widgets = ['Processed picon ', SimpleProgress(), ' ', Percentage(), ' ', ETA()]
        pbar = ProgressBar(widgets = widgets, maxval = len(self.backgrounds) * len(self.logos))
        pbar.start()
        i = 0
        # iterate over all the backgrounds and logos and
        # generate picons
        for background in self.backgrounds:
            for logo in self.logos:
                picon_dir = os.path.join(self.out_dir, format_background(background))
                picon_file = os.path.join(picon_dir, os.path.basename(logo.filename))
                # skip creation of logo it exists and the source logo is older
                # than the picon
                if not self.force and os.path.isfile(picon_file) and os.path.getmtime(picon_file) > os.path.getmtime(logo.filename):
                    i += 1
                    pbar.update(i)
                    continue
                if not os.path.isdir(picon_dir):
                    try:
                        os.makedirs(picon_dir)
                    except EnvironmentError as err:
                        sys.exit('ERROR: Failed to create picons directory %s: %s' % (picon_dir, os.strerror(err.errno)))
                try:
                    picon = background.merge_overlay(logo)
                except EnvironmentError as err:
                    print >> sys.stderr, 'WARNING: Failed to create picon %s, skipping!' % picon_file
                try:
                    picon.save(picon_file)
                    picon.close()
                    logo.close()
                except EnvironmentError as err:
                    print >> sys.stderr, 'WARNING: Failed to save picon %s, skipping!' % picon_file
                i += 1
                pbar.update(i)
            background.close()
        pbar.finish()

def main():
    # Define commandline arguments
    parser = argparse.ArgumentParser(description="Generate final set of ocram's picons from the channel logos and backgrounds.")
    parser.add_argument('-d', '--logodir',
        metavar = 'logo dir',
        default = LOGO_DIR_DEFAULT,
        help = "directory containing source logos for ocram's picons")
    parser.add_argument('-b', '--backgrounddir',
        metavar = 'background dir',
        default = BACKGROUND_DIR_DEFAULT,
        help = "directory containing the background types sub directories")
    parser.add_argument('-o', '--outdir',
        metavar = 'output dir',
        default = OUT_DIR_DEFAULT,
        help = "base directory for writing the finalized ocram's picons")
    parser.add_argument('-t', '--backgroundtypes',
        action = 'append',
        metavar = 'type1,type2,...',
        help = "process only these background types separated by commas, these map to the subdirectories under the background directory, all by default")
    parser.add_argument('-v', '--backgroundvariations',
        action = 'append',
        metavar = 'variation1,variation2,...',
        help = "process only these background variations separated by commas, these map to the .png files under the background types directories, all by default")
    parser.add_argument('-l', '--logos',
        action = 'append',
        metavar = 'logo1,logo2,...',
        help = "process only these logos separated by commas, these map to the .png files under the logo dir, all by default")
    parser.add_argument('-f', '--force',
        action = 'store_true',
        default = FORCE_DEFAULT,
        help = "force creation of the picons even a picon already exists and the corresponding source logo is older than the picon")

    argsDict = vars(parser.parse_args())

    picons = PIcons(logo_dir = argsDict['logodir'],
        background_dir = argsDict['backgrounddir'],
        out_dir = argsDict['outdir'],
        requested_background_types = argsDict['backgroundtypes'],
        requested_background_variations = argsDict['backgroundvariations'],
        requested_logos = argsDict['logos'],
        force = argsDict['force'])
    picons.generate()

if __name__ == '__main__':
    sys.exit(main())
