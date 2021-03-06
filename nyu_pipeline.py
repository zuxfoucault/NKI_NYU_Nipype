import nipype.interfaces.io as nio
import nipype.pipeline.engine as pe 
from base import (create_anat_preproc, create_func_preproc,
                    create_reg_preproc, create_seg_preproc)
from base_nuisance import create_nuisance_preproc
from base_stats import create_stats_preproc
import re
import os
import glob
import e_afni

from nipype.interfaces.utility import IdentityInterface
from nipype.interfaces import fsl

subject_paths = glob.glob('/home/data/Originals/NYU_TRT/NYU_TRT_session1/sub*')
subject_ids = [re.search('(sub\w+)',sp).group(1) for sp in subject_paths]
session_ids = ['NYU_TRT_session1', 'NYU_TRT_session2', 'NYU_TRT_session3']
data_path = os.path.abspath('/home/data/Originals/NYU_TRT/')
output_path = os.path.abspath('/home/data/Projects/nuisance_reliability_paper/')
start_volume = 0
stop_volume = 196

inputnode = pe.Node(interface=IdentityInterface(fields=['session_id', 'subject_id'],
                                                mandatory_inputs=True),
                    name='inputnode')
inputnode.iterables = [('session_id', session_ids),
                       ('subject_id', subject_ids[0:3])]

datasource = pe.Node(interface=nio.DataGrabber(infields=['session_id','subject_id'],
                                               outfields=['func', 'struct']),
                                               name='datasource')

datasource.inputs.base_directory = data_path
datasource.inputs.template = '*' 
datasource.inputs.field_template = dict(func='%s/%s/func/lfo.nii.gz',
                                        struct='%s/%s/anat/mprage_anonymized.nii.gz')

datasource.inputs.template_args = dict(func=[['session_id',  'subject_id']],
                                       struct=[['session_id', 'subject_id']])

datasink = pe.Node(nio.DataSink(infields=['container.@subject']), name='sinker')
datasink.inputs.base_directory = output_path
#datasink.inputs.substitutions = [('session\d_subject_id_', '')]

#st = pe.Node(interface=fsl.SliceTimer(), name='st')
#st.iterables = [('time_repetition', [2.0, 3.0])]

workflow = pe.Workflow(name='wf')
workflow.base_dir = output_path

anatpreproc=create_anat_preproc()

funcpreproc=create_func_preproc()
funcpreproc.inputs.inputspec.start_idx=start_volume
funcpreproc.inputs.inputspec.stop_idx=stop_volume

regpreproc=create_reg_preproc()
regpreproc.inputs.inputspec.standard_res_brain=os.path.abspath('/usr/share/fsl/4.1/data/standard/MNI152_T1_3mm_brain.nii.gz')
regpreproc.inputs.inputspec.standard=os.path.abspath('/usr/share/fsl/4.1/data/standard/MNI152_T1_3mm.nii.gz')
regpreproc.inputs.inputspec.config_file=os.path.abspath('/usr/share/fsl/4.1/etc/flirtsch/T1_2_MNI152_3mm.cnf')
regpreproc.inputs.inputspec.standard_brain_mask_dil=os.path.abspath('/usr/share/fsl/4.1/data/standard/MNI152_T1_3mm_brain_mask_dil.nii.gz')

segpreproc=create_seg_preproc()
segpreproc.inputs.inputspec.PRIOR_CSF = os.path.abspath('./tissuepriors/3mm/avg152T1_csf_bin.nii.gz')
segpreproc.inputs.inputspec.PRIOR_WHITE = os.path.abspath('./tissuepriors/3mm/avg152T1_white_bin.nii.gz')
segpreproc.inputs.inputspec.PRIOR_GRAY = os.path.abspath('./tissuepriors/3mm/avg152T1_gray_bin_3mm.nii.gz')
segpreproc.inputs.inputspec.standard_res_brain=os.path.abspath('/usr/share/fsl/4.1/data/standard/MNI152_T1_3mm_brain.nii.gz')

nuisancepreproc = create_nuisance_preproc()
nuisancepreproc.inputs.inputspec.selector = [False, False, False, False, False, False, True]
nuisancepreproc.inputs.inputspec.num_components = 5
nuisancepreproc.inputs.inputspec.target_angle_deg = 85

npbm = create_nuisance_preproc(name='nuisance_preproc_bm')
npbm.inputs.inputspec.selector = [True, True, True, True, True, True, True]
npbm.inputs.inputspec.num_components = 5
npbm.inputs.inputspec.target_angle_deg = 85

nppm = create_nuisance_preproc(name='nuisance_preproc_postmotion')
nppm.inputs.inputspec.selector = [True, True, True, True, True, True, True]
nppm.inputs.inputspec.num_components = 5
nppm.inputs.inputspec.target_angle_deg = 85

mni_warp = pe.MapNode(interface=fsl.ApplyWarp(), name='mni_warp', iterfield=['in_file',
                                                                             'field_file',
                                                                             'premat'])

statspreproc = create_stats_preproc()

workflow.connect(inputnode, 'session_id', datasource, 'session_id')
workflow.connect(inputnode, 'subject_id', datasource, 'subject_id')
#workflow.connect(datasource, 'func', st, 'in_file')
workflow.connect(datasource, 'func', funcpreproc, 'inputspec.rest')
workflow.connect(datasource, 'struct', anatpreproc, 'inputspec.anat')

workflow.connect(funcpreproc, 'outputspec.example_func', regpreproc, 'inputspec.example_func')
workflow.connect(funcpreproc, 'outputspec.preprocessed_mask', segpreproc, 'inputspec.preprocessed_mask')
workflow.connect(funcpreproc, 'outputspec.example_func', segpreproc, 'inputspec.example_func')

workflow.connect(anatpreproc, 'outputspec.brain', regpreproc, 'inputspec.brain')
workflow.connect(anatpreproc, 'outputspec.reorient', regpreproc, 'inputspec.reorient')
workflow.connect(anatpreproc, 'outputspec.brain', segpreproc, 'inputspec.brain')

workflow.connect(regpreproc, 'outputspec.highres2example_func_mat', segpreproc, 'inputspec.highres2example_func_mat')
workflow.connect(regpreproc, 'outputspec.stand2highres_warp', segpreproc, 'inputspec.stand2highres_warp')

workflow.connect(inputnode, 'session_id', datasink, 'container')

workflow.connect(funcpreproc, 'outputspec.preprocessed', mni_warp, 'in_file')
workflow.connect(regpreproc, 'inputspec.standard', mni_warp, 'ref_file')
workflow.connect(regpreproc, 'outputspec.highres2standard_warp', mni_warp, 'field_file')
workflow.connect(regpreproc, 'outputspec.example_func2highres_mat', mni_warp, 'premat')
workflow.connect(mni_warp, 'out_file', statspreproc, 'inputspec.realigned_file')
workflow.connect(mni_warp, 'out_file', datasink, 'preprocessed_mni')

workflow.connect(funcpreproc, 'outputspec.preprocessed', datasink, 'preprocessed')
workflow.connect(segpreproc, 'outputspec.csf_mask', datasink, 'masks.csf')
workflow.connect(segpreproc, 'outputspec.wm_mask', datasink, 'masks.wm')
workflow.connect(segpreproc, 'outputspec.probability_maps', datasink, 'masks.probability')
workflow.connect(segpreproc, 'outputspec.wm_mask', nuisancepreproc, 'inputspec.wm_mask')
workflow.connect(segpreproc, 'outputspec.csf_mask', nuisancepreproc, 'inputspec.csf_mask')
workflow.connect(segpreproc, 'outputspec.gm_mask', nuisancepreproc, 'inputspec.gm_mask')
workflow.connect(funcpreproc, 'outputspec.preprocessed', nuisancepreproc, 'inputspec.realigned_file')
workflow.connect(funcpreproc, 'outputspec.movement_parameters', nuisancepreproc, 'inputspec.motion_components')

workflow.connect(segpreproc, 'outputspec.wm_mask', npbm, 'inputspec.wm_mask')
workflow.connect(segpreproc, 'outputspec.csf_mask', npbm, 'inputspec.csf_mask')
workflow.connect(segpreproc, 'outputspec.gm_mask', npbm, 'inputspec.gm_mask')
workflow.connect(funcpreproc, 'outputspec.preprocessed', npbm, 'inputspec.realigned_file')
workflow.connect(funcpreproc, 'outputspec.movement_parameters', npbm, 'inputspec.motion_components')

workflow.connect(segpreproc, 'outputspec.wm_mask', nppm, 'inputspec.wm_mask')
workflow.connect(segpreproc, 'outputspec.csf_mask', nppm, 'inputspec.csf_mask')
workflow.connect(segpreproc, 'outputspec.gm_mask', nppm, 'inputspec.gm_mask')
workflow.connect(nuisancepreproc, 'outputspec.residual_file', nppm, 'inputspec.realigned_file')
workflow.connect(funcpreproc, 'outputspec.movement_parameters', nppm, 'inputspec.motion_components')
workflow.connect(nuisancepreproc, 'outputspec.residual_file', datasink, 'nuisance_corrected')

#workflow.connect(st, 'slice_time_corrected_file', datasink, 'slicecorrected')
