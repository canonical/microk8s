import yaml
import sys

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)

    eks_manifest_file = sys.argv[1]
    configuration_file = f"{sys.argv[2]}/configuration.sh"

    with open(eks_manifest_file) as fin:
        manifest = yaml.safe_load(fin)

    kvs = {}

    for component in manifest["status"]["components"]:
        for asset in component["assets"]:
            if asset["name"] == "pause-image":
                kvs["PAUSE_IMAGE"] = asset["image"]["uri"]
            elif asset["name"] == "coredns-image":
                kvs["COREDNS_IMAGE"] = asset["image"]["uri"]
            elif asset["name"] == "metrics-server-image":
                kvs["METRICS_SERVER_IMAGE"] = asset["image"]["uri"]

    with open(configuration_file, "w+") as fout:
        fout.write("\n".join("{}={}".format(k, v) for k, v in kvs.items()))
