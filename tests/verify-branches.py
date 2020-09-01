import requests
from subprocess import check_output


class TestMicrok8sBranches(object):
    def test_branches(self):
        """Ensures LP builders push to correct snap tracks.

        We need to make sure the LP builders pointing to the master github branch are only pushing
        to the latest and current k8s stable snap tracks. An indication that this is not enforced is
        that we do not have a branch for the k8s release for the previous stable release. Let me
        clarify with an example.

        Assuming upstream stable k8s release is v1.12.x, there has to be a 1.11 github branch used
        by the respective LP builders for building the v1.11.y.
        """
        upstream_version = self._upstream_release()
        assert upstream_version
        version_parts = upstream_version.split('.')
        major_minor_upstream_version = "{}.{}".format(version_parts[0][1:], version_parts[1])
        if version_parts[1] != "0":
            prev_major_minor_version = "{}.{}".format(
                version_parts[0][1:], int(version_parts[1]) - 1
            )
        else:
            major = int(version_parts[0][1:]) - 1
            minor = self._get_max_minor(major)
            prev_major_minor_version = "{}.{}".format(major, minor)
        print(
            "Current stable is {}. Making sure we have a branch for {}".format(
                major_minor_upstream_version, prev_major_minor_version
            )
        )
        cmd = "git ls-remote --heads http://github.com/ubuntu/microk8s.git {}".format(
            prev_major_minor_version
        )
        branch = check_output(cmd.split()).decode("utf-8")
        assert prev_major_minor_version in branch

    def _upstream_release(self):
        """Return the latest stable k8s in the release series"""
        release_url = "https://dl.k8s.io/release/stable.txt"
        r = requests.get(release_url)
        if r.status_code == 200:
            return r.content.decode().strip()
        else:
            None

    def _get_max_minor(self, major):
        """Get the latest minor release of the provided major.
        For example if you use 1 as major you will get back X where X gives you latest 1.X release.
        """
        minor = 0
        while self._upstream_release_exists(major, minor):
            minor += 1
        return minor - 1

    def _upstream_release_exists(self, major, minor):
        """Return true if the major.minor release exists"""
        release_url = "https://dl.k8s.io/release/stable-{}.{}.txt".format(major, minor)
        r = requests.get(release_url)
        if r.status_code == 200:
            return True
        else:
            return False
