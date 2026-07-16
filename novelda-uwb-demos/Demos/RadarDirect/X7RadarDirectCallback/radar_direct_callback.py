# radar_direct_callback.py
# Modified version with:
# 1. Print once whether data is BBIQ or RF
# 2. Live Range-Time Map visualization
# 3. Original functionality preserved




from pathlib import Path
import os
import sys
import json

import numpy as np

_X7_SDK_BIN = r"C:\RR_02\X7_SDK_0.6_x64-win\bin"
if _X7_SDK_BIN not in sys.path and os.path.isdir(_X7_SDK_BIN):
    sys.path.insert(0, _X7_SDK_BIN)

import PySignalFlow as psf

# from live_rtm import update_rtm

from Utils.param_maker import ParamMaker
from Utils.semantics import *
from Utils.misc import prep_rec_dir


class RadarDirectCallback:

    def __init__(self):

        self._callback_func = None
        self._json_preset = None

        self._range_offset = -1.0
        self._bin_length = -1.0
        self._range_decimation = -1

        self._printed_type = False

        self.frames = []

    def run_with_callback_preset(self, callback_func, preset_json_path):

        self._callback_func = callback_func
        self._json_preset = preset_json_path

        flow = psf.Flow()

        liveflow_fp = str(
            Path(__file__).resolve().parent /
            "Flows" /
            "LiveHost_RadarDirect_Python.sfl"
        )

        playbackflow_fp = str(
            Path(__file__).resolve().parent /
            "Flows" /
            "PlaybackHost_RadarDirect_Python.sfl"
        )

        live_dcremoval_fp = str(
            Path(__file__).resolve().parent /
            "Flows" /
            "LiveHost_RadarDirect_DCRemoval_Python.sfl"
        )

        playback_dcremoval_fp = str(
            Path(__file__).resolve().parent /
            "Flows" /
            "PlaybackHost_RadarDirect_DCRemoval_Python.sfl"
        )

        stp_fp = str(Path(self._json_preset).resolve())

        with open(stp_fp, "r") as f:
            stp = json.load(f)

        islive = stp.get("IsLive", True)
        is_dc_removal = stp.get("DCRemoval", "true")
        if isinstance(is_dc_removal, str):
            is_dc_removal = is_dc_removal.lower() == "true"
        elif not isinstance(is_dc_removal, bool):
            is_dc_removal = bool(is_dc_removal)

        pm = ParamMaker()
        pm["RDPlottingParameters"]["IsLive"] = (
            "true" if islive else "false"
        )

        ba22 = stp["BA22FirmwarePath"]
        filesource_in = stp["PlaybackFile"]

        if islive:

            pm["ConnectionParameters"]["BA22FirmwarePath"] = f"\"{ba22}\""

            ba22_fp = Path(ba22).resolve()

            if not os.path.isfile(ba22_fp):
                raise FileNotFoundError(
                    "BA22 firmware file not specified or not found!"
                )

        else:

            in_fp = Path(filesource_in).resolve()

            if not os.path.isfile(in_fp):
                raise FileNotFoundError(
                    "Playback file for X7BasebandRaw not specified or not found!"
                )

            pm["fileSource"]["Path"] = f"\"{in_fp}\""

        for sec, dct in stp.items():

            if isinstance(dct, dict):

                for param, val in dct.items():
                    pm[sec][param] = val

        record = stp["DoRecording"]
        recdir = stp["RecordingDirectory"]
        recprefix = stp["RecordingPrefix"]

        if record and islive:

            recfp, _ = prep_rec_dir(
                str(stp_fp),
                recdir,
                recprefix
            )

            pm["fileSink"]["Enabled"] = (
                "true" if record else "false"
            )

            pm["fileSink"]["Path"] = f"\"{str(recfp)}\""

        if islive:
            flow_to_load = (
                live_dcremoval_fp
                if is_dc_removal
                else liveflow_fp
            )
        else:
            flow_to_load = (
                playback_dcremoval_fp
                if is_dc_removal
                else playbackflow_fp
            )

        print(
            "Running RadarDirect(callback) with preset:",
            self._json_preset
        )

        flow.load(flow_to_load)

        flow.set_output_tap(
            self._actual_tapout_func
        )

        flow.set_parameters(
            parameter_string=pm.get_as_string()
        )

        flow.run()

    def _actual_tapout_func(self, node_key, frame):

        if SIGSEM_RADAR_PARAMETERS in frame:

            self._range_offset = np.asarray(
                frame[SIGSEM_RADAR_PARAMETERS][ARRSEM_RANGE_OFFSET]
            )[0]

            self._bin_length = np.asarray(
                frame[SIGSEM_RADAR_PARAMETERS][ARRSEM_BIN_LENGTH]
            )[0]

            self._range_decimation = np.asarray(
                frame[SIGSEM_RADAR_PARAMETERS][ARRSEM_RANGE_DECIMATION]
            )[0]

        seq_num = frame.sequence_number
        timestamp = frame.timestamp

        trx_mask = np.asarray(
            frame[SIGNAL_SEMANTIC_RADAR_X7][ARRAY_SEMANTIC_RADAR_TRXMASK]
        )[0]

        data = None

        if ARRAY_SEMANTIC_BBIQ_FLOAT32 in frame[SIGNAL_SEMANTIC_RADAR_X7]:

            if not self._printed_type:
                print("\nReceiving BBIQ_FLOAT32")
                self._printed_type = True

            data = np.asarray(
                frame[SIGNAL_SEMANTIC_RADAR_X7][
                    ARRAY_SEMANTIC_BBIQ_FLOAT32
                ]
            )

        elif ARRAY_SEMANTIC_RF_FLOAT32 in frame[SIGNAL_SEMANTIC_RADAR_X7]:

            if not self._printed_type:
                print("\nReceiving RF_FLOAT32")
                self._printed_type = True

            data = np.asarray(
                frame[SIGNAL_SEMANTIC_RADAR_X7][
                    ARRAY_SEMANTIC_RF_FLOAT32
                ]
            )

        else:
            raise RuntimeError(
                "There is no data in the radar frame."
            )

        try:
            signal = np.mean(
                np.abs(data),
                axis=(0, 1)
            )

            if not hasattr(self, "prev_signal"):
                self.prev_signal = signal.copy()

            motion_metric = np.mean(
                np.abs(signal - self.prev_signal)
            )

            self.prev_signal = signal.copy()

            if seq_num % 10 == 0:

                # print("\n" + "=" * 60)
                # print(f"FRAME {seq_num}")
                # print("=" * 60)

                # print(
                #     f"Motion Metric = {motion_metric:.6f}"
                # )
                pass

            if motion_metric > 0.05:
                # print(">>> MOVEMENT DETECTED <<<")
                pass

            for tx in range(2):
                for rx in range(2):

                    sig = data[tx, rx, :]

                    peak_bin = np.argmax(
                        np.abs(sig)
                    )

                    peak_val = np.max(
                        np.abs(sig)
                    )

                    # print(
                    #     f"TX{tx}RX{rx} | "
                    #     f"PeakBin={peak_bin} | "
                    #     f"PeakVal={peak_val:.4f}"
                    # )
                    pass

            global_peak = np.argmax(signal)

            # print(
            #     f"GlobalPeakBin={global_peak} | "
            #     f"GlobalPeakValue={signal[global_peak]:.4f}"
            # )

        # Update RTM
            # update_rtm(signal)

        except Exception as e:
            if "application has been destroyed" not in str(e):
                print("RTM Error:", e)

        return self._callback_func(
            trx_mask,
            data,
            seq_num,
            timestamp,
            self._range_offset,
            self._bin_length
        )