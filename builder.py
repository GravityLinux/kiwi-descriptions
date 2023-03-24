#!/usr/bin/python3

import time
import os
import subprocess
import boto3
import json
import click
import sys
import requests
from datetime import date
import shutil


def fail(message):
    click.echo(message, err=True)
    sys.exit(1)


RELEASE = os.getenv("FEDORA_RELEASE")

if not RELEASE:
    fail("FEDORA_RELEASE is not defined in your environment, aborting")

# TODO: should be a class using abc
TARGETS = {
    "gnome": {
        "profile": "Workstation-GNOME",
        "name": f"Fedora Linux {RELEASE}",
        "id": "gnome",
    },
    "kde": {
        "profile": "Workstation-KDE",
        "name": f"Fedora Linux {RELEASE} with KDE",
        "id": "kde",
    },
    "server": {
        "profile": "Server",
        "name": f"Fedora Linux {RELEASE} Server",
        "id": "server",
    },
    "minimal": {
        "profile": "Minimal",
        "name": f"Fedora Linux {RELEASE} Minimal",
        "id": "minimal",
    },
}

MANIFEST_URI = os.getenv("MANIFEST_URI")
CF_DISTRIBUTION = os.getenv("CF_DISTRIBUTION")
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
    today = date.today().strftime("%Y%m%d")

    if target["id"] == "gnome":
        package = f"fedora-{RELEASE}-{today}.zip"
    else:
        package = f"fedora-{RELEASE}-{target['id']}-{today}.zip"
        os.rename(f"fedora-{RELEASE}-{today}.zip", package)
    with open("installer_data.json", "r") as f:
        data = json.load(f)

    data["os_list"][0]["name"] = target["name"]
    data["os_list"][0]["default_os_name"] = target["name"]
    data["os_list"][0]["package"] = package

    with open("installer_data.json", "w") as f:
        json.dump(data, f)


def uploadToS3(source, destination):
    s3 = boto3.client("s3")
    s3.upload_file(source, S3_BUCKET, destination)


def invalidateCF(path):
    cf = boto3.client("cloudfront")
    res = cf.create_invalidation(
        DistributionId=CF_DISTRIBUTION,
        InvalidationBatch={
            "Paths": {"Quantity": 1, "Items": [path]},
            "CallerReference": str(time.time()).replace(".", ""),
        },
    )
    invalidation_id = res["Invalidation"]["Id"]
    return invalidation_id


def packageUpload(target):
    today = date.today().strftime("%Y%m%d")
    if target["id"] == "gnome":
        package = f"fedora-{RELEASE}-{today}.zip"
    else:
        package = f"fedora-{RELEASE}-{target['id']}-{today}.zip"

    uploadToS3(package, f"os/{package}")


def getManifest():
    return requests.get(MANIFEST_URI).json()


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
    uploadToS3("merged_installer_data.json", "installer_data.json")
    invalidateCF("/installer_data.json")


@cli.command()
@click.option("--update/--no-update", default=False)
@click.option("--upload/--no-upload", default=False)
@click.option("--invalidate/--no-invalidate", default=False)
def manifest(update, upload, invalidate):
    if update:
        manifestUpdate()
        manifest = "merged_installer_data.json"
        if upload:
            uploadToS3(manifest, "installer_data.json")
    else:
        manifest = getManifest()

    click.echo(json.dumps(manifest, indent=2))

    if invalidate:
        invalidateCF("/installer_data.json")


@cli.command()
def clean():
    runCommand(["sudo", "rm", "-rf", "outdir"])
    runCommand(["rm", "-f", "installer_data.json", "merged_installer_data.json"])


if __name__ == "__main__":
    cli()
