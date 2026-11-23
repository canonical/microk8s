import io
import tarfile

import pytest

from common.utils import safe_extract


def build_tar(path, entries):
    """Create a tar archive from (type, name, payload) tuples."""
    with tarfile.open(path, "w:gz") as tar:
        for entry in entries:
            kind, name = entry[0], entry[1]
            info = tarfile.TarInfo(name)
            if kind == "file":
                data = entry[2].encode()
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            elif kind == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = entry[2]
                tar.addfile(info)
            elif kind == "hardlink":
                info.type = tarfile.LNKTYPE
                info.linkname = entry[2]
                tar.addfile(info)
            elif kind == "fifo":
                info.type = tarfile.FIFOTYPE
                tar.addfile(info)
            else:
                raise ValueError("unknown entry type {}".format(kind))


def extract(archive, destination):
    with tarfile.open(archive, "r:gz") as tar:
        safe_extract(tar, path=str(destination))


def test_extract_regular_file(tmp_path):
    archive = tmp_path / "backup.tar.gz"
    build_tar(archive, [("file", "data/backup.db", "payload")])

    destination = tmp_path / "destination"
    destination.mkdir()
    extract(archive, destination)

    assert (destination / "data" / "backup.db").read_text() == "payload"


def test_reject_member_outside_destination(tmp_path):
    archive = tmp_path / "backup.tar.gz"
    # The sibling directory shares the destination prefix, which the previous
    # os.path.commonprefix based check treated as being inside the destination.
    build_tar(archive, [("file", "../destination-evil/pwned", "owned")])

    destination = tmp_path / "destination"
    destination.mkdir()
    with pytest.raises(Exception, match="Path Traversal"):
        extract(archive, destination)

    assert not (tmp_path / "destination-evil" / "pwned").exists()


def test_reject_absolute_member_path(tmp_path):
    archive = tmp_path / "backup.tar.gz"
    build_tar(archive, [("file", str(tmp_path / "pwned"), "owned")])

    destination = tmp_path / "destination"
    destination.mkdir()
    with pytest.raises(Exception, match="Path Traversal"):
        extract(archive, destination)

    assert not (tmp_path / "pwned").exists()


def test_reject_symlink_escape(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    archive = tmp_path / "backup.tar.gz"
    build_tar(
        archive,
        [
            ("symlink", "escape", str(outside)),
            ("file", "escape/pwned", "owned"),
        ],
    )

    destination = tmp_path / "destination"
    destination.mkdir()
    with pytest.raises(Exception, match="link"):
        extract(archive, destination)

    assert not (outside / "pwned").exists()


def test_reject_hardlink(tmp_path):
    archive = tmp_path / "backup.tar.gz"
    build_tar(
        archive,
        [
            ("file", "backup.db", "payload"),
            ("hardlink", "backup-link.db", "backup.db"),
        ],
    )

    destination = tmp_path / "destination"
    destination.mkdir()
    with pytest.raises(Exception, match="link"):
        extract(archive, destination)


def test_extract_selected_members_from_iterator(tmp_path):
    archive = tmp_path / "backup.tar.gz"
    build_tar(archive, [("file", "one.txt", "one"), ("file", "two.txt", "two")])

    destination = tmp_path / "destination"
    destination.mkdir()
    with tarfile.open(archive, "r:gz") as tar:
        # members may be any iterable accepted by extractall().
        selected = (member for member in tar.getmembers() if member.name == "one.txt")
        safe_extract(tar, path=str(destination), members=selected)

    assert (destination / "one.txt").read_text() == "one"
    assert not (destination / "two.txt").exists()


def test_reject_device_file(tmp_path):
    archive = tmp_path / "backup.tar.gz"
    build_tar(archive, [("fifo", "pipe")])

    destination = tmp_path / "destination"
    destination.mkdir()
    with pytest.raises(Exception, match="device"):
        extract(archive, destination)
