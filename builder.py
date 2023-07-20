#!/usr/bin/python3

import time
import os
import subprocess
import boto3
import io
import json
import click
import sys
import requests
from datetime import date
import shutil
import xml.etree.ElementTree as ET


def fail(message):
    click.echo(message, err=True)
    sys.exit(1)


tree = ET.parse("config.xml")
for e in tree.getroot().iter("release-version"):
    RELEASE = e.text
    break


if not RELEASE:
    fail("Could not parse release from config.xml")

TODAY = date.today().strftime("%Y%m%d")

# TODO: should be a class using abc
TARGETS = {
    "kde": {
        "profile": "Workstation-KDE",
        "name": f"Fedora Linux {RELEASE.capitalize()} with KDE Plasma ({TODAY})",
        "os_name": "Fedora Linux with KDE Plasma",
        "id": "kde",
    },
    "gnome": {
        "profile": "Workstation-GNOME",
        "name": f"Fedora Linux {RELEASE.capitalize()} with GNOME ({TODAY})",
        "os_name": "Fedora Linux with GNOME",
        "id": "gnome",
    },
    "server": {
        "profile": "Server",
        "name": f"Fedora Linux {RELEASE.capitalize()} Server ({TODAY})",
        "os_name": "Fedora Linux Server",
        "id": "server",
    },
    "minimal": {
        "profile": "Minimal",
        "name": f"Fedora Linux {RELEASE.capitalize()} Minimal ({TODAY})",
        "os_name": "Fedora Linux Minimal",
        "id": "minimal",
    },
}

MANIFEST = os.getenv("MANIFEST", "installer_data.json")
S3_BUCKET = os.getenv("S3_BUCKET")


def requireCommands(commands):
    missing = []
    for cmd in commands:
        if shutil.which(cmd) is None:
            missing.append(cmd)

    if len(missing) > 0:
        fail("Required commands not found: {}".format(" ".join(missing)))


def runCommand(cmd, shell=False):
    p = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        shell=shell,
    )
    if p.returncode != 0:
        fail(p.stdout)

    return p


def kiwiBuild(profile):
    requireCommands(["kiwi-ng"])

    # TODO: check current status first
    # runCommand(
    #    [
    #        "sudo",
    #        "setenforce",
    #        "0",
    #    ]
    # )
    # TODO: use the API instead of shelling out
    runCommand(
        [
            "sudo",
            "kiwi-ng",
            "--debug",
            "--type=oem",
            f"--profile={profile}",
            "system",
            "build",
            "--description",
            "./",
            "--target-dir",
            "./outdir",
        ]
    )
    # runCommand(
    #    [
    #        "sudo",
    #        "setenforce",
    #        "1",
    #    ]
    # )


def packageBuild(target):
    # TODO: rewrite in python instead of shelling out
    runCommand(["./make-asahi-installer-package.sh"])

    package = f"fedora-{RELEASE}-{target['id']}-{TODAY}.zip"
    os.rename(f"fedora-{RELEASE}-{TODAY}.zip", package)
    with open("installer_data.json", "r") as f:
        data = json.load(f)

    data["os_list"][0]["name"] = target["name"]
    data["os_list"][0]["default_os_name"] = target["os_name"]
    data["os_list"][0]["package"] = package

    with open("installer_data.json", "w") as f:
        json.dump(data, f)


def uploadToS3(source, destination):
    s3 = boto3.client("s3")
    s3.upload_file(source, S3_BUCKET, destination)


def packageUpload(target):
    base = f"fedora-{RELEASE}-{target['id']}-{TODAY}"
    package = f"{base}.zip"
    logs_package = f"{base}-logs.zip"
    image = f"{base}.raw.zstd"

    uploadToS3(package, f"os/{package}")
    uploadToS3(logs_package, f"os/{logs_package}")
    uploadToS3(image, f"os/{image}")


def getManifest():
    s3 = boto3.resource("s3")
    obj = s3.Object(S3_BUCKET, MANIFEST)
    data = io.BytesIO()
    obj.download_fileobj(data)

    return json.loads(data.getvalue().decode("utf-8"))


def manifestUpdate():
    old = getManifest()
    with open("installer_data.json", "r") as f:
        new = json.load(f)

    old["os_list"].insert(0, new["os_list"][0])
    with open("merged_installer_data.json", "w") as f:
        json.dump(old, f)


@click.group()
def cli():
    pass


@cli.command()
@click.argument("target")
def build(target):
    if target not in TARGETS.keys():
        fail(f"Unknown target: {target}")

    target = TARGETS[target]
    kiwiBuild(target["profile"])


@cli.command()
@click.argument("target")
def package(target):
    if target not in TARGETS.keys():
        fail(f"Unknown target: {target}")

    target = TARGETS[target]
    packageBuild(target)


@cli.command()
@click.argument("target")
def upload(target):
    if target not in TARGETS.keys():
        fail(f"Unknown target: {target}")

    target = TARGETS[target]

    packageUpload(target)
    manifestUpdate()
    uploadToS3("merged_installer_data.json", MANIFEST)


@cli.command()
@click.option("--update/--no-update", default=False)
@click.option("--upload/--no-upload", default=False)
def manifest(update, upload):
    if update:
        manifestUpdate()
        manifest = "merged_installer_data.json"
        if upload:
            uploadToS3(manifest, MANIFEST)
    else:
        manifest = getManifest()

    click.echo(json.dumps(manifest, indent=2))


@cli.command()
def clean():
    runCommand(["sudo", "rm", "-rf", "outdir"])
    runCommand(["rm", "-f", "installer_data.json", "merged_installer_data.json"])


if __name__ == "__main__":
    cli()
