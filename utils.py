# Utility Functions ---------------------------------------------------------
import nipype.pipeline.engine as pe
import nipype.interfaces.io as nio          # input/output
import nipype.interfaces.utility as util
import nipype.interfaces.fsl as fsl

def pick_wm_0(probability_maps):

    import sys
    import os


    if(isinstance(probability_maps, list)):

        if(len(probability_maps) == 1):
            probability_maps = probability_maps[0]
        for file in probability_maps:
            print file
            if file.endswith("prob_0.nii.gz"):

                return file
    return None


def pick_wm_1(probability_maps):

    import sys
    import os
    if(isinstance(probability_maps, list)):

        if(len(probability_maps) == 1):
            probability_maps = probability_maps[0]
        for file in probability_maps:
            print file
            if file.endswith("prob_2.nii.gz"):

                return file
    return None