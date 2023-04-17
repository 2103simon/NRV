"""
Access and modify NRV Parameters
Authors: Florian Kolbl / Roland Giraud / Louis Regnacq / Thomas Couppey
(c) ETIS - University Cergy-Pontoise - CNRS
"""
import configparser
import os
from numpy import pi





class nrv_parameters():
    def __init__(self):
        """
        """
        self.dir_path = os.environ['NRVPATH'] + '/_misc'
        self.config_fname = self.dir_path + '/NRV.ini'

        self.load()

        with open('self.config_fname', 'w') as configfile:
            self.machine_config.write(configfile)
    
    def load(self, fname=None):
        if fname is None:
            fname = self.config_fname

        self.machine_config = configparser.ConfigParser()
        self.machine_config.read(self.config_fname)

        #GMSH
        self.GMSH_Ncores = int(self.machine_config.get('GMSH', 'GMSH_CPU'))
        self.GMSH_Status = self.machine_config.get('GMSH', 'GMSH_STATUS') == 'True'
        #LOG
        self.LOG_Status = self.machine_config.get('LOG', 'LOG_STATUS') == 'True'
        self.VERBOSITY_LEVEL = int(self.machine_config.get('LOG', 'VERBOSITY_LEVEL'))

    def get_nrv_verbosity(self):
        """
        get general verbosity level
        """
        return self.VERBOSITY_LEVEL


    def set_nrv_verbosity(self, i):
        """
        set general verbosity level
        """
        self.VERBOSITY_LEVEL = i


    def get_gmsh_ncore(self):
        """
        get gmsh core number
        """
        return self.GMSH_Ncores

    def set_gmsh_ncore(self,n):
        """
        set gmsh core number
        """
        self.GMSH_Ncores = n

##########################################################################
########################### Parameter singleton ##########################
##########################################################################

NRV_param = nrv_parameters()
