# FILE SOURCE: https://github.com/apacelus/python-os-functions
from pathlib import Path
from time import sleep
from threading import Thread
import subprocess

verbose = False


#######################################################################################
#                               PATHLIB FUNCTIONS                                     #
#######################################################################################
# unlink all files in a directory and remove the directory
def rmdir(rm_dir: str, keep_dir: bool = True) -> None:
    def unlink_files(path_to_rm: Path) -> None:
        try:
            for file in path_to_rm.iterdir():
                if file.is_file():
                    file.unlink()
                else:
                    unlink_files(path_to_rm)
        except FileNotFoundError:
            print(f"No such file or directory: {path_to_rm.absolute().as_posix()}, ignoring")
            return

    # convert string to Path object
    rm_dir_as_path = Path(rm_dir)
    try:
        unlink_files(rm_dir_as_path)
    except RecursionError:  # python doesn't work for folders with a lot of subfolders
        print("\033[93m" + f"Failed to remove {rm_dir} with python, using bash" + "\033[0m")
        bash(f"rm -rf {rm_dir_as_path.absolute().as_posix()}")
    # Remove emtpy directory
    if not keep_dir:
        try:
            rm_dir_as_path.rmdir()
        except FileNotFoundError:  # Directory doesn't exist, because bash was used
            return


# remove a single file
def rmfile(file: str, force: bool = False) -> None:
    if force:
        Path(file).unlink(missing_ok=True)
    file_as_path = Path(file)
    if file_as_path.exists():
        file_as_path.unlink()


# make directory
def mkdir(mk_dir: str, create_parents: bool = False) -> None:
    mk_dir_as_path = Path(mk_dir)
    if not mk_dir_as_path.exists():
        mk_dir_as_path.mkdir(parents=create_parents)


def path_exists(path_str: str) -> bool:
    return Path(path_str).exists()


def get_full_path(path_str: str) -> str:
    return Path(path_str).absolute().as_posix()


# recursively copy files from a dir into another dir
def cpdir(src_as_str: str, dst_as_string: str) -> None:  # dst_dir must be a full path, including the new dir name
    def copy_files(src: Path, dst: Path) -> None:
        # create dst dir if it doesn't exist
        print(f"Copying {src} to {dst}")
        mkdir(dst.absolute().as_posix(), create_parents=True)
        for src_file in src.iterdir():
            if src_file.is_file():
                dst_file = dst.joinpath(src_file.stem + src_file.suffix)
                dst_file.write_bytes(src_file.read_bytes())
            elif src_file.is_dir():
                if src_file.exists():
                    new_dst = dst.joinpath(src_file.stem + src_file.suffix)
                    copy_files(src_file, new_dst)
                else:
                    print(f"No such file or directory: {src_file.absolute().as_posix()}, ignoring")

    src_as_path = Path(src_as_str)
    dst_as_path = Path(dst_as_string)
    if src_as_path.exists():
        if not dst_as_path.exists():
            mkdir(dst_as_string)
        # TODO: Fix python copy dir
        '''
        try:
            copy_files(src_as_path, dst_as_path)
        except RecursionError:
            print("\033[93m" + f"Failed to copy {root_src} to {root_dst}, using bash" + "\033[0m")
            bash(f"cp -rp {src_as_path.absolute().as_posix()} {dst_as_path.absolute().as_posix()}")
        '''
        bash(f"cp -rp {src_as_path.absolute().as_posix()}/* {dst_as_path.absolute().as_posix()}")
    else:
        print("Source directory does not exist?")


def cpfile(src: str, dst: str) -> None:  # "/etc/resolv.conf", "/mnt/eupnea/etc/resolv.conf"
    src_as_path = Path(src)
    dst_as_path = Path(dst)
    if src_as_path.exists():
        dst_as_path.write_bytes(src_as_path.read_bytes())
    else:
        print(f"{src} does not exist, ignoring")


#######################################################################################
#                               SUBPROCESS FUNCTIONS                                  #
#######################################################################################

# return the output of a command
def bash(command: str) -> str:
    output = subprocess.check_output(command, shell=True, text=True).strip()
    if verbose:
        print(output)
    return output


#######################################################################################
#                                    MISC STUFF                                       #
#######################################################################################

def set_verbose(new_state: bool) -> None:
    global verbose
    verbose = new_state


def install_build_packages(user_id: str) -> None:
    print_status("Installing: vboot, cgpt, parted")

    # check if packages are already installed
    if path_exists("/usr/bin/vbutil_kernel") and path_exists("/usr/bin/cgpt") and path_exists("/usr/sbin/parted"):
        print_status("Packages already installed")
        return

    if path_exists("/usr/bin/apt"):  # Ubuntu + debian
        bash("apt-get install cgpt vboot-kernel-utils parted -y")
    elif path_exists("/usr/bin/pacman"):  # Arch
        # remove old files if present
        rmdir("/tmp/eupnea-packages/cgpt-bin", keep_dir=False)
        rmdir("/tmp/eupnea-packages/vboot-utils", keep_dir=False)
        mkdir("/tmp/eupnea-packages")

        bash("pacman -S --needed base-devel --noconfirm")  # install base-devel for mkpkg

        # clone packages
        bash("git clone https://aur.archlinux.org/cgpt-bin.git /tmp/eupnea-packages/cgpt-bin")
        bash("git clone https://aur.archlinux.org/vboot-utils.git /tmp/eupnea-packages/vboot-utils")
        bash("chmod -R 557 /tmp/eupnea-packages")  # update perms so normal user can access

        # Using custom PKGBUILD, as the one in the AUR is broken
        try:
            cpfile("configs/PKGBUILD", "/tmp/eupnea-packages/cgpt-bin/PKGBUILD")  # config while building
        except FileNotFoundError:
            cpfile("/usr/local/eupnea-configs/PKGBUILD", "/tmp/eupnea-packages/cgpt-bin/PKGBUILD")  # config in Eupnea

        # makepkg wont run as root
        bash(f'su -c "cd /tmp/eupnea-packages/cgpt-bin && makepkg -sirc --noconfirm" {user_id}')
        bash(f'su -c "cd /tmp/eupnea-packages/vboot-utils && makepkg -sirc --noconfirm" {user_id}')

        # install parted
        bash("pacman -S parted --noconfirm")

    elif path_exists("/usr/bin/dnf"):  # Fedora
        bash("dnf install vboot-utils parted --assumeyes")  # cgpt is included in vboot-utils on fedora
    elif path_exists("/usr/bin/zypper"):  # openSUSE
        bash("zypper --non-interactive install vboot parted")


#######################################################################################
#                                    PROCESS MONITOR FUNCTIONS                        #
#######################################################################################
def start_progress(force_show: bool = False) -> None:
    if not force_show and verbose:
        return
    rmfile(".stop_progress")
    Thread(target=__print_progress_dots, daemon=True).start()


def stop_progress(force_show: bool = False) -> None:
    if not force_show and verbose:
        return
    with open(".stop_progress", "w") as file:
        file.write("")
    sleep(3)


def start_download_progress(file_path_str: str) -> None:
    rmfile(".stop_download_progress")
    Thread(target=__print_download_progress, args=(Path(file_path_str),), daemon=True).start()


def stop_download_progress() -> None:
    with open(".stop_download_progress", "w") as file:
        file.write("")
    sleep(1)
    print("\n", end="")


def __print_progress_dots() -> None:  # Do not call this function directly, use start_progress() instead
    while True:
        if not path_exists(".stop_progress"):
            print(".", end="", flush=True)
            sleep(2)
        else:
            return


def __print_download_progress(file_path: Path) -> None:
    while True:
        if not path_exists(".stop_download_progress"):
            try:
                print("\rDownloaded: " + "%.0f" % int(file_path.stat().st_size / 1048576) + "mb", end="", flush=True)
            except FileNotFoundError:
                sleep(0.5)  # in case download hasn't started yet
        else:
            return


#######################################################################################
#                                    PRINT FUNCTIONS                                  #
#######################################################################################

def print_warning(message: str) -> None:
    print("\033[93m" + message + "\033[0m", flush=True)


def print_error(message: str) -> None:
    print("\033[91m" + message + "\033[0m", flush=True)


def print_status(message: str) -> None:
    print("\033[94m" + message + "\033[0m", flush=True)


def print_question(message: str) -> None:
    print("\033[92m" + message + "\033[0m", flush=True)


def print_header(message: str) -> None:
    print("\033[95m" + message + "\033[0m", flush=True)


if __name__ == "__main__":
    print_error("There is nothing to be run in this file!")
