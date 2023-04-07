import os
import shutil

from calico.upgrade import (
    try_upgrade,
    get_installed_version_of_calico,
    get_calicos_autodetection_method,
    mark_apply_needed,
)


class TestCNIUpgrade(object):
    def setup_class(self):
        dirname, filename = os.path.split(os.path.abspath(__file__))
        self._invalid_yaml = os.path.join(dirname, "yamls/invalid.yaml")
        self._calico_new_yaml = os.path.join(dirname, "yamls/calico-new.yaml")
        self._calico_old_yaml = os.path.join(dirname, "yamls/cni.yaml")
        self._calico_old_copy_yaml = os.path.join(dirname, "yamls/cni.yaml.copy")
        self._calico_old_copy_backup_yaml = os.path.join(dirname, "yamls/cni.yaml.copy.backup")
        self._lock_file = os.path.join(dirname, "yamls/lock_file")
        self._cni_no_manage_file = os.path.join(dirname, "yamls/cni_no_manage")

    def test_no_op(self):
        """
        Test conditions under which the upgrade should not continue
        """
        res = try_upgrade("foo", "bar")
        assert res is False
        res = try_upgrade(self._calico_new_yaml, self._calico_new_yaml)
        assert res is False
        res = try_upgrade(self._invalid_yaml, self._calico_new_yaml)
        assert res is False
        shutil.copyfile(self._invalid_yaml, self._cni_no_manage_file)
        res = try_upgrade(self._calico_new_yaml, self._calico_new_yaml, self._cni_no_manage_file)
        assert res is False
        os.remove(self._cni_no_manage_file)

    def test_get_version(self):
        """
        Test extracting the Calico version
        """
        res = get_installed_version_of_calico(self._calico_new_yaml)
        assert res == "v3.23.4"

    def test_get_autodetect_method(self):
        """
        Test extracting the IP autodetection method
        """
        res = get_calicos_autodetection_method(self._calico_new_yaml)
        assert res == "first-found"

    def test_patch(self):
        """
        Test patching the manifest
        """
        shutil.copyfile(self._calico_old_yaml, self._calico_old_copy_yaml)
        res = get_calicos_autodetection_method(self._calico_old_copy_yaml)
        assert res == "can-reach=192.168.1.43"
        res = get_calicos_autodetection_method(self._calico_new_yaml)
        assert res == "first-found"
        res = get_installed_version_of_calico(self._calico_old_copy_yaml)
        assert res == "v3.21.1"
        res = try_upgrade(self._calico_old_copy_yaml, self._calico_new_yaml)
        assert os.path.exists(self._calico_old_copy_backup_yaml)
        res = get_installed_version_of_calico(self._calico_old_copy_yaml)
        assert res == "v3.23.4"
        os.remove(self._calico_old_copy_yaml)
        os.remove(self._calico_old_copy_backup_yaml)

    def test_mark(self):
        """
        Test marking the need for reapplying the manifest
        """
        shutil.copyfile(self._calico_old_yaml, self._lock_file)
        mark_apply_needed(self._lock_file)
        assert not os.path.exists(self._lock_file)
