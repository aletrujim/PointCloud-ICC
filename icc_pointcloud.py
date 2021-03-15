#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 10 13:36:04 2020

@author: alexa
"""

import time
from pyntcloud import PyntCloud
import numpy as np
from skimage.measure import EllipseModel
import math
import csv


def scale(data):
    "Escalar los datos (mesh o pointcloud) a la altura medida"
    
    # mover ejes (punto minimo = 0)
    data['x'] = data['x'] - min(data['x'])
    data['y'] = data['y'] - min(data['y'])
    data['z'] = data['z'] - min(data['z'])
    
    # calculo factor de escala
    scale = h / max(data['y'])
    
    # escalar
    data['x'] = data['x']*scale
    data['y'] = data['y']*scale
    data['z'] = data['z']*scale
        
    return data


def roi(data):
    "Region of Interest: filtra los datos del area abdominal"
                
    # Lista de los Y que pertenecen al area abdominal    
    list_y = []
    yi = centroid_y
    yj = centroid_y
    
    for i in range(25):
        yi = yi - 1
        yj = yj + 0.5
        list_y.append(yi)
        list_y.append(yj)
        
    list_y.append(centroid_y)
    list_y.sort()
    
    # datos region de interes
    roi_data = {}  
        
    for y in list_y:
        yselect = data[(data['y'] <= (y + epsilon)) & (data['y'] >= (y - epsilon))]
        yselect.sort_values('y')    
        roi_data[y] = yselect
    
    return roi_data


def ellipse_fitting(data):
    "Ajuste de datos a elipses"
    
    ellipses = {}
    
    for y in data.keys():
        x = data[y]['x']
        z = data[y]['z']
    
        data_points = np.column_stack([x, z])
        
        ell = EllipseModel()
        ell.estimate(data_points)
        
        xc, zc, a, b, theta = ell.params
        ellipses[y] = [a, b]
            
    return ellipses 


def ellipse_perimeter(a,b):
    "Perimetro de una elipse (Ramanujan's approximation)"
    
    perimeter = math.pi*(3*(a+b) - math.sqrt((3*a + b)*(a + 3*b)))
    
    return perimeter


def icc_index(ellipses):
    "Calculo del indice cintura, cadera"
    
    errormin = 100
    yi_waist = 0
    waistmin = 0
    
    yi_hip = 0
    hipmax = 0
    
    for y in ellipses.keys():   
        
        ya, yb = ellipses[y]    
        calculate_waist = ellipse_perimeter(ya, yb)
        calculate_hip = ellipse_perimeter(ya, yb)
                    
        # Cintura minimo error
        error_waist = abs(real_waist - calculate_waist)   
        if error_waist < errormin:
            errormin, yi_waist, waistmin = error_waist, y, calculate_waist
            
        # Cadera perimetro mayor
        if calculate_hip > hipmax and y < centroid_y:
            yi_hip, hipmax = y, calculate_hip
    
    
    print("Calculated Waist  = {}".format(waistmin))
    log.write("Calculated Waist  = {}\r\n".format(waistmin))
    print("Calculated Hip  = {}".format(hipmax))
    log.write("Calculated Hip  = {}\r\n".format(hipmax))
    
    icc = float(waistmin / hipmax)
    print("Calculated ICC index = {}".format(icc))
    log.write("Calculated Hip  = {}\r\n".format(hipmax))
    
    return [yi_waist, waistmin, yi_hip, hipmax]
        


if __name__ == '__main__':
    
    import argparse
   
     # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Measure waist in the PointCloud or Mesh')
    parser.add_argument('--mesh', 
                        required=False,
                        default='data/050_mesh.ply',
                        help='Data Path')
    parser.add_argument('--pointcloud', 
                        required=False,
                        default='data/050.ply',
                        help='Data Path')
    parser.add_argument('--pointc_noseg', 
                        required=False,
                        default='data/050_noseg.ply',
                        help='Data Path')
    parser.add_argument('--hight', 
                        required=False,
                        default='165.5',
                        help='Anthropometric height measurement')
    parser.add_argument('--waist', 
                        required=False,
                        default='72.4',
                        help='Anthropometric waist measurement')
    parser.add_argument('--hip', 
                        required=False,
                        default='95.4',
                        help='Anthropometric hip measurement')
    args = parser.parse_args()
    
    # Log file
    log = open(str("waist_return.txt"), "a+")
    now = time.strftime("%c")
    log.write("\n{}\r\n\n".format(now))
    
    # Antropometric measurements      
    h = float(args.hight)
    real_waist = float(args.waist)
    real_hip = float(args.hip)
    real_icc = real_waist / real_hip
    
    # Epsilon (ancho de la "cinta metrica")
    epsilon = h * 1 / 100
    print("Epsilon(cm) = {}".format(epsilon))
    log.write("Epsilon(cm) = {}\r\n".format(epsilon))
    
    # ICC Mesh
    print("Mesh: {}".format(args.mesh))
    log.write("Mesh: {}\r\n".format(args.mesh))
    
    file_mesh = PyntCloud.from_file(args.mesh)
    mesh = file_mesh.points
    
    scale_mesh = scale(mesh) 
    
    centroid_y = PyntCloud(scale_mesh).centroid[1]

    roi_mesh = roi(scale_mesh) 
    ellipses_mesh = ellipse_fitting(roi_mesh)
    
    ym_waist, mesh_waist, ym_hip, mesh_hip = icc_index(ellipses_mesh)
    mesh_icc = float(mesh_waist / mesh_hip)
    
    # ICC Point Cloud
    print("Point Cloud: {}".format(args.pointcloud))
    log.write("Point Cloud: {}\r\n".format(args.pointcloud))
    
    file_cloud = PyntCloud.from_file(args.pointcloud)
    cloud = file_cloud.points
    
    scale_pointcloud = scale(cloud)
    
    ypc_waist = h - ym_waist #porque el point cloud viene al reves 
    ypc_hip = h - ym_hip
    
    roi_waist = scale_pointcloud[(scale_pointcloud['y'] <= (ypc_waist + epsilon)) & 
                                (scale_pointcloud['y'] >= (ypc_waist - epsilon))]
    roi_hip = scale_pointcloud[(scale_pointcloud['y'] <= (ypc_hip + epsilon)) & 
                                (scale_pointcloud['y'] >= (ypc_hip - epsilon))] 
    
    roi_cloud = {ypc_waist: roi_waist, ypc_hip: roi_hip}
    ellipses_cloud = ellipse_fitting(roi_cloud)
    
    yc_waist, cloud_waist, yc_hip, cloud_hip = icc_index(ellipses_cloud)
    cloud_icc = float(cloud_waist / cloud_hip)
    
    #####
    # ICC Point Cloud NO SEG
    print("Point Cloud: {}".format(args.pointc_noseg))
    log.write("Point Cloud NoSeg: {}\r\n".format(args.pointc_noseg))
    
    file_cloud_noseg = PyntCloud.from_file(args.pointc_noseg)
    cloud_noseg = file_cloud_noseg.points
    
    scale_pointc_noseg = scale(cloud_noseg)
       
    roi_waist_noseg = scale_pointc_noseg[(scale_pointc_noseg['y'] <= (ypc_waist + epsilon)) & 
                                (scale_pointc_noseg['y'] >= (ypc_waist - epsilon))]
    roi_hip_noseg = scale_pointc_noseg[(scale_pointc_noseg['y'] <= (ypc_hip + epsilon)) & 
                                (scale_pointc_noseg['y'] >= (ypc_hip - epsilon))] 
    
    roi_cloud_noseg = {ypc_waist: roi_waist_noseg, ypc_hip: roi_hip_noseg}
    ellipses_cloud_noseg = ellipse_fitting(roi_cloud_noseg)
    
    yc_waist_noseg, cloud_waist_noseg, yc_hip_noseg, cloud_hip_noseg = icc_index(ellipses_cloud_noseg)
    cloud_icc_noseg = float(cloud_waist_noseg / cloud_hip_noseg)
    
    #####
    

    # csv file
    with open('icc_return.csv', 'a+', newline='') as csv_file:
        writer = csv.writer(csv_file)
        #writer.writerow(["Mesh", "PointCloud", "Hight",
        #                 "Waist", "Mesh Waist", "PointCloud Waist", "PointC-NoSeg Waist",
        #                 "Hip", "Mesh Hip", "PointCloud Hip", "PointC-NoSeg Hip",
        #                 "ICC", "Mesh ICC", "PointCloud ICC", "PointC-NoSeg ICC"])
        writer.writerow([args.mesh, args.pointcloud, h,
                         real_waist, mesh_waist, cloud_waist, cloud_waist_noseg,
                         real_hip, mesh_hip, cloud_hip, cloud_hip_noseg,
                         real_icc, mesh_icc, cloud_icc, cloud_icc_noseg])
    
    log.close()
    print("end")