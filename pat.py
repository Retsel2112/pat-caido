#!/usr/bin/env python
import argparse
import os
import shutil
import sqlite3
import sys
import tarfile
from urllib.request import pathname2url

class CaidoUtil:

    def __init__(self, caido_home=None, read_only=True):
        self.data_path = caido_home
        self.read_only = read_only
        # Lets us reuse the open helper function to reopen r/w
        self.db = None
        if not caido_home:
            self.data_path = self.get_data_path()
        self.project_path = os.path.join(self.data_path, 'projects')
        self.db_file = os.path.join(self.data_path, 'projects.db')
        self.__open_db()

    def __open_db(self):
        ''' Open or reopen the DB at db_file, based on current state of read_only'''
        if self.db != None:
            self.db.close()
            self.db = None
        if self.read_only:
            db_uri = 'file:{}?mode=r'.format(pathname2url(self.db_file))
        else:
            db_uri = 'file:{}?mode=rw'.format(pathname2url(self.db_file))
        # Use uri-like path to prevent file creation
        try:
            self.db = sqlite3.connect(self.db_file, uri=True)
        except sqlite3.OperationalError:
            #missing DB
            self.data_path = None
            self.db = None
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

    def get_active_projects(self):
        ''' Get active projects from sqlite'''
        cur = self.db.cursor()
        res = cur.execute("SELECT id, name FROM projects")
        loft =  res.fetchall()
        results = []
        for row in loft:
            # "archived" projects w/o a Caido launch will still be in the DB
            # remove results without project folders
            print(os.path.join(self.project_path, row[0]))
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
        for ap in candidates:
            if ap['name'] == name:
                return os.path.join(self.project_path, ap['id'])
        return None
    
    def get_archive_file_by_id(self, projectid):
        ''' Look up the path for an archived project by ID'''
        dlist = os.listdir(self.project_path)
        for fname in dlist:
            if fname.endswith('.tgz'):
                fnparts = fname[:-4].rsplit('-',5)
                if len(fnparts) == 6:
                    found_id = fnparts[1:]
                    found_name = fnparts[0]
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
                    found_id = fnparts[1:]
                    found_name = fnparts[0]
                    if name == found_name:
                        return fname
        return None
    
    def get_archive_directory(self):
        ''' Default archive directory is same as project path, but reasonable to be changed'''
        return self.project_path

    def db_add(self):
        pass

    def db_remove(self):
        pass


#remove archived project
#(helper, mostly)
##grab name-uuid.tgz file
##?
##delete it




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
    cutil = CaidoUtil(read_only = args.modify)
    if args.operation == 'list':
        active = cutil.get_active_projects()
        archived = cutil.get_archived_projects()
        print('Active Workspaces:')
        for ap in active:
            print('{name} ({projectid})'.format(name=ap['name'], projectid=ap['id']))
        print('')
        print('-------------------')
        print('Archived Workspaces:')
        for ap in archived:
            print('{name} ({projectid})'.format(name=ap['name'], projectid=ap['id']))
        print('')
    else:
        if args.wsname == None:
            print('error: operation requires a workspace name')
            sys.exit(1)
        if args.operation == 'archive':
            # It's about here where I wonder if I should have {name: id} instead 
            # Shouldn't be a problem even to linear search the restore list
            #   even if it has a handful of archived projects.
            active = cutil.get_active_projects()
            archive_target = None
            for ap in active:
                if ap['name'] == args.wsname:
                    archive_target = ap
                    break
            else:
                print('error: unable to find workspace')
                sys.exit(2)
            # archive the folder in the uuid directory
            tgz_name = '%s-%s.tgz' % (archive_target['name'], archive_target['id'])
            tgz_path = os.path.join(cutil.get_archive_directory(), tgz_name)
            src_directory = cutil.get_project_directory_by_id(archive_target['id'])
            print('Creating archive.')
            print('This may take some time, depending on project size')
            with tarfile.open(tgz_path, "w:gz") as tar:
                tar.add(src_directory, arcname=os.path.basename(src_directory))
            if args.preserve:
                print('Complete.')
            else:
                print('Complete. Removing workspace directory.')
                shutil.rmtree(src_directory)
        elif args.operation == 'restore':
            archived = cutil.get_archived_projects()
            archive_target = None
            for ap in archived:
                if ap['name'] == args.wsname:
                    archive_target = ap
                    break
            else:
                print('error: unable to find workspace archive')
                sys.exit(3)
            # uncompress the archive to the uuid folder name
            # TODO - do we need to jam metadata back into the db?
            tgz_name = '%s-%s.tgz' % (archive_target['name'], archive_target['id'])
            tgz_path = os.path.join(cutil.get_archive_directory(), tgz_name)
            #Shouldn't need more than the project base directory
            dst_directory = cutil.get_project_directory_by_id(archive_target['id'])
            uncomp_directory = os.path.split(dst_directory)[0]
            print('Restoring archive.')
            print('This may take some time, depending on project size')
            with tarfile.open(tgz_path, "r:gz") as tar:
                ### tar.add(src_directory, arcname=os.path.basename(src_directory))
                tar.extractall(path=uncomp_directory)
            if args.preserve:
                print('Complete.')
            else:
                print('Complete. Removing workspace archive.')
                os.path.remove(tgz_path)
            pass
        
