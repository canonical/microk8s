import subprocess
import yaml
import sys

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    with open(sys.argv[1], "r") as stream:
        try:
            manifest = yaml.safe_load(stream)
            for component in manifest["status"]["components"]:
                for asset in component["assets"]:
                    if asset["name"] == "pause-image":
                        with open(f"{sys.argv[2]}/PAUSE_IMAGE", "w+") as pause_image:
                            pause_image.write(asset["image"]["uri"])
                    elif asset["name"] == "coredns-image":
                        with open(f"{sys.argv[2]}/COREDNS_IMAGE", "w+") as coredns_image:
                            coredns_image.write(asset["image"]["uri"])
                    elif asset["name"] == "metrics-server-image":
                        with open(f"{sys.argv[2]}/METRICS_SERVER_IMAGE", "w+") as metrics_server_image:
                            metrics_server_image.write(asset["image"]["uri"])
        except yaml.YAMLError as exc:
            print(exc)