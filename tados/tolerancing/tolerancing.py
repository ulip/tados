# -*- coding: utf-8 -*-
"""
Created on Fri Apr 08 17:47:19 2016

@author: Hambach
"""
from __future__ import print_function

import numpy as np

class ToleranceSystem(object):
  """
  Helper class for tolerancing the system
  """

  def __init__(self,hDDE,filename):
    self.hDDE=hDDE;
    self.ln = hDDE.link;
    self.filename=filename;
    self.reset();
    # initial orientation and position of each surface
    self.__R0, self.__t0 = self.__get_surface_coordinates();        
      
  def reset(self):
    " reset system to original state"
    self.hDDE.load(self.filename);
    self.ln.zPushLens(1);

    self.numSurf = self.ln.zGetNumSurf();
    # index arrays for conversion between real and all surfaces
    self.__isRealSurf = np.ones(self.numSurf,dtype=bool);
    self.__real2all = np.arange(self.numSurf);
    self.__all2real = np.arange(self.numSurf);    


  def get_orig_surface(self,orig_surface_index):
    """
    returns index of given surface in distorted system (which includes dummy surfaces)
      orig_surface_index ... index of surface in initial system
    """
    return self.__real2all[orig_surface_index];    
  
  def __get_surface_coordinates(self):
    """
    returns for each surface in the system, the global rotation matrix 
           | R11  R12  R13 |                 | X |
      R =  | R21  R22  R23 | and shift   t = | Y |
           | R31  R32  R33 |                 | Z |
    Returns: (R,t) of shape (numSurf,3,3) and (numSurf,3) respectively
    """    
    coords = [ self.ln.zGetGlobalMatrix(s) for s in self.__real2all]
    coords = np.asarray(coords);
    R = coords[:,0:9].reshape(self.numSurf,3,3);
    t = coords[:,9:12];
    return R,t
    
  def __get_surface_comments(self):
    return [ self.ln.zGetComment(s) for s in self.__real2all];
    
  def __register_dummy_surfaces(self,surf):
    """ 
    register dummy surfaces for keeping track of real surfaces 
    in optical system during tolerancing, use following index arrays
    to convert between real and all surfaces including dummies and coord-breaks:
      __all2real ... converst from surface index to original surface index (or -1)
      __real2all ... gives index of original surface in current system
    """
    # calculate indices where to insert False in __isRealSurf
    insert_at=np.sort(surf)-np.arange(len(surf));
    self.__isRealSurf = np.insert(self.__isRealSurf,insert_at,False);
    numAll = self.__isRealSurf.size;
    self.__all2real= (-1)*np.ones(numAll);
    self.__all2real[self.__isRealSurf]=np.arange(self.numSurf);
    self.__real2all=np.arange(numAll)[self.__isRealSurf]      
    assert(np.all(self.__isRealSurf[list(surf)]==False));
    assert( len(self.__real2all)==self.numSurf );

  
  def print_LDE(self,bShowDummySurfaces=False):
    print(self.ln.ipzGetLDE());

  def print_current_geometric_changes(self):
    """
    print all surfaces that have been decentered or rotated
    """  
    R,t = self.__get_surface_coordinates();
    dR = R - self.__R0; 
    dt = t - self.__t0;
    numSurf = dR.shape[0];
    comment = self.__get_surface_comments();
    
    if np.all(dR==0) and np.all(dt==0):
      print(" system unchanged.")
      return
  
    print("   surface     shift    tilt     comment")
    for s in range(numSurf):
      print("  %2d: "%s, end=' ')
      # check for translation (with precision of 10^-8 lens units)
      x,y,z=np.round(dt[s],decimals=8);
      if   x==0 and y==0 and z==0: print("                    ", end=' ')
      elif x==0 and y==0 and z!=0: print("DZ: %5.3f,          "%z, end=' ')
      elif x==0 and y!=0 and z==0: print("DY: %5.3f,          "%y, end=' ')
      elif x!=0 and y==0 and z==0: print("DX: %5.3f,          "%x, end=' ')
      else:                        print("(%5.2f,%5.2f,%5.2f),"%(x,y,z), end=' ')
      
      # check for rotations (with precision of 10^-8 lens units)
      x,y,z = np.round(np.linalg.norm(dR[s],axis=1),decimals=8);
      if   x==0 and y==0 and z==0: print("    ", end=' ')
      elif x==0:                   print("XROT", end=' ')
      elif x==0 and y!=0 and z==0: print("YROT", end=' ')
      elif x!=0 and y==0 and z==0: print("ZROT", end=' ')
      else:                        print(" ROT", end=' ')
      
      if comment[s]: print("  (%s)"%(comment[s]));
      else: print("")
    
  def tilt_decenter_surface(self,surf,xdec=0.0,ydec=0.0,xtilt=0.0,ytilt=0.0,ztilt=0.0,order=0):
    """
    Wrapper for pyzDDE.zSetSurfaceData. The function tilts/decenters single surface
    by changing the surface data. Assumes that surface is unchanged before.
    """    
    #
    surfNum = self.__real2all[surf];              # calculate real surface indices 
    def apply_surf_parameter(surfNum,code,value): # local help function
      if value==0: return  # do nothing
      assert self.ln.zGetSurfaceData(surfNum,code)==0; # decenter / tilt must be 0 before
      self.ln.zSetSurfaceData(surfNum,code,value);   
    apply_surf_parameter(surfNum,self.ln.SDAT_DCNTR_X_BEFORE,xdec);
    apply_surf_parameter(surfNum,self.ln.SDAT_DCNTR_Y_BEFORE,ydec);
    apply_surf_parameter(surfNum,self.ln.SDAT_TILT_X_BEFORE,xtilt);
    apply_surf_parameter(surfNum,self.ln.SDAT_TILT_Y_BEFORE,ytilt);
    apply_surf_parameter(surfNum,self.ln.SDAT_TILT_Z_BEFORE,ztilt);
    apply_surf_parameter(surfNum,self.ln.SDAT_TILT_DCNTR_ORD_BEFORE,order);
    # After status. 0 for explicit; 1 for pickup current surface; 
    #         2 for reverse current surface; 3 for pickup previous surface; 
    #         4 for reverse previous surface, etc.
    self.ln.zSetSurfaceData(surfNum,self.ln.SDAT_TILT_DCNTR_STAT_AFTER,2); # reverse current surface
    self.ln.zGetUpdate();    
    
  def tilt_decenter_elements(self,firstSurf,lastSurf,**kwargs):
    """
    Wrapper for pyzDDE.zTiltDecenterElements(firstSurf, lastSurf, xdec=0.0, ydec=0.0, 
      xtilt=0.0, ytilt=0.0, ztilt=0.0, order=0, cbComment1=None, cbComment2=None, dummySemiDiaToZero=False)
    The function tilts/decenters optical elements between two surfaces
    by adding appropriate coordinate breaks and dummy surfaces.
    
    returns surface numbers of added surfaces (triple of ints)     
    """
    # calculate real surface indices and check, that there are no
    # coordinate breaks or dummy surfaces between these
    s1,s2 = self.__real2all[[firstSurf,lastSurf]]; 
    if not all(self.__isRealSurf[s1:s2+1]):
      raise RuntimeError("Elements (surface ranges) are not allowed to overlap in tolerancing.");
    added_surf = self.ln.zTiltDecenterElements(s1,s2,**kwargs);
    self.__register_dummy_surfaces(added_surf);
    return added_surf;
    
  def insert_coordinate_break(self,surf,**kwargs):
    """
    Wrapper for pyzDDE.zInsertCoordinateBreak(self, surfNum, xdec=0.0, ydec=0.0, 
      xtilt=0.0, ytilt=0.0,ztilt=0.0, order=0, thick=None, comment=None)
    This function tilts/decenters the coordinate system in front of a given surface
    
    returns surface number of added surface
    """
    # calculate real surface indices and check, that there are no
    # coordinate breaks or dummy surfaces between these
    numSurf = self.__real2all[surf]; 
    self.ln.zInsertCoordinateBreak(numSurf,**kwargs);
    self.__register_dummy_surfaces([numSurf]);
    self.ln.zGetUpdate()
    return numSurf;
    
    
  def change_thickness(self,surf=0,adjust_surf=0,value=0):
    """
    Wrapper for TTHI operand. Change thickness of given surface by a given value 
    in lens units. An adjustment surface can be specified, whose thickness is
    adjusted to compensate the z-shift. All surfaces after the adjustment surface
    will not be altered (imitates the behaviour fo TTHI(n,m).
      surf       ... surface number after which the thickness is changed
      adjust_surf... (opt) adjustment surface, ineffective if surf==adjust_surf
      value      ... thickness variation in lens units
          
    """
    # calculate real surface indices  and check, that there are no
    # coordinate breaks or dummy surfaces between these
    s1,s2 = self.__real2all[[surf,adjust_surf]]; 
    if not all(self.__isRealSurf[s1:s2+1]):
      raise RuntimeError("Elements (surface ranges) are not allowed to overlap in tolerancing.");
    t1=self.ln.zGetThickness(s1);
    self.ln.zSetThickness(s1,value=t1+value);
    if adjust_surf>surf:  
      t2=self.ln.zGetThickness(s2);
      self.ln.zSetThickness(s2,value=t2-value);
    self.ln.zGetUpdate();  


  # Wrapper for simulating ZEMAX operands follow
  def TTHI(self,surf,adjust_surf,val):
    return self.change_thickness(surf,adjust_surf=adjust_surf,value=val);
  def TEDX(self,firstSurf,lastSurf,val,**kwargs):
    return self.tilt_decenter_elements(firstSurf,lastSurf,xdec=val,**kwargs)
  def TEDY(self,firstSurf,lastSurf,val,**kwargs):
    return self.tilt_decenter_elements(firstSurf,lastSurf,ydec=val,**kwargs)
  def TETX(self,firstSurf,lastSurf,val,**kwargs):
    return self.tilt_decenter_elements(firstSurf,lastSurf,xtilt=val,**kwargs)
  def TETY(self,firstSurf,lastSurf,val,**kwargs):
    return self.tilt_decenter_elements(firstSurf,lastSurf,ytilt=val,**kwargs)
  def TETZ(self,firstSurf,lastSurf,val,**kwargs):
    return self.tilt_decenter_elements(firstSurf,lastSurf,ztilt=val,**kwargs)


if __name__ == '__main__':
  import os
  from tados.zemax import dde_link
  
  with dde_link.DDElinkHandler() as hDDE:
    
    # start tolerancing
    filename= os.path.realpath('../../tests/zemax/pupil_slicer.ZMX');
    tol=ToleranceSystem(hDDE,filename);
    tol.print_LDE();
  
    tol.change_thickness(5,12,value=2);
    tol.tilt_decenter_elements(1,3,ydec=0.02);  # [mm]
    tol.TETX(1,3,0.001)
    tol.TTHI(1,2,0.01)
    tol.insert_coordinate_break(10,xdec=-0.01,comment="new CB")
    tol.print_current_geometric_changes();
    
    tol.ln.zPushLens(1); # show changes also in Zemax LDE
    #  changes to system by hand:
    #
    #  ln.zSetSurfaceData(surfNum=5, code=ln.SDAT_THICK, value=2);
    #  TEDY=20./1000;    # [mm=1000um]
    #  ln.zSetSurfaceData(surfNum=1, code=ln.SDAT_DCNTR_Y_BEFORE, value=TEDY);
    #  ln.zSetSurfaceData(surfNum=3, code=ln.SDAT_DCNTR_Y_AFTER, value=-TEDY);
    #
    #  TETX=3./60;  # [deg=60'=17mrad]
    #  ln.zTiltDecenterElements(15,18,xtilt=TETX)
