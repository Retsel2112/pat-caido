import os
import sqlite3
from urllib.request import pathname2url

class CaidoUtil:

    def __init__(self, caido_home=None):
        self.data_path = caido_home
        if not caido_home:
            self.data_path = self.get_data_path()
        db_file = os.path.join(self.data_path, 'projects.db')
        db_uri = 'file:{}?mode=r'.format(pathname2url(db_file))
        # Use uri-like path to prevent file creation
        try:
            self.db = sqlite3.connect(db_file, uri=True)
        except sqlite3.OperationalError:
            #missing DB
            self.data_path = None
            self.db = None
            raise

    def get_data_path(self):
        """Expand the home directory and look for the caido storage location"""
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
        # Get active projects from sqlite
        cur = self.db.cursor()
        res = cur.execute("SELECT id, name FROM projects")
        loft =  res.fetchall()
        results = []
        for row in loft:
            results.append({'id': row[0], 'name': row[1]})
        return results






#get "archived" projects





#archive active project
##determine uuid for name
##compress to name-uuid.tgz
##optional: remove original directory recursively



#unarchive project
##optional check for two existing active projects
##grab name-uuid.tgz file
##uncompress to uuid/



#remove archived project
#(helper, mostly)
##grab name-uuid.tgz file
##?
##delete it




#include an option for --data-path
