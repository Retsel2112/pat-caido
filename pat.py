#!/usr/bin/env python
"""
Project Archive Tool for Caido Workspaces

List, Archive, and Restore Caido workspaces/projects
Note that, by design, this works best when it modifies the Caido sqlite3 database
...so, at your own risk, and the schema may change.
"""
import argparse
import os
import shutil
import sqlite3
import sys
import tarfile
from urllib.request import pathname2url

class CaidoUtil:
    """ Helper utility for isolating the interaction with Caido's home"""

    def __init__(self, caido_home=None, read_only=True):
        self.data_path = caido_home
        self.read_only = read_only
        # Lets us reuse the open helper function to reopen r/w
        self.db_conn = None
        if not caido_home:
            self.data_path = self.get_data_path()
        self.project_path = os.path.join(self.data_path, 'projects')
        self.db_file = os.path.join(self.data_path, 'projects.db')
        self.__open_db()

    def __del__(self):
        ''' Clean self up'''
        if self.db_conn is not None:
            self.db_conn.close()
        # Everything else should just be boring things we don't care about

    def __open_db(self):
        ''' Open or reopen the DB at db_file, based on current state of read_only'''
        if self.db_conn is not None:
            self.db_conn.close()
            self.db_conn = None
        path_as_url = pathname2url(self.db_file)
        if self.read_only:
            db_uri = f'file:{path_as_url}?mode=ro'
        else:
            db_uri = f'file:{path_as_url}?mode=rw'
        # Use uri-like path to prevent file creation
        try:
            self.db_conn = sqlite3.connect(db_uri, uri=True)
        except sqlite3.OperationalError:
            # missing DB
            self.data_path = None
            self.db_conn = None
            raise

    def get_data_path(self):
        ''' Expand the home directory and look for the caido storage location'''
        userhome = os.path.expanduser('~')
        # Linux?
        testpath = os.path.join(userhome, '.local', 'share', 'caido')
        if os.path.exists(testpath):
            return testpath
        # Mac?
        testpath = os.path.join(userhome, 'Library', 'Application Support', 'io.caido.Caido')
        if os.path.exists(testpath):
            return testpath
        # Windows?
        testpath = os.path.join(userhome, 'caido', 'Caido', 'data')
        if os.path.exists(testpath):
            return testpath
        return None

    def get_active_projects(self):
        ''' Get active projects from sqlite'''
        cur = self.db_conn.cursor()
        res = cur.execute("SELECT id, name FROM projects")
        loft =  res.fetchall()
        results = []
        for row in loft:
            # "archived" projects w/o a Caido launch will still be in the DB
            # remove results without project folders
            # print(os.path.join(self.project_path, row[0]))
            if os.path.isdir(os.path.join(self.project_path, row[0])):
                results.append({'id': row[0], 'name': row[1]})
        return results

    def get_archived_projects(self):
        ''' Get "archived" projects - tgz files like NAME-UUID.tgz in the data path'''
        dlist = os.listdir(self.project_path)
        archived_projects = []
        for fname in dlist:
            if fname.endswith('.tgz'):
                fnparts = fname[:-4].rsplit('-',5)
                if len(fnparts) == 6:
                    archived_projects.append({'id': '-'.join(fnparts[1:]), 'name': fnparts[0]})
        return archived_projects

    def get_project_directory_by_id(self, projectid):
        ''' Return the full path for a provided project ID. Does not verify existence.'''
        return os.path.join(self.project_path, projectid)

    def get_project_directory_by_name(self, name):
        ''' Return the full path for a provided project name. Requires existence.'''
        candidates = self.get_active_projects()
        for candp in candidates:
            if candp['name'] == name:
                return os.path.join(self.project_path, candp['id'])
        return None

    def get_archive_file_by_id(self, projectid):
        ''' Look up the path for an archived project by ID'''
        dlist = os.listdir(self.project_path)
        for fname in dlist:
            if fname.endswith('.tgz'):
                fnparts = fname[:-4].rsplit('-',5)
                if len(fnparts) == 6:
                    found_id = fnparts[1:]
                    #found_name = fnparts[0]
                    if projectid == found_id:
                        return fname
        return None

    def get_archive_file_by_name(self, name):
        ''' Look up the path for an archived project name'''
        dlist = os.listdir(self.project_path)
        for fname in dlist:
            if fname.endswith('.tgz'):
                fnparts = fname[:-4].rsplit('-',5)
                if len(fnparts) == 6:
                    #found_id = fnparts[1:]
                    found_name = fnparts[0]
                    if name == found_name:
                        return fname
        return None

    def get_archive_directory(self):
        ''' Default archive directory is same as project path, but reasonable to be changed'''
        return self.project_path

    # CREATE TABLE IF NOT EXISTS "projects" (
    #  id text NOT NULL PRIMARY KEY,
    #  name text NOT NULL,
    #  version text NOT NULL,
    #  created_at datetime NOT NULL,
    #  updated_at datetime NOT NULL,
    #  "status" TEXT NOT NULL DEFAULT 'ready',
    #  selected_at datetime);
    def db_add(self, projectid):
        ''' Read the project config to re-insert the project record'''
        src_file = os.path.join(self.get_project_directory_by_id(projectid), 'metadata.txt')
        cur = self.db_conn.cursor()
        with open(src_file, 'rt', encoding='utf8') as fin:
            lines = fin.read()
            parts = lines.strip().split('\n')
            # print(parts)
            try:
                _ = cur.execute('INSERT INTO projects \
                        (id, name, version, created_at, updated_at, status, selected_at) \
                        VALUES (?,?,?,?,?,?,?)', parts)
                self.db_conn.commit()
            except sqlite3.IntegrityError:
                print('Project name already found in DB. Not able to INSERT record.')

    def db_remove(self, projectid):
        ''' Remove the project from the db, based on project ID'''
        cur = self.db_conn.cursor()
        # I don't like testing this part.
        _ = cur.execute('DELETE FROM projects WHERE id = ?', (projectid,))
        self.db_conn.commit()

    def db_record(self, projectid):
        ''' Create the project config txt file in the project directory from the DB record'''
        cur = self.db_conn.cursor()
        _ = cur.execute('SELECT id, name, version, created_at, updated_at, status, selected_at \
                FROM projects WHERE id = ?', (projectid,))
        result_record = cur.fetchone()
        # Maybe add a 'verbose' flag at some point.
        #print(result_record)
        dest_dir = self.get_project_directory_by_id(projectid)
        dest_file = os.path.join(dest_dir, 'metadata.txt')
        with open(dest_file, 'wt', encoding='utf8') as fout:
            for rec in result_record:
                fout.write(rec)
                fout.write('\n')



#include an option for --data-path
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            prog='pat-caido',
            description='Project Archive Tool for Caido Workspaces',
            epilog='')
    parser.add_argument('operation', choices=['list', 'archive', 'restore'])
    parser.add_argument('wsname', default=None, nargs='?')
    parser.add_argument('-p', '--preserve', action='store_true',
            help='Preserve original content (do not delete workspace/archive)')
    parser.add_argument('-m', '--modify', action='store_true',
            help='Modify the Caido projects.db file to reflect changes')
    args = parser.parse_args()
    cutil = CaidoUtil(read_only = not args.modify)
    if args.operation == 'list':
        active = cutil.get_active_projects()
        archived = cutil.get_archived_projects()
        print('Active Workspaces:')
        for acp in active:
            print(f'{acp["name"]} ({acp["id"]})')
        print('')
        print('-------------------')
        print('Archived Workspaces:')
        for arp in archived:
            print(f'{arp["name"]} ({arp["id"]})')
        print('')
    else:
        if args.wsname is None:
            print('error: operation requires a workspace name')
            sys.exit(1)
        if args.operation == 'archive':
            # It's about here where I wonder if I should have {name: id} instead
            # Shouldn't be a problem even to linear search the restore list
            #   even if it has a handful of archived projects.
            active = cutil.get_active_projects()
            archive_target = None
            for acp in active:
                if acp['name'] == args.wsname:
                    archive_target = acp
                    break
            else:
                print('error: unable to find workspace')
                sys.exit(2)
            # archive the folder in the uuid directory
            tgz_name = f'{archive_target["name"]}-{archive_target["id"]}.tgz'
            tgz_path = os.path.join(cutil.get_archive_directory(), tgz_name)
            src_directory = cutil.get_project_directory_by_id(archive_target['id'])
            cutil.db_record(archive_target['id'])
            print('Creating archive.')
            print('This may take some time, depending on project size')
            with tarfile.open(tgz_path, "w:gz") as tar:
                tar.add(src_directory, arcname=os.path.basename(src_directory))
            if args.preserve:
                print('Complete.')
            else:
                print('Complete. Removing workspace directory.')
                cutil.db_remove(archive_target['id'])
                shutil.rmtree(src_directory)
        elif args.operation == 'restore':
            archived = cutil.get_archived_projects()
            archive_target = None
            for arp in archived:
                if arp['name'] == args.wsname:
                    archive_target = arp
                    break
            else:
                print('error: unable to find workspace archive')
                sys.exit(3)
            # uncompress the archive to the uuid folder name
            tgz_name = f'{archive_target["name"]}-{archive_target["id"]}.tgz'
            tgz_path = os.path.join(cutil.get_archive_directory(), tgz_name)
            # Shouldn't need more than the project base directory
            dst_directory = cutil.get_project_directory_by_id(archive_target['id'])
            uncomp_directory = os.path.split(dst_directory)[0]
            print('Restoring archive.')
            print('This may take some time, depending on project size')
            with tarfile.open(tgz_path, "r:gz") as tar:
                ### tar.add(src_directory, arcname=os.path.basename(src_directory))
                tar.extractall(path=uncomp_directory)
            cutil.db_add(archive_target['id'])
            if args.preserve:
                print('Complete.')
            else:
                print('Complete. Removing workspace archive.')
                os.remove(tgz_path)
