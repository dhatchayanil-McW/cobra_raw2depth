import argparse
import sys
import os
from pathlib import Path

import numpy as np

from development.src.M20_iTOF_data_generator import M20_iTOF_data
from development.src.M20_GPixel import M20_GPixel_device

"""Simple testbench to use M20-GPixel with imported data and save the SNR-voted frames for sharing with customers
"""


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--one',
                        action='store_true',
                        help='Save 1x1 binned raw data')
    parser.add_argument('--two',
                        action='store_true',
                        help='Save 2x2 binned raw data')
    parser.add_argument('-p', '--phase',
                        action='store_true',
                        help='Save phase data')
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help='Print stuff')
    return parser.parse_args(argv)



# 2: Process
configs = {  # 'perform_tap_add': perform_tap_add,
    'correct_strips': False,
    'binning': (1, 1),
    'binning_scale_input': False,
    'SNR_voting_combined': True,
    'SNR_voting_thres_enable': False,
    'temporal_boxcar_length': 1,  # Set this to 1 to disable it
    'enable_convolution': False,
    'enable_phase_correction': False,
    'use_1d_convolutions': True,
    'convolution_kernel_x_size': 5,
    'convolution_kernel_y_size': 7,
    'M_filter': False,
    'M_filter_loc': 1,
    'M_filter_type': 2,
    'M_median_filter_size': 3,
    'M_median_filter_shape': None,
    'range_edge_filter_en': False,
    'NN_enable': False,
    'NN_filter_level': 0,
    'NN_min_neighbors': 6,
    'NN_patch_size': 3,
    'NN_range_tolerance': 0.7,
    'SNR_threshold_enable': False,
    'SNR_threshold': 2}



general_name = 'phase_calibration'
prepends = ['pixel-phase']
data_name = 'pixel_phase_scene'


if '_g' in general_name:
    if '06' in data_name:
        IGNORE = {1: 91*3-14,
        }
        OFFSET = 0
        START = 1
        END = 24
    elif '69' in data_name:
        IGNORE = {}
        OFFSET = 23
        START = 1
        END = 12
elif '_h' in general_name:
    IGNORE = {}
    OFFSET = 0
    START = 1
    END = 20
elif 'phase_calibration' in general_name:
    IGNORE = {1: 91*10-15}#91*3-14}
    OFFSET = 0
    START = 1
    END = 2
elif 'phase_scene' in general_name:
    IGNORE = {}#91*10-15}#91*3-14}
    OFFSET = 0
    START = 3
    END = 4
else:
    IGNORE = {}
    OFFSET = 0
    START = 1
    END = 2
N_ROIS = 5000

#path = Path(Path.home(), 'chronoptics',  general_name, 'raw_roi_bin', data_name)
path = Path(Path.home(), *prepends, general_name,)
N_ROIS = 10000

print(path)


##############################################
# 1: Import input data
# General params
num_rows_per_roi = 20        # Number of rows per ROI at the input (before any binning)
num_columns_per_roi = 640   # Number of columns per ROI at the input (before any binning)
num_rois = 91               # Number of ROIs per frame
num_rows_full_frame = 460


def main(args):
    data_gen = M20_iTOF_data(num_rows_per_roi, num_columns_per_roi, num_rois, num_rows_full_frame)
    device = M20_GPixel_device(num_rows_per_roi, num_columns_per_roi,
                               num_rois, num_rows_full_frame)

    ################
    # Import data recorded from real sensor (Uncomment the next 4 lines if you want to load data from sensor)
    # UNCOMMENT ALL THE FOLLOWING LINES TO USE

    use_old_metadata_format = False
    fov_num_to_use = 0

    for idx, base in enumerate(range(START, END)):

        num_frames = int((N_ROIS-IGNORE.get(base, 90)) / num_rois)
        # The device processes 1 frame at a time

        cnt = (idx+OFFSET) * num_frames
        print('\n\nbase', base, 'count', cnt, 'idx', idx, '\n\n')

        file_name_base = data_name + f'_0_{base:02}_'
        print('file name base', file_name_base, path)
        input_data_name, input_data_shape, perform_tap_add = (
            data_gen.load_sensor_data(path, file_name_base, num_frames, np.uint16,
                                      use_old_metadata_format, fov_num_to_use,
                                      ignore_num=IGNORE.get(base, 90))
        )
        configs['perform_tap_add'] = perform_tap_add

        ###########################################################################
        start_vector = data_gen.data["ROI_start_vector"]
        print(len(start_vector), [len(x) for x in start_vector])
        # Checking that we skipped the right number of frames in the beginning. These should all be the same.
        print('first entry', [x[0] for x in start_vector])
        print('last entry', [x[-1] for x in start_vector])
        if args.verbose:
            for idx, x in enumerate(start_vector[1::]):
                print(np.asarray(start_vector[idx-1], dtype=float) - np.asarray(start_vector[idx], dtype=float))
            print([x for x in start_vector])

        input_data = data_gen.data[input_data_name]

        if args.one:
            configs['binning'] = (1, 1)
            b1cnt = []
            for i in range(num_frames):
                b1cnt.append(cnt+i)
                _ = device(input_data=input_data[i],
                           roi_start_vector=start_vector[i],
                           configs=configs)
                save_file = Path(Path.home(), *prepends, general_name, 'unbinned_frame_npy',
                                 f'{general_name}_assembled_frame_unbinned_{base+OFFSET:02}_{i:03}.npy')
                print(save_file)
                np.save(save_file, device.dsp.data["combined_data_frame"].flt)
                if args.phase:

                    psave_file = Path(Path.home(), *prepends, general_name, 'unbinned_frame_npy',
                                      f'{general_name}_assembled_phase_frame_unbinned_{base+OFFSET:02}_{i:03}.npy')
                    np.save(psave_file, device.dsp.data["phase_frame"].flt)
                device.clear(force_clear=True)
            print('1bin', b1cnt)
        if args.two:
            b2cnt = []
            configs['binning'] = (2, 2)
            for i in range(num_frames):
                b2cnt.append(cnt+i)
                _ = device(input_data=input_data[i],
                           roi_start_vector=start_vector[i],
                           configs=configs)
                save_file = Path(Path.home(), *prepends, general_name, 'binned_frame_npy',
                                 f'{general_name}_assembled_frame_binned_{base+OFFSET:02}_{i:03}.npy')
                print(save_file)
                np.save(save_file, device.dsp.data["combined_data_frame"].flt)
                if args.phase:

                    psave_file = Path(Path.home(), *prepends, general_name, 'unbinned_frame_npy',
                                      f'{general_name}_assembled_phase_frame_binned_{base+OFFSET:02}_{i:03}.npy')
                    np.save(psave_file, device.dsp.data["phase_frame"].flt)
                device.clear(force_clear=True)
            print('2bin', b2cnt)


if __name__ == "__main__":
    args_ = parse_args(sys.argv[1:])
    main(args_)
