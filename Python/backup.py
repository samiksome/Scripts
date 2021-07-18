import argparse
from datetime import datetime
import filecmp
import hashlib
import json
import os
import random
import shutil

from colorama import Fore, Style
import colorama
import ntsecuritycon as con
from tqdm import tqdm
import win32api
import win32security

ID_ALPHABET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
WD = os.getcwd()
BAK_DIR = '.bak'
BAK_FILES_DIR = os.path.join('.bak', 'files')
SNAPSHOTS_FILE = os.path.join(BAK_DIR, 'snapshots.json')
STORE_INFO_FILE = os.path.join(BAK_DIR, 'store_info.json')
LOCK_FILE = os.path.join(BAK_DIR, 'locked')


def locked():
    """Check whether backup is locked.

    Returns
    -------
    bool
        True is backup is locked, False otherwise.
    """
    return os.path.exists(LOCK_FILE)


def read_file(file_obj, size=1024):
    """Reads a given file in small chunks rather than all at once.

    Parameters
    ----------
    file_obj : _io.BufferedReader
        File object.
    size : int, optional
        Bytes to read at once. (default=1024)

    Yields
    ------
    data : bytes
        Chunk read.
    """
    while True:
        data = file_obj.read(size)

        if not data:
            break

        yield data


def get_files(ignore=True):
    """Get all directories and files in current directory.

    Parameters
    ----------
    ignore : bool
        If True ignore directories/files in ignore list.

    Returns
    -------
    dir_list : list[str]
        List of directories.
    file_list : list[str]
        List of files.
    """
    # Get all directories and files.
    dir_list = []
    file_list = []
    for root, dirs, files in os.walk(WD):
        # Strip DIR prefix from paths.
        dir_list += [os.path.join(root, d)[len(WD)+1:] for d in dirs]
        file_list += [os.path.join(root, f)[len(WD)+1:] for f in files]

    if not ignore:
        return dir_list, file_list

    ignore_dirs = []
    ignore_files = []

    # Always add BAK_DIR to ignore list.
    ignore_dirs.append(BAK_DIR)

    # Add directories and files inside ignored directories to ignore lists as well.
    for dir_path in ignore_dirs:
        for root, dirs, files in os.walk(dir_path):
            ignore_dirs += [os.path.join(root, d) for d in dirs]
            ignore_files += [os.path.join(root, f) for f in files]

    # Remove directories/files in ignore lists.
    dir_list = [d for d in dir_list if d not in ignore_dirs]
    file_list = [f for f in file_list if f not in ignore_files]

    return dir_list, file_list


def add_file(file_path, store_info):
    """Add a file to the file store.

    Parameters
    ----------
    file_path : str
        Path to file.
    store_info : dict
        Info object for the file store.

    Returns
    -------
    file_id : str
        ID of the added file.
    """
    # Check if file already exists in store and return existing id if if does.
    file_sha512sum = hashlib.sha512()
    with open(file_path, 'rb') as file_obj:
        for chunk in read_file(file_obj):
            file_sha512sum.update(chunk)
    file_sha512sum = file_sha512sum.hexdigest()

    file_hashes = store_info['hashes']
    if file_sha512sum in file_hashes:
        for file_id in file_hashes[file_sha512sum]:
            if filecmp.cmp(file_path, os.path.join(BAK_FILES_DIR, file_id), shallow=False):
                return file_id
    else:
        store_info['hashes'][file_sha512sum] = []

    # Otherwise get new file id and copy file to store.
    file_id = ''.join(random.choices(ID_ALPHABET, k=64))
    file_ids = store_info['file_ids']
    while file_id in file_ids:
        file_id = ''.join(random.choices(ID_ALPHABET, k=64))

    shutil.copy(file_path, os.path.join(BAK_FILES_DIR, file_id))
    store_info['file_ids'].append(file_id)
    store_info['hashes'][file_sha512sum].append(file_id)

    return file_id


def get_curr_snapshot():
    """Get current snapshot.

    Returns
    -------
    snapshot : dict
        Current snapshot.
    """
    with open(SNAPSHOTS_FILE, 'r', encoding='utf8') as file_obj:
        snapshots = json.load(file_obj)

    curr_snapshot_id = snapshots['curr_snapshot_id']

    # If no snapshots exist return None.
    if curr_snapshot_id == None:
        return None

    for snapshot in snapshots['snapshots']:
        if snapshot['id'] == curr_snapshot_id:
            return snapshot


def get_changes(snapshot=None):
    """Get changes since provided snapshot.

    Parameters
    ----------
    snapshot : dict, optional
        Snapshot object. If None changes are calculated from current snapshot. (default=None)

    Returns
    -------
    bool
        True if there are changes. False otherwise.
    dirs_added : list[str]
        Directories added.
    dirs_removed : list[str]
        Directories removed.
    files_added : list[str]
        Files added.
    files_removed : list[str]
        Files removed.
    files_modified : list[str]
        Files modified.
    """
    # Get current snapshot if snapshot is None
    if snapshot is None:
        snapshot = get_curr_snapshot()

    # Get list of directories and files.
    dir_list, file_list = get_files()

    # If no snapshot is present treat all directories and files as additions.
    # Should only be called once during initial snapshot.
    if snapshot is None:
        dirs_added = dir_list
        files_added = file_list

        if dirs_added or files_added:
            return True, dirs_added, [], files_added, [], []
        else:
            return False, [], [], [], [], []

    # Find added and removed directories.
    last_dir_list = snapshot['dir_list']
    dirs_added = [d for d in dir_list if d not in last_dir_list]
    dirs_removed = [d for d in last_dir_list if d not in dir_list]

    # Find added, removed and modified files.
    last_file_list = snapshot['file_list']
    files_added = [f for f in file_list if f not in last_file_list]
    files_removed = [f for f in last_file_list if f not in file_list]
    files_modified = []
    for file_path in file_list:
        # Skip added files.
        if file_path in files_added:
            continue

        # If files have equal stats consider them unchanged.
        file_stat = os.stat(file_path)
        file_stat = {
            'mode': file_stat.st_mode,
            'ino': file_stat.st_ino,
            'dev': file_stat.st_dev,
            'nlink': file_stat.st_nlink,
            'size': file_stat.st_size,
            'mtime': file_stat.st_mtime,
            'ctime': file_stat.st_ctime
        }
        last_stat = snapshot['file_info'][file_path]['stat']
        if file_stat == last_stat:
            continue

        # If files are of same size, compare their content.
        last_id = snapshot['file_info'][file_path]['id']
        if (
            file_stat['size'] == last_stat['size']
            and filecmp.cmp(file_path, os.path.join(BAK_FILES_DIR, last_id), shallow=False)
        ):
            continue

        files_modified.append(file_path)

    if dirs_added or dirs_removed or files_added or files_removed or files_modified:
        return True, dirs_added, dirs_removed, files_added, files_removed, files_modified
    else:
        return False, [], [], [], [], []


def init(tag='Initial snapshot.', force=False):
    """Initialize a backup.

    Parameters
    ----------
    tag : str, optional
        Tag for initial snapshot. (default='Initial snapshot.')
    force : bool, optional
        Force creation of backup even if it already exists. (default=False)
    """
    # Check if .bak already exists.
    if os.path.exists(BAK_DIR) and not force:
        print('Cannot initialize backup. Backup already exists.')
        return()
    elif os.path.exists(BAK_DIR) and force:
        print('Removing exisitng backup (--force).')
        shutil.rmtree(BAK_DIR)

    # Intialize backup.
    os.mkdir(BAK_DIR)
    os.mkdir(BAK_FILES_DIR)
    with open(SNAPSHOTS_FILE, 'w', encoding='utf8') as file_obj:
        json.dump({'snapshots': [], 'snapshot_ids': [], 'curr_snapshot_id': 'None'}, file_obj)
    with open(STORE_INFO_FILE, 'w', encoding='utf8') as file_obj:
        json.dump({'file_ids': [], 'hashes': {}}, file_obj)

    # Grant full permissions.
    grant_full_permissions()

    # Take initial snapshot
    snapshot(tag)


def status():
    """Get current status of directory tree."""
    # If backup is locked do nothing.
    if locked():
        print('Operation not permitted. Backup is locked.')
        return()

    # Get changes.
    changed, dirs_added, dirs_removed, files_added, files_removed, files_modified = get_changes()

    if not changed:
        print('No changes.')
        return

    if dirs_added or files_added:
        print('Added:')
        for dir_ in dirs_added:
            print(f'    {Fore.GREEN}{dir_}{Style.RESET_ALL}')
        for file in files_added:
            print(f'    {Fore.GREEN}{file}{Style.RESET_ALL}')
    if dirs_removed or files_removed:
        print('Removed:')
        for dir_ in dirs_removed:
            print(f'    {Fore.RED}{dir_}{Style.RESET_ALL}')
        for file in files_removed:
            print(f'    {Fore.RED}{file}{Style.RESET_ALL}')
    if files_modified:
        print('Modified:')
        for file in files_modified:
            print(f'    {Fore.YELLOW}{file}{Style.RESET_ALL}')


def log():
    """Show a log of all available snapshots."""
    # Load snapshots.
    with open(os.path.join(BAK_DIR, 'snapshots.json'), 'r', encoding='utf8') as file_obj:
        snapshots = json.load(file_obj)['snapshots']

    # Get current snapshot id.
    curr_snapshot_id = get_curr_snapshot()['id']

    print('ID          Time                          Tag')
    for snapshot in snapshots:
        if snapshot['id'] == curr_snapshot_id:
            print(f"{Fore.GREEN}{snapshot['id']}    {snapshot['time']}    {snapshot['tag']}{Style.RESET_ALL}")
        else:
            print(f"{snapshot['id']}    {snapshot['time']}    {snapshot['tag']}")


def snapshot(tag=None):
    """Create a new snapshot of the current state.

    Parameters
    ----------
    tag : str, optional
        Tag for the snapshot. (default=None)
    """
    # If backup is locked do nothing.
    if locked():
        print('Operation not permitted. Backup is locked.')
        return()

    # Get changes.
    changed, _, _, files_added, _, files_modified = get_changes()

    if not changed:
        print('No changes to snapshot.')
        return()

    # Get current snapshot.
    curr_snapshot = get_curr_snapshot()

    # Get list of directories and files.
    dir_list, file_list = get_files()

    # Load json files.
    with open(SNAPSHOTS_FILE, 'r', encoding='utf8') as file_obj:
        snapshots = json.load(file_obj)
    with open(STORE_INFO_FILE, 'r', encoding='utf8') as file_obj:
        store_info = json.load(file_obj)

    # Gather file info.
    file_info = {}
    for file_path in file_list:
        # Add new and modified files to file store. For existing files pull id from current snapshot.
        if file_path in files_added or file_path in files_modified:
            file_id = add_file(file_path, store_info)
        else:
            file_id = curr_snapshot['file_info'][file_path]['id']
        file_stat = os.stat(file_path)
        file_stat = {
            'mode': file_stat.st_mode,
            'ino': file_stat.st_ino,
            'dev': file_stat.st_dev,
            'nlink': file_stat.st_nlink,
            'size': file_stat.st_size,
            'mtime': file_stat.st_mtime,
            'ctime': file_stat.st_ctime
        }
        file_info[file_path] = {'id': file_id, 'stat': file_stat}

    # Get new snapshot id.
    snapshot_id = ''.join(random.choices(ID_ALPHABET, k=8))
    while snapshot_id in snapshots['snapshot_ids']:
        snapshot_id = ''.join(random.choices(ID_ALPHABET, k=8))

    # Create new snapshot.
    time_now = str(datetime.now())
    if tag is None:
        tag = f'Snapshot {time_now}'
    snapshot = {
        'id': snapshot_id,
        'tag': tag,
        'time': time_now,
        'dir_list': dir_list,
        'file_list': file_list,
        'file_info': file_info
    }
    snapshots['snapshot_ids'].append(snapshot_id)
    snapshots['snapshots'].append(snapshot)
    snapshots['curr_snapshot_id'] = snapshot_id

    with open(SNAPSHOTS_FILE, 'w', encoding='utf8') as file_obj:
        json.dump(snapshots, file_obj)
    with open(STORE_INFO_FILE, 'w', encoding='utf8') as file_obj:
        json.dump(store_info, file_obj)


def checkout(snapshot_id):
    """Checkout a particular snapshot.

    Parameters
    ----------
    snapshot_id : str
        ID of the snapshot to checkout.
    """
    # If backup is locked do nothing.
    if locked():
        print('Operation not permitted. Backup is locked.')
        return()

    # Load snapshots json.
    with open(SNAPSHOTS_FILE, 'r', encoding='utf8') as file_obj:
        snapshots = json.load(file_obj)

    if snapshot_id not in snapshots['snapshot_ids']:
        print('Invalid snapshot ID.')
        return

    for snapshot in snapshots['snapshots']:
        if snapshot['id'] == snapshot_id:
            break

    # Check if any there are pending changes.
    changed, _, _, _, _, _ = get_changes()
    if changed:
        print('There are pending changes which will be lost on checkout. Continue (y/N)? ', end='')
        choice = input()
        choice = choice.lower()
        if choice != 'y' and choice != 'yes':
            return

    # Get changes since requested snapshot.
    changed, dirs_added, dirs_removed, files_added, files_removed, files_modified = get_changes(snapshot)

    # If there are no changes simply update current snapshot id.
    if not changed:
        snapshots['curr_snapshot_id'] = snapshot_id
        with open(SNAPSHOTS_FILE, 'w', encoding='utf8') as file_obj:
            json.dump(snapshots, file_obj)
        return

    # Remove added directories and add removed directories.
    for dir_path in dirs_added:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
    for dir_path in dirs_removed:
        os.makedirs(dir_path)

    # Remove added files and add removed and modified files.
    for file_path in files_added:
        if os.path.exists(file_path):
            os.remove(file_path)
    for file_path in files_removed:
        shutil.copy(os.path.join(BAK_FILES_DIR, snapshot['file_info'][file_path]['id']), file_path)
    for file_path in files_modified:
        shutil.copy(os.path.join(BAK_FILES_DIR, snapshot['file_info'][file_path]['id']), file_path)

    # Update current snapshot id.
    snapshots['curr_snapshot_id'] = snapshot_id
    with open(SNAPSHOTS_FILE, 'w', encoding='utf8') as file_obj:
        json.dump(snapshots, file_obj)

    print(f'Checked out snapshot {snapshot_id}.')


def grant_full_permissions():
    """Grant full permission to user."""
    # Get list of directories and files.
    dir_list, file_list = get_files(ignore=False)

    # Get SID for everyone.
    user, _, _ = win32security.LookupAccountName('', win32api.GetUserName())

    # Apply to working directory as well.
    sdesc = win32security.GetFileSecurity(WD, win32security.DACL_SECURITY_INFORMATION)
    dacl = win32security.ACL()
    dacl.AddAccessAllowedAce(win32security.ACL_REVISION, con.GENERIC_ALL, user)
    sdesc.SetSecurityDescriptorDacl(1, dacl, 0)
    win32security.SetFileSecurity(WD, win32security.DACL_SECURITY_INFORMATION, sdesc)

    # Grant full permission to all directories/files.
    for dir_path in dir_list:
        sdesc = win32security.GetFileSecurity(dir_path, win32security.DACL_SECURITY_INFORMATION)
        dacl = win32security.ACL()
        dacl.AddAccessAllowedAce(win32security.ACL_REVISION, con.GENERIC_ALL, user)
        sdesc.SetSecurityDescriptorDacl(1, dacl, 0)
        win32security.SetFileSecurity(dir_path, win32security.DACL_SECURITY_INFORMATION, sdesc)
    for file_path in file_list:
        sdesc = win32security.GetFileSecurity(file_path, win32security.DACL_SECURITY_INFORMATION)
        dacl = win32security.ACL()
        dacl.AddAccessAllowedAce(win32security.ACL_REVISION, con.GENERIC_ALL, user)
        sdesc.SetSecurityDescriptorDacl(1, dacl, 0)
        win32security.SetFileSecurity(file_path, win32security.DACL_SECURITY_INFORMATION, sdesc)


def restrict_permissions():
    """Restrict permission so that only reading and executing is allowed."""
    # Get list of directories and files.
    dir_list, file_list = get_files()
    dir_list = dir_list[::-1]
    file_list = file_list[::-1]

    # Get SID for user.
    everyone, _, _ = win32security.LookupAccountName('', 'Everyone')

    # Restrict permissions of all files/directories.
    for file_path in file_list:
        sdesc = win32security.GetFileSecurity(file_path, win32security.DACL_SECURITY_INFORMATION)
        dacl = win32security.ACL()
        dacl.AddAccessAllowedAce(win32security.ACL_REVISION, con.GENERIC_READ | con.GENERIC_EXECUTE, everyone)
        sdesc.SetSecurityDescriptorDacl(1, dacl, 0)
        win32security.SetFileSecurity(file_path, win32security.DACL_SECURITY_INFORMATION, sdesc)
    for dir_path in dir_list:
        sdesc = win32security.GetFileSecurity(dir_path, win32security.DACL_SECURITY_INFORMATION)
        dacl = win32security.ACL()
        dacl.AddAccessAllowedAce(win32security.ACL_REVISION, con.GENERIC_READ | con.GENERIC_EXECUTE, everyone)
        sdesc.SetSecurityDescriptorDacl(1, dacl, 0)
        win32security.SetFileSecurity(dir_path, win32security.DACL_SECURITY_INFORMATION, sdesc)

    # Apply to working directory as well.
    sdesc = win32security.GetFileSecurity(WD, win32security.DACL_SECURITY_INFORMATION)
    dacl = win32security.ACL()
    dacl.AddAccessAllowedAce(win32security.ACL_REVISION, con.GENERIC_READ | con.GENERIC_EXECUTE, everyone)
    sdesc.SetSecurityDescriptorDacl(1, dacl, 0)
    win32security.SetFileSecurity(WD, win32security.DACL_SECURITY_INFORMATION, sdesc)


def lock():
    """Lock the backup."""
    # If backup is locked do nothing.
    if locked():
        print('Backup is already locked.')
        return()

    # Check if any there are pending changes.
    changed, _, _, _, _, _ = get_changes()
    if changed:
        print('Cannot lock while there are pending changes.')
        return

    # Delete files current present.
    curr_snapshot = get_curr_snapshot()
    _, file_list = get_files()
    for file_path in file_list:
        file_store_path = os.path.join(BAK_FILES_DIR, curr_snapshot['file_info'][file_path]['id'])
        if os.path.exists(file_store_path):
            os.remove(file_store_path)

    # Restrict permissions.
    restrict_permissions()

    # Write file indicating backup is locked.
    with open(LOCK_FILE, 'wb') as file_obj:
        file_obj.write(b'')


def unlock():
    """Unlock the backup."""
    # If backup is unlocked do nothing.
    if not locked():
        print('Backup is already unlocked.')
        return()

    # Copy files currently present.
    curr_snapshot = get_curr_snapshot()
    _, file_list = get_files()
    for file_path in file_list:
        file_store_path = os.path.join(BAK_FILES_DIR, curr_snapshot['file_info'][file_path]['id'])
        if not os.path.exists(file_store_path):
            shutil.copy(file_path, file_store_path)

    # Grant full permissions.
    grant_full_permissions()

    # Delete lock file.
    os.remove(LOCK_FILE)


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    parser_init = subparsers.add_parser('init', help='Initialize a backup.')
    parser_init.add_argument('-t', '--tag', help='Initial snapshot tag.', default='Initial snapshot.')
    parser_init.add_argument('-f', '--force', help='Overwriting existing backup.', action='store_true')

    subparsers.add_parser('status', help='Show current status.')
    subparsers.add_parser('log', help='Show snapshot log.')

    parser_snapshot = subparsers.add_parser('snapshot', help='Create a snapshot.')
    parser_snapshot.add_argument('-t', '--tag', help='Snapshot tag.', default=None)

    parser_checkout = subparsers.add_parser('checkout', help='Checkout a snapshot.')
    parser_checkout.add_argument('snapshot_id', help='ID of snapshot to checkout.')

    subparsers.add_parser('lock', help='Lock backup.')
    subparsers.add_parser('unlock', help='Unlock backup.')

    args = parser.parse_args()

    colorama.init()

    if args.command == 'init':
        init(args.tag, args.force)
    elif args.command == 'status':
        status()
    elif args.command == 'log':
        log()
    elif args.command == 'snapshot':
        snapshot(args.tag)
    elif args.command == 'checkout':
        checkout(args.snapshot_id)
    elif args.command == 'lock':
        lock()
    elif args.command == 'unlock':
        unlock()

    colorama.deinit()


if __name__ == '__main__':
    main()
