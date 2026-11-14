from datetime import datetime
from math import isfinite
from pathlib import PurePosixPath
from zipfile import ZipFile, is_zipfile

from defusedxml.ElementTree import iterparse

LIMIT = 32 * 1024 * 1024


def readings(stream):
    latest = {}
    for _, node in iterparse(stream, events=("end",)):
        attrs = node.attrib
        if node.tag == "Record" and attrs.get("type") == "HKQuantityTypeIdentifierHeartRate" and attrs.get("unit") in ("count/min", "bpm"):
            try:
                stamp = datetime.strptime(attrs["startDate"], "%Y-%m-%d %H:%M:%S %z")
                value = float(attrs["value"])
                if isfinite(value) and value > 0:
                    latest[stamp] = value
            except (ValueError, KeyError):
                pass
        node.clear()
    return [{"time": stamp.isoformat(), "heart_rate": latest[stamp]} for stamp in sorted(latest)[-100:]]


def import_health(upload):
    if upload.size > LIMIT:
        raise ValueError("Use a file smaller than 32 MB.")
    upload.seek(0)
    if is_zipfile(upload):
        upload.seek(0)
        with ZipFile(upload) as archive:
            for item in archive.infolist():
                if PurePosixPath(item.filename).name == "export.xml":
                    if item.file_size > LIMIT:
                        raise ValueError("The uncompressed export must be smaller than 32 MB.")
                    with archive.open(item) as stream:
                        return readings(stream)
        raise ValueError("The archive needs an export.xml file.")
    upload.seek(0)
    return readings(upload)
