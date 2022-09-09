import os
import yaml
import sys
from pathlib import Path

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    with open(sys.argv[1], "r") as stream:
        try:
            manifest = yaml.safe_load(stream)
            with open(f"{sys.argv[2]}/images-list", "w+") as list:
                for component in manifest["status"]["components"]:
                    component_path = "{}/eksd-components/{}".format(os.environ["SNAPCRAFT_PART_BUILD"], component["name"])
                    Path(component_path).mkdir(parents=True, exist_ok=True)

                    with open(f"{component_path}/git-tag", "w+") as tag_file:
                        tag_file.write(component["gitTag"])

                    for asset in component["assets"]:
                        if asset["name"] == "pause-image":
                            list.write("PAUSE_IMAGE={}\n".format(asset["image"]["uri"]))
                        elif asset["name"] == "coredns-image":
                            list.write("COREDNS_IMAGE={}\n".format(asset["image"]["uri"]))
                        elif asset["name"] == "metrics-server-image":
                            list.write("METRICS_SERVER_IMAGE={}\n".format(asset["image"]["uri"]))
        except yaml.YAMLError as exc:
            print(exc)