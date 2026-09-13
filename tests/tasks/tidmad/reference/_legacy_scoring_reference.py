"""Reference-only copy of the five historical TIDMAD scoring functions.

The algorithm is preserved for numeric parity.  The sole compatibility patch
casts the FFT input to float64, restoring NumPy 1.x promotion under which the
canonical historical score was produced.  Production code must not import this
test oracle.
"""

# ruff: noqa
from __future__ import annotations

import concurrent.futures
import gc
import logging
import math
import os

import h5py
import h5py as h5
import numpy as np
from tqdm import tqdm

logging.basicConfig(
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
    level=logging.ERROR,
)


def GetOneSecPSD(file_path, files, ch, start=0):
    file_list = []

    if type(files) == list:
        for f in files:
            file_list.append(os.path.join(file_path, f))
    elif files.endswith(".h5"):
        file_list = [os.path.join(file_path, files)]
        logging.info("Getting data from h5 file")
    else:
        logging.error("Not acceptable data format!")
    N = 10000000
    psd_sum = np.zeros(int(N / 2))
    interfile_data = []
    total_psds = 0
    N_sec_file = 200

    fileNum = start // N_sec_file
    startIndex = N * (start % N_sec_file)

    file = file_list[fileNum]
    logging.info("Opening file " + file)
    with h5.File(file) as h5f:
        if ch == 1:
            data = h5f["timeseries"]["channel0001"]["timeseries"][
                startIndex : startIndex + N
            ]
        elif ch == 2:
            data = h5f["timeseries"]["channel0002"]["timeseries"][
                startIndex : startIndex + N
            ]
        else:
            logging.error("Incorrect channel number. Choose 1 or 2")
        volt_range = (h5f["timeseries"]["channel0001"]).attrs["voltage_range_mV"]
        logging.info("Retrieved data from h5.")

        scaling = np.float32(volt_range / (2 * 128.0))
        TS = np.array(data, dtype=np.float32) * scaling
        logging.info("Retrieved time series.")

        dt = (
            1.0
            / (h5.File(file)["timeseries"]["channel0001"]).attrs["sampling_frequency"]
        )

        psd_chunk = (
            dt
            / N
            * (
                abs(np.fft.rfft(TS.astype(np.float64).reshape(len(TS) // N, N))) ** 2
            ).sum(0)[1:]
        )
        freq_array = np.linspace(0, 5 * 1e6, int(N / 2))
    del data, TS, dt
    gc.collect()
    return freq_array, psd_chunk


def findPeak(pwr):
    peakdiff = pwr[1:-1] - pwr[:-2] - pwr[2:]
    peakIndex = int(np.where(peakdiff == np.amax(peakdiff))[0][0]) + 1
    return peakIndex


def getSNR(freq, pwr, target=0):
    if target == 0:
        center_id = findPeak(pwr)
    else:
        center_id = int(np.where(freq == target)[0][0])
    sig_range = 1
    noise_range = 50
    signal = np.sum(pwr[center_id - sig_range : center_id + sig_range + 1])
    noise = np.sum(pwr[center_id - noise_range : center_id + noise_range + 1]) - signal
    if noise == 0:
        noise = 1e-5
    return [signal / noise, freq[center_id]]


def process_iteration(i, path, file, coarse):
    start_index = i * 10 if coarse else i
    freq_sg, psd_sg = GetOneSecPSD(path, file, ch=2, start=start_index)
    snr_sg, center_freq = getSNR(freq_sg, psd_sg)

    freq_squid, psd_squid = GetOneSecPSD(path, file, ch=1, start=start_index)
    snr_squid = getSNR(freq_squid, psd_squid, center_freq)[0]
    return i, snr_sg, snr_squid


def calculateBenchmark(path, file, args):
    if type(file) == list:
        n = 200 * len(file)
    elif file.endswith(".h5"):
        with h5py.File(os.path.join(path, file), "r") as file:
            dataset = file["/timeseries/channel0001/timeseries"]
            length = dataset.shape[0]
            n = length // 10000000
    else:
        print("Incorrect file format")
    if args.coarse:
        n = int(n / 10)
    snr_squid = np.zeros(shape=(n,))
    snr_sg = np.zeros(shape=(n,))
    if args.parallel:
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=args.num_workers
        ) as executor:
            tasks = [
                executor.submit(process_iteration, i, path, file, args.coarse)
                for i in range(n)
            ]

            for future in tqdm(concurrent.futures.as_completed(tasks), total=n):
                i, result_snr_sg, result_snr_squid = future.result()
                snr_sg[i] = result_snr_sg
                snr_squid[i] = result_snr_squid
    else:
        for i in tqdm(range(n)):
            i, result_snr_sg, result_snr_squid = process_iteration(
                i, path, file, args.coarse
            )
            snr_sg[i] = result_snr_sg
            snr_squid[i] = result_snr_squid
    snr_sg = snr_sg / (np.amax(snr_sg))
    score = (
        np.round(np.sum(np.multiply(snr_sg, snr_squid)) / snr_squid.size, decimals=2)
        + 1e-10
    )
    return math.log(score, 5.27)
