"""Compare calibrated photometry from two images in Afterglow .csv file"""

import argparse
import os

import numpy as np
from matplotlib.pyplot import figure, errorbar, savefig, xlabel, ylabel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('filename', metavar='FILENAME', help='Afterglow CVS photometry file name')
    args = parser.parse_args()

    with open(os.path.expanduser(args.filename), encoding="ascii") as f:
        lines = f.read().splitlines()

    colnames = lines[0].split(",")
    col_pos = {name: i for i, name in enumerate(colnames)}
    file_id_pos = col_pos['file_id']
    src_id_pos = col_pos['id']
    x_pos = col_pos['x']
    y_pos = col_pos['y']
    mag_pos = col_pos['calibrated_mag']
    mag_error_pos = col_pos['mag_error']
    zero_point_error_pos = col_pos['zero_point_error']

    sources = {}
    for line in lines[1:]:
        fields = line.split(",")
        mag = fields[mag_pos]
        if mag.strip():
            sources[(int(fields[file_id_pos]), fields[src_id_pos])] = (
                float(fields[x_pos]), float(fields[y_pos]), float(mag), float(fields[mag_error_pos]),
                float(fields[zero_point_error_pos]),
            )

    file_ids = set(file_id for file_id, _ in sources)
    assert len(file_ids) == 2, "Expected exactly two files in the photometry file"
    # Keep only sources present in both files
    src_ids = set(src_id for file_id, src_id in sources if ((file_ids - {file_id}).pop(), src_id) in sources)
    print(f"Found {len(src_ids)} common sources")

    file_id1, file_id2 = file_ids
    x1, y1, mag1, mag1_err, zp1_err = np.transpose([sources[(file_id1, src_id)] for src_id in src_ids])
    x2, y2, mag2, mag2_err, zp2_err = np.transpose([sources[(file_id2, src_id)] for src_id in src_ids])

    figure()
    errorbar(
        mag2, mag1 - mag2, yerr=np.sqrt(mag1_err**2 + zp1_err**2 + mag2_err**2 + zp2_err**2),
        xerr=np.sqrt(mag2_err**2 + zp2_err**2), fmt='o', capsize=2, ecolor="black"
    )
    xlabel("Calibrated magnitude")
    ylabel(r"$\Delta m$")
    savefig("compare_photometry.png")

    print(f"Zero point offset: {(mag2 - mag1)[mag1 < 18].mean():.3f}")

if __name__ == '__main__':
    main()
