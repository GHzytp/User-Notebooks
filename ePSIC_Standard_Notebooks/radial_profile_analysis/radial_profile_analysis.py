# Atomic structure analysis with radial (azimuthal) average & variance profiles
# Only compatible with the ePSIC data processig workflow
# Jinseok Ryu (jinseok.ryu@diamond.ac.uk or jinseuk56@gmail.com)
# ePSIC, Diamond Light Source
import os
import glob
from scipy.signal import find_peaks
from scipy.ndimage import gaussian_filter
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import py4DSTEM
import hyperspy.api as hs

import tifffile
import matplotlib.gridspec as gridspec
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from matplotlib.colors import ListedColormap
from matplotlib.colors import hsv_to_rgb
from sklearn.decomposition import NMF, PCA
from sklearn.manifold import TSNE
from sklearn.cluster import OPTICS
import ipywidgets as pyw
import time

def find_nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx

class radial_profile_analysis():

    color_rep = ["black", "red", "green", "blue", "orange", "purple", "yellow", "lime", 
             "cyan", "magenta", "lightgray", "peru", "springgreen", "deepskyblue", 
             "hotpink", "darkgray"]

    cm_rep = ['Reds', 'Greens', 'Blues', 'Oranges', 'Purples']
    
    def __init__(self, base_dir, subfolders, profile_length, num_load, 
                 include_key=None, exclude_key=None, limit_scan_region=[1000, 1000], 
                 simult_edx=False, edx_key='', 
                 roll_axis=True, edx_crop=[0, 0], verbose=True):

        edx_split = []
        edx_avg_split = []
        radial_var_split = []
        radial_var_sum_split = []
        pixel_size_split = []
        loaded_data_path = []

        new_process_flag = True
        
        for i, sub in enumerate(subfolders):
            if simult_edx:
                edx_adrs = glob.glob(base_dir+'/'+sub+'/*/EDX/*.rpl', recursive=True)
                if edx_adrs == []:
                    edx_adrs = glob.glob(base_dir+'/'+sub+'/EDX/*.rpl', recursive=True)
                    if edx_adrs == []:
                        edx_adrs = glob.glob(base_dir+'/'+sub+'EDX/*.rpl', recursive=True)
                        if edx_adrs == []:
                            print("Please make sure that the base directory and subfolder name are correct.")
                            return                

            file_adrs = glob.glob(base_dir+'/'+sub+'/*/*/*.hspy', recursive=True)
            if file_adrs == []:
                file_adrs = glob.glob(base_dir+'/'+sub+'/*/*.hspy', recursive=True)
                if file_adrs == []:
                    file_adrs = glob.glob(base_dir+'/'+sub+'/*.hspy', recursive=True)
                    if file_adrs == []:
                        print("Please make sure that the base directory and subfolder name are correct.")
                        return
            
            file_adrs.sort()
            try:
                edx_adrs.sort()

            except:
                print("No EDX files")
        
            if include_key == []:
                key_list = []
                keyword_ = list(exclude_key)
                keyword_.extend(["mean", "max", "bin"])
                for adr in file_adrs:
                    check = []
                    for key in keyword_:
                        if key in adr:
                            check.append(1)
                    if check == []:
                        key_list.append(adr)
                #print(*key_list, sep="\n")
                print("number of data in subfolder '%s'"%sub)
                print(len(key_list))
                key_list = np.asarray(key_list)

                if simult_edx:
                    edx_adrs = np.asarray(edx_adrs)
                    edx_adrs = edx_adrs[:len(key_list)]
            
                if len(key_list) >= num_load:
                    ri = np.random.choice(len(key_list), num_load, replace=False)
                    file_adr_ = key_list[ri]
                    if simult_edx:
                        edx_adr_ = edx_adrs[ri]
                else:
                    file_adr_ = key_list
                    if simult_edx:
                        edx_adr_ = edx_adrs
        
            else:
                file_adr_ = []
                for adr in file_adrs:
                    for key in include_key:
                        if key in adr and "mean" not in adr:
                            file_adr_.append(adr)
                if simult_edx:
                    edx_adr_ = edx_adrs
                print("number of data in subfolder '%s'"%sub)
                print(len(file_adr_))

            edx_tmp_list = []
            edx_avg_list = []
            radial_var_list = []
            avg_radial_var_list = []
            file_adr = []
            pixel_size_list = []
            for e, adr in enumerate(file_adr_):
                data = hs.load(adr)
                print('original profile size = ', data.data.shape[-1])
                file_adr.append(adr)
                data.data = data.data[:, :, :profile_length]
                local_radial_var_sum = data.mean()
                pixel_size_inv_Ang = local_radial_var_sum.axes_manager[-1].scale

                if simult_edx:
                    edx_data = hs.load(edx_adr_[e]).data
                    if roll_axis:
                        edx_data = np.rollaxis(edx_data, 0, 3)[:limit_scan_region[0], :limit_scan_region[1]]
                    edx_data = hs.signals.Signal1D(edx_data)

                if verbose:
                    print("radial profile data information")
                    print(adr)
                    print(data)
                    print(data.axes_manager)
                    if simult_edx:
                        print("EDX data information")
                        print(edx_adr_[e])
                        print(edx_data)
                        print(edx_data.axes_manager)                   

                radial_var_list.append(data)
                avg_radial_var_list.append(local_radial_var_sum.data)
                pixel_size_list.append(pixel_size_inv_Ang)
                if simult_edx:
                    edx_tmp_list.append(edx_data)
                    edx_avg_list.append(edx_data.mean().data)                    
        
            avg_radial_var_list = np.asarray(avg_radial_var_list)
            radial_var_split.append(radial_var_list)
            radial_var_sum_split.append(avg_radial_var_list)
            pixel_size_split.append(pixel_size_list)
        
            loaded_data_path.append(file_adr)

            if simult_edx:
                edx_avg_list = np.asarray(edx_avg_list)
                edx_split.append(edx_tmp_list)
                edx_avg_split.append(edx_avg_list)                

        # mean profile data load
        loaded_data_mean_path = []
        radial_avg_split = []
        radial_avg_sum_split = []
        for i, sub in enumerate(subfolders):
            radial_avg_list = []
            radial_avg_sum_list = []
            loaded_data_mean = []
            for adr in loaded_data_path[i]:
                dir_path = os.path.dirname(adr)
                data_name = os.path.basename(adr).split("_")
                data_name = data_name[0]+'_'+data_name[1]
                
                try:
                    adr_ = dir_path+"/"+data_name+"_"+'azimuthal_mean.hspy'
                    data = hs.load(adr_)
                except:
                    try:
                        adr_ = dir_path+"/"+data_name+"_"+'mean.hspy'
                        data = hs.load(adr_)
                        new_process_flag = False
                    except:
                        print('There is no mean profile data, so it will be replaced with variance profile data')
                        adr_ = dir_path+"/"+data_name+"_"+'variance.hspy'
                        data = hs.load(adr_)
                    
                loaded_data_mean.append(adr_)
                data.data = data.data[:, :, :profile_length]
                local_radial_avg_sum = data.mean()
                radial_avg_list.append(data)
                radial_avg_sum_list.append(local_radial_avg_sum.data)

            loaded_data_mean_path.append(loaded_data_mean)
        
            radial_avg_split.append(radial_avg_list)
            radial_avg_sum_split.append(radial_avg_sum_list)

            self.radial_avg_split = radial_avg_split
            self.radial_avg_sum_split = radial_avg_sum_split

        # aligned center beam image load
        BF_disc_align = []
        for i, sub in enumerate(subfolders):
            BF_disc_list = []
            for adr in loaded_data_path[i]:
                dir_path = os.path.dirname(adr)
                data_name = os.path.basename(adr).split("_")
                data_name = data_name[0]+'_'+data_name[1]
                
                try:
                    adr_ = dir_path+"/"+data_name+"_"+'azimuthal_data_centre.png'
                    data = plt.imread(adr_) 
                except:
                    adr_ = dir_path+"/"+"BF_disc_align_bvm.png"
                    data = plt.imread(adr_) 
                    new_process_flag = False

                BF_disc_list.append(data)
            BF_disc_align.append(BF_disc_list)

        self.pixel_size_inv_Ang = pixel_size_split[0][0]

        self.base_dir = base_dir
        self.subfolders = subfolders
        self.profile_length = profile_length
        self.num_load = num_load
        self.radial_var_split = radial_var_split
        self.radial_var_sum_split = radial_var_sum_split
        self.pixel_size_split = pixel_size_split
        self.edx_split = edx_split
        self.loaded_data_path = loaded_data_path
        self.loaded_data_mean_path = loaded_data_mean_path
        self.BF_disc_align = BF_disc_align
        self.new_process_flag = new_process_flag
        
        print("data loaded.")


    def center_beam_alignment_check(self, crop=[0, -1, 0, -1]):

        self.crop = crop
        top, bottom, left, right = self.crop
        
        for i in range(len(self.subfolders)):
            num_img = len(self.BF_disc_align[i])
            print(num_img)
            grid_size = int(np.around(np.sqrt(num_img)))
            if (num_img - grid_size**2) <= 0 and (num_img - grid_size**2) > -grid_size:
                fig, ax = plt.subplots(grid_size, grid_size, figsize=(12, 12))
            else:
                fig, ax = plt.subplots(grid_size, grid_size+1, figsize=(12, 10))
            for j in range(num_img):
                ax.flat[j].imshow(self.BF_disc_align[i][j][top:bottom, left:right])
                ax.flat[j].set_title(os.path.basename(self.loaded_data_path[i][j])[:15])
                ax.flat[j].axis("off")
            fig.suptitle(self.subfolders[i]+' BF disc align result')
            fig.tight_layout()
            plt.show()

    
    def intensity_integration_image(self):
    
        for i in range(len(self.subfolders)):
            num_img = len(self.radial_avg_split[i])
            grid_size = int(np.around(np.sqrt(num_img)))
            if (num_img - grid_size**2) <= 0 and (num_img - grid_size**2) > -grid_size:
                fig, ax = plt.subplots(grid_size, grid_size, figsize=(12, 12))
            else:
                fig, ax = plt.subplots(grid_size, grid_size+1, figsize=(12, 10))
            for j in range(num_img):
                sum_map = np.sum(self.radial_avg_split[i][j].data, axis=2)
                ax.flat[j].imshow(sum_map, cmap='inferno')
                ax.flat[j].set_title(os.path.basename(self.loaded_data_path[i][j])[:15])
                ax.flat[j].axis("off")
            fig.suptitle(self.subfolders[i]+' sum of intensities map')
            fig.tight_layout()
            plt.show()

    
    def basic_setup(self, str_path, from_unit, to_unit, broadening=0.01, 
                    fill_width=0.1, height=None, width=None, threshold=None, 
                    distance=None, prominence=0.001, visual=True):
        print("Original scattering vector range = [%.6f, %.6f]"%(0, self.profile_length*self.pixel_size_inv_Ang))
        
        self.str_path = str_path
        self.from_unit = from_unit
        self.to_unit = to_unit

        self.from_ind = int(np.around(from_unit/self.pixel_size_inv_Ang))
        self.to_ind = int(np.around(to_unit/self.pixel_size_inv_Ang))
        self.from_ = self.pixel_size_inv_Ang*self.from_ind
        self.to_ = self.pixel_size_inv_Ang*self.to_ind
        self.x_axis = np.linspace(self.from_, self.to_, self.to_ind-self.from_ind)
        print("Selected scattering vector range = [%.6f, %.6f]"%(self.x_axis.min(), self.x_axis.max()))
        print('Reciprocal pixel size : %.6f (original), %.6f (present)'%(self.pixel_size_inv_Ang, self.x_axis[1]-self.x_axis[0]))

        self.range_ind = [self.from_ind, self.to_ind]
        print('Selected scattering vector index range = [%d, %d]'%(self.range_ind[0], self.range_ind[1]))
        
        if str_path != []:
            int_sf = {}
            peak_sf = {}
            for adr in self.str_path:
                str_name = adr.split('/')[-1].split('.')[0]
                crystal = py4DSTEM.process.diffraction.Crystal.from_CIF(adr, conventional_standard_structure=True)
                crystal.calculate_structure_factors(self.to_)
            
                int_sf[str_name] = py4DSTEM.process.diffraction.utils.calc_1D_profile(
                                            self.x_axis,
                                            crystal.g_vec_leng,
                                            crystal.struct_factors_int,
                                            k_broadening=broadening,
                                            int_scale=1.0,
                                            normalize_intensity=True)
                
                peaks = find_peaks(int_sf[str_name], 
                                   height=height, 
                                   width=width, 
                                   threshold=threshold, 
                                   distance=distance, 
                                   prominence=prominence)[0]
                
                peaks = peaks * self.pixel_size_inv_Ang
                peaks = peaks + self.from_

                peak_sf[str_name] = peaks

                if visual:
                    fig, ax = plt.subplots(1, 1, figsize=(8, 6))
                    ax.plot(self.x_axis, int_sf[str_name], 'k-', label=str_name)
                    ax.legend(loc='right')
    
                    for j, peak in enumerate(peaks):
                        if peak >= self.from_ and peak <= self.to_:
                            print("%d peak position (1/Å):\t"%(j+1), peak)
                            ax.axvline(peak, ls=':', lw=1.5, c='r')
                            ax.fill_between([peak-fill_width, peak+fill_width], y1=np.max(int_sf[str_name]), y2=np.min(int_sf[str_name]), alpha=0.5, color='orange')
                            ax.text(peak, 1.0, "%d"%(j+1))
                    
                    fig.tight_layout()
                    plt.show()
            
            if visual:
                int_sf["sum_of_all"] = np.sum(list(int_sf.values()), axis=0)
                fig, ax = plt.subplots(1, 1, figsize=(8, 6))
                ax.plot(self.x_axis, int_sf["sum_of_all"], 'k-', label="sum of all")
                ax.legend(loc='right')
                fig.tight_layout()
                plt.show()
    
            self.int_sf = int_sf
            self.peak_sf = peak_sf
    
            print('structure name')
            print(*int_sf.keys(), sep="\n")
    
    
    def sum_radial_profile(self, str_name=None, profile_type="variance"):            

        fig_tot, ax_tot = plt.subplots(2, 1, figsize=(8, 12))
        
        for i in range(len(self.subfolders)):
            num_img = len(self.radial_var_sum_split[i])
            grid_size = int(np.around(np.sqrt(num_img)))
            
            fig_sub, ax_sub = plt.subplots(2, 1, figsize=(8, 12))
            ax_sub_twin = ax_sub[1].twinx()
        
            total_sp = []
            
            if (num_img - grid_size**2) <= 0 and (num_img - grid_size**2) > -grid_size:
                fig, ax = plt.subplots(grid_size, grid_size, figsize=(16, 12))
            else:
                fig, ax = plt.subplots(grid_size, grid_size+1, figsize=(16, 10))
            for j, sp in enumerate(self.radial_var_sum_split[i]):
                
                if profile_type == "variance":
                    tmp_sp = sp[self.range_ind[0]:self.range_ind[1]]
                    ax.flat[j].plot(self.x_axis, tmp_sp, 'k-', label="var_sum")
                elif profile_type == "mean":
                    tmp_sp = self.radial_avg_sum_split[i][j][self.range_ind[0]:self.range_ind[1]]
                    ax.flat[j].plot(self.x_axis, tmp_sp, 'k-', label="mean_sum")
                else:
                    print("Warning! wrong profile type!")
                    return                    
                
                ax.flat[j].set_title(os.path.basename(self.loaded_data_path[i][j])[:15])
                ax.flat[j].legend(loc='upper right')
                
                
                ax_twin = ax.flat[j].twinx()
                if profile_type == "variance":
                    tmp_ap = self.radial_avg_sum_split[i][j][self.range_ind[0]:self.range_ind[1]]
                    ax_twin.plot(self.x_axis, tmp_ap, 'r:', label="mean_sum")
                elif profile_type == "mean":
                    tmp_ap = self.radial_var_sum_split[i][j][self.range_ind[0]:self.range_ind[1]]
                    ax_twin.plot(self.x_axis, tmp_ap, 'r:', label="var_sum")
                else:
                    print("Warning! wrong profile type!")
                    return    
                ax_twin.legend(loc='right')
                
                ax_sub[1].plot(self.x_axis, tmp_sp/np.max(tmp_sp), label=self.subfolders[i]+"_"+os.path.basename(self.loaded_data_path[i][j])[:15])
                ax_sub[1].set_title("max-normalized")
                ax_sub[0].plot(self.x_axis, tmp_sp, label=self.subfolders[i]+"_"+os.path.basename(self.loaded_data_path[i][j])[:15])
                ax_sub[0].set_title("without normalization")
                total_sp.append(tmp_sp)

            if str_name != None:
                for key in str_name:
                    ax_sub_twin.plot(self.x_axis, self.int_sf[key], label=key, linestyle=":")
                ax_sub_twin.legend(loc="right")
        
            mean_tot = np.mean(total_sp, axis=0)
            ax_tot[0].plot(self.x_axis, mean_tot, label=self.subfolders[i])
            ax_tot[0].legend(loc="upper right")
            ax_tot[1].plot(self.x_axis, mean_tot/np.max(mean_tot), label=self.subfolders[i]+" (max-normalized)")
            ax_tot[1].legend(loc="upper right")
            
            ax_sub[0].legend(loc="upper right")
            ax_sub[1].legend(loc="upper right")
            fig.suptitle(self.subfolders[i]+' - scattering vector range %.3f-%.3f (1/Å)'%(self.from_, self.to_))
            fig.tight_layout()
            if profile_type == "variance":
                fig_sub.suptitle("mean of radial variance profiles - scattering vector range %.3f-%.3f (1/Å)"%(self.from_, self.to_))
            else:
                fig_sub.suptitle("mean of radial mean profiles - scattering vector range %.3f-%.3f (1/Å)"%(self.from_, self.to_))
            fig_sub.tight_layout()
        if profile_type == "variance":
            fig_tot.suptitle("Compare the mean of radial variance profiles between subfolders")
        else:
            fig_tot.suptitle("Compare the mean of radial mean profiles between subfolders")
        fig_tot.tight_layout()
        plt.show()

    
    def sum_edx(self, edx_from, edx_to, offset=0.0, edx_scale=0.01, visual=True):
        self.edx_dim = self.edx_split[0][0].data.shape[2]
        self.edx_range = np.linspace(0.0, self.edx_dim*edx_scale, self.edx_dim)
        self.edx_offset = offset

        self.edx_from = edx_from
        self.edx_to = edx_to
        self.edx_scale = edx_scale

        self.edx_range_ind = [int(np.around(self.edx_from/self.edx_scale)), int(np.around(self.edx_to/self.edx_scale))]
        self.edx_offset_ind = [int(np.around((self.edx_from+self.edx_offset)/self.edx_scale)), int(np.around((self.edx_to+self.edx_offset)/self.edx_scale))]

        if visual:
            for i in range(len(self.subfolders)):
                num_img = len(self.edx_split[i])
                grid_size = int(np.around(np.sqrt(num_img)))
                if (num_img - grid_size**2) <= 0 and (num_img - grid_size**2) > -grid_size:
                    fig, ax = plt.subplots(grid_size, grid_size*2, figsize=(12*2, 12))
                else:
                    fig, ax = plt.subplots(grid_size, (grid_size+1)*2, figsize=(12*2, 10))
                    
                for j in range(num_img):
                    edx_sum_map = np.sum(self.edx_split[i][j].data[:, :, self.edx_range_ind[0]:self.edx_range_ind[1]], axis=2)
                    ax.flat[j*2].imshow(edx_sum_map, cmap='inferno')
                    ax.flat[j*2].set_title(os.path.basename(self.loaded_data_path[i][j])[:15])
                    ax.flat[j*2].axis("off")
                    
                    edx_sum = np.mean(self.edx_split[i][j].data[:, :, self.edx_offset_ind[0]:self.edx_offset_ind[1]], axis=(0, 1))
                    ax.flat[j*2+1].plot(self.edx_range[self.edx_range_ind[0]:self.edx_range_ind[1]], edx_sum, 'k-')
                fig.suptitle(self.subfolders[i]+' EDX intensity map and mean EDX spectrum')
                fig.tight_layout()
                plt.show()        

    
    def NMF_decompose(self, num_comp, max_normalize=False, rescale_0to1=True, profile_type="variance", verbose=True):
        
        self.num_comp = num_comp
        
        # NMF - load data
        flat_adr = []
        if profile_type == "variance":
            for adrs in self.loaded_data_path:
                flat_adr.extend(adrs)
        elif profile_type == "mean":
            for adrs in self.loaded_data_mean_path:
                flat_adr.extend(adrs)
        else:
            print("Warning! wrong profile type!")
            return
        
        self.run_SI = drca(flat_adr, dat_dim=3, dat_unit='1/Å', cr_range=[self.from_, self.to_, self.pixel_size_inv_Ang], 
                                dat_scale=1, rescale=False, DM_file=True, verbose=verbose)

        # NMF - prepare the input dataset
        self.run_SI.make_input(min_val=0.0, max_normalize=max_normalize, rescale_0to1=rescale_0to1)

        # NMF - NMF decomposition and visualization
        self.run_SI.ini_DR(method="nmf", num_comp=num_comp, result_visual=True, intensity_range="absolute")

    
    def NMF_result(self):
        
        # Loading vectors
        fig, ax = plt.subplots(1, 1, figsize=(6, 4))
        for lv in range(self.num_comp):
            ax.plot(self.x_axis, self.run_SI.DR_comp_vectors[lv], self.color_rep[lv+1], label="lv %d"%(lv+1))
        ax.set_facecolor("lightgray")
        ax.legend(loc='upper right')
        fig.tight_layout()
        plt.show()

        # All coefficient maps in one image plot
        if self.num_comp <= len(self.cm_rep):
            num_comp = self.num_comp
            k = 0
            for i in range(len(self.subfolders)):
                num_img = len(self.radial_var_split[i])
                grid_size = int(np.around(np.sqrt(num_img)))
                if (num_img - grid_size**2) <= 0 and (num_img - grid_size**2) > -grid_size:
                    fig, ax = plt.subplots(grid_size, grid_size, figsize=(12, 12))
                else:
                    fig, ax = plt.subplots(grid_size, grid_size+1, figsize=(12, 10))
                for j in range(num_img):
                    sum_map = np.sum(self.radial_avg_split[i][j].data, axis=2)
                    ax.flat[j].imshow(sum_map, cmap='gray')
                    for lv in range(num_comp):
                        ax.flat[j].imshow(self.run_SI.coeffs_reshape[k][:, :, lv], 
                                          cmap=self.cm_rep[lv], 
                                          alpha=self.run_SI.coeffs_reshape[k][:, :, lv]/np.max(self.run_SI.coeffs_reshape[k][:, :, lv]))
                    ax.flat[j].set_title(os.path.basename(self.loaded_data_path[i][j])[:15])
                    k += 1
                for a in ax.flat:
                    a.axis('off')
                fig.suptitle(self.subfolders[i])
                fig.tight_layout()
                plt.show()

        else:
            print('The number of loading vectors exceeds the number of the preset colormaps.')
            print(self.cm_rep)
            print('So, it will show the coefficient maps for only 1-%d loading vectors'%(len(self.cm_rep)))
            num_comp = len(self.cm_rep)
            k = 0
            for i in range(len(self.subfolders)):
                num_img = len(self.radial_var_split[i])
                grid_size = int(np.around(np.sqrt(num_img)))
                if (num_img - grid_size**2) <= 0 and (num_img - grid_size**2) > -grid_size:
                    fig, ax = plt.subplots(grid_size, grid_size, figsize=(12, 12))
                else:
                    fig, ax = plt.subplots(grid_size, grid_size+1, figsize=(12, 10))
                for j in range(num_img):
                    sum_map = np.sum(self.radial_avg_split[i][j].data, axis=2)
                    ax.flat[j].imshow(sum_map, cmap='gray')
                    for lv in range(num_comp):
                        ax.flat[j].imshow(self.run_SI.coeffs_reshape[k][:, :, lv], 
                                          cmap=self.cm_rep[lv], 
                                          alpha=self.run_SI.coeffs_reshape[k][:, :, lv]/np.max(self.run_SI.coeffs_reshape[k][:, :, lv]))
                    ax.flat[j].set_title(os.path.basename(self.loaded_data_path[i][j])[:15])
                    k += 1
                for a in ax.flat:
                    a.axis('off')
                fig.suptitle(self.subfolders[i])
                fig.tight_layout()
                plt.show()

    
    def NMF_comparison(self, str_name=None, percentile_threshold=90, ref_variance=0.7):
        # Show the pixels with high coefficients for each loading vector and the averaged profiles for the mask region
        coeff_split = []
        thresh_coeff_split = []
        lv_line = []

        for lv in range(self.num_comp):
            lv_tot = np.zeros(self.profile_length)
            total_num = 0
            coeff_lv = []
            thresh_coeff_lv = []
            fig_lv, ax_lv = plt.subplots(1, 3, figsize=(12, 4))
            ax_lv[0].plot(self.x_axis, self.run_SI.DR_comp_vectors[lv], self.color_rep[lv+1])
            ax_twin = ax_lv[0].twinx()
            if str_name != None:
                for key in str_name:
                    ax_twin.plot(self.x_axis, self.int_sf[key], label=key, linestyle=":")
                ax_twin.legend(loc="right")
            ax_lv[0].set_facecolor("lightgray")
            fig_lv.suptitle("Loading vector %d"%(lv+1))
        
            thresh = np.percentile(self.run_SI.DR_coeffs[:, lv], percentile_threshold)
            print("threshold coefficient value for loading vector %d = %f"%(lv+1, thresh))

            k=0
            for i in range(len(self.subfolders)):
                fig_sub_tot, ax_sub_tot = plt.subplots(1, 1, figsize=(8, 6))
                lv_sub = np.zeros(self.profile_length)
                sub_num = 0
                coeff = []
                thresh_coeff = []
                num_img = len(self.radial_var_split[i])
                grid_size = int(np.around(np.sqrt(num_img)))
                if (num_img - grid_size**2) <= 0 and (num_img - grid_size**2) > -grid_size:
                    fig, ax = plt.subplots(grid_size, grid_size*2, figsize=(12*2, 12))
                else:
                    fig, ax = plt.subplots(grid_size, (grid_size+1)*2, figsize=(12*2, 10))
                    
                for j in range(num_img):                 
                    coeff_map = self.run_SI.coeffs_reshape[k][:, :, lv].copy()
                    coeff.append(coeff_map)
                    coeff_map[coeff_map<=thresh] = 0
                    coeff_map[coeff_map>thresh] = 1
                    thresh_coeff.append(coeff_map)
                    
                    ax.flat[j*2].imshow(coeff_map, cmap='gray')
                    ax.flat[j*2].set_title(os.path.basename(self.loaded_data_path[i][j])[:15])
                    ax.flat[j*2].axis("off")
                    if len(np.where(coeff_map==1)[0]) != 0:
                        tmp_num = len(np.where(coeff_map==1)[0])
                        sub_num += tmp_num
                        total_num += tmp_num
                        coeff_rv = np.sum(self.radial_var_split[i][j].data[np.where(coeff_map==1)], axis=0)
                        lv_tot += coeff_rv
                        lv_sub += coeff_rv

                        ax.flat[j*2+1].set_ylim(0.0, ref_variance*1.5)
                        ax.flat[j*2+1].plot(self.x_axis, zero_one_rescale(coeff_rv[self.range_ind[0]:self.range_ind[1]]), 'k-')
                        ax.flat[j*2+1].hlines(y=ref_variance, xmin=self.x_axis.min(), xmax=self.x_axis.max(), color="k", linestyle=":", alpha=0.5)
                        ax.flat[j*2+1].plot(self.x_axis, self.radial_var_sum_split[i][j][self.range_ind[0]:self.range_ind[1]], 'k:', alpha=0.5)
                        for lva in range(self.num_comp):
                            mean_coeff = np.mean(self.run_SI.coeffs_reshape[k][:, :, lva][np.where(coeff_map==1)])
                            ax.flat[j*2+1].plot(self.x_axis, self.run_SI.DR_comp_vectors[lva]*mean_coeff, self.color_rep[lva+1], alpha=0.7)
                        
                        ax.flat[j*2+1].set_title(os.path.basename(self.loaded_data_path[i][j])[:15])
                        ax.flat[j*2+1].set_facecolor("lightgray")
                    k+=1
                if sub_num != 0:
                    lv_sub /= sub_num
                ax_sub_tot.plot(self.x_axis, lv_sub[self.range_ind[0]:self.range_ind[1]], 'k-')
                ax_sub_tot.set_title("sum of profiles for all threshold maps - subfolder by subfolder")
                fig_sub_tot.tight_layout()

                ax_lv[2].plot(self.x_axis, lv_sub[self.range_ind[0]:self.range_ind[1]], c=self.color_rep[i], label=self.subfolders[i])
                
                fig.suptitle(self.subfolders[i]+' threshold coefficient map for loading vector %d'%(lv+1))
                fig.tight_layout()
                coeff_lv.append(coeff)
                thresh_coeff_lv.append(thresh_coeff)
                
            coeff_split.append(coeff_lv)
            thresh_coeff_split.append(thresh_coeff_lv)
            
            if total_num != 0:
                lv_tot /= total_num
            lv_line.append(lv_tot)
            ax_lv[1].plot(self.x_axis, lv_tot[self.range_ind[0]:self.range_ind[1]], 'k-')
            ax_lv[1].set_title("sum of profiles for all threshold maps - loading vector %d"%(lv+1))
            ax_lv[2].legend()
            fig_lv.tight_layout()

        fig_tot, ax_tot = plt.subplots(1, 1, figsize=(6, 4))
        for l, line in enumerate(lv_line):
            ax_tot.plot(self.x_axis, line[self.range_ind[0]:self.range_ind[1]], c=self.color_rep[l+1], label='lv %d'%(l+1))
        ax_tot.legend()
        fig_tot.suptitle("Compare the mean of radial profiles between loading vectors")
        fig_tot.tight_layout()
        plt.show()
            
        self.coeff_split = coeff_split
        self.thresh_coeff_split = thresh_coeff_split

        return lv_line


    def scattering_range_of_interest(self, profile_type="variance", str_name=None, fill_width=0.1, height=None, width=None, threshold=None, distance=None, prominence=0.001):

        if width != None:
            width = width/self.pixel_size_inv_Ang

        if distance != None:
            distance = distance/self.pixel_size_inv_Ang
        
        # sum of radial variance profile by subfolder
        total_sum_split = []
        if profile_type == "variance":
            for split in self.radial_var_sum_split:
                total_sum_split.append(np.mean(split, axis=0))
        elif profile_type == "mean":
            for split in self.radial_avg_sum_split:
                total_sum_split.append(np.mean(split, axis=0))  
        else:
            print("Warning! wrong profile type!")
            return

        peak_sub = {}
        for i, sp in enumerate(total_sum_split):
            fig, ax = plt.subplots(1, 1, figsize=(8, 6))
            tmp_sp = sp[self.range_ind[0]:self.range_ind[1]]
            if np.max(tmp_sp) != 0:
                tmp_sp /= np.max(tmp_sp)

            peaks = find_peaks(tmp_sp, height=height, 
                               width=width, 
                               threshold=threshold, 
                               distance=distance, 
                               prominence=prominence)[0]
            
            peaks = peaks * self.pixel_size_inv_Ang
            peaks = peaks + self.from_
            peak_sub[self.subfolders[i]] = peaks
            
            ax.plot(self.x_axis, tmp_sp, c=self.color_rep[i+1], label=self.subfolders[i])

            if str_name != None:
                ax_twin = ax.twinx()
                for key in str_name:
                    ax_twin.plot(self.x_axis, self.int_sf[key], label=key, linestyle=":")
                ax_twin.legend(loc="right")

            for j, peak in enumerate(peaks):
                if peak >= self.from_ and peak <= self.to_:
                    print("%d peak position (1/Å):\t"%(j+1), peak)
                    ax.axvline(peak, ls=':', lw=1.5, c=self.color_rep[i+1])
                    ax.fill_between([peak-fill_width, peak+fill_width], y1=np.max(tmp_sp), y2=np.min(tmp_sp), alpha=0.5, color='orange')
                    ax.text(peak, 1.0, "%d"%(j+1))

            ax.set_xlabel('scattering vector (1/Å)')
            ax.set_facecolor("lightgray")
            ax.legend(loc="right")
            fig.tight_layout()
            plt.show()
            
        self.peak_sub = peak_sub

    
    def variance_map(self, sv_range=None, peaks=None, fill_width=0.1):

        if peaks != None:
            for i, peak in enumerate(peaks):
                sv_range = [peak-fill_width, peak+fill_width]
                mean_var_map = []
                std_var_map = []
                for i in range(len(self.subfolders)):
                    num_img = len(self.radial_var_split[i])
                    grid_size = int(np.around(np.sqrt(num_img)))
                    if (num_img - grid_size**2) <= 0 and (num_img - grid_size**2) > -grid_size:
                        fig, ax = plt.subplots(grid_size, grid_size, figsize=(12, 12))
                    else:
                        fig, ax = plt.subplots(grid_size, grid_size+1, figsize=(12, 10))
                    for j in range(num_img):
                        var_map = np.sum(self.radial_var_split[i][j].isig[sv_range[0]:sv_range[1]].data, axis=2)
                        mean_var_map.append(np.mean(var_map))
                        std_var_map.append(np.std(var_map))
                        ax.flat[j].imshow(var_map, cmap='inferno')
                        ax.flat[j].set_title(os.path.basename(self.loaded_data_path[i][j])[:15])
                    for a in ax.flat:
                        a.axis('off')
                    fig.suptitle(self.subfolders[i]+' - scattering vector range %.3f-%.3f (1/Å)'%(sv_range[0], sv_range[1]))
                    fig.tight_layout()
                    plt.show()
                
        
                # to specify the absolute threshold value to make the binary variance map
                total_num = 0
                fig, ax = plt.subplots(1, 1, figsize=(10, 6))
                for i in range(0, len(self.subfolders)):
                    num_img = len(self.radial_var_split[i])
                    if i == 0:
                        num_range = np.arange(0, num_img)
                        ax.plot(num_range, mean_var_map[:num_img], c=self.color_rep[i+1], marker='s', label=self.subfolders[i])
                        ax.errorbar(num_range, mean_var_map[:num_img], yerr=std_var_map[:num_img], capsize=5, c=self.color_rep[i+1])
                
                    else:
                        num_range = np.arange(total_num, total_num+num_img)
                        ax.plot(num_range, mean_var_map[total_num:total_num+num_img], c=self.color_rep[i+1], marker='s', label=self.subfolders[i])
                        ax.errorbar(num_range, mean_var_map[total_num:total_num+num_img], 
                                    yerr=std_var_map[total_num:total_num+num_img], capsize=5, c=self.color_rep[i+1])
                    total_num += num_img
                ax.grid()
                ax.legend()
                fig.suptitle("mean and standard deviation of the variance maps above")
                fig.tight_layout()
                plt.show()
            
        elif sv_range != None:
            self.sv_range = sv_range
            mean_var_map = []
            std_var_map = []
            for i in range(len(self.subfolders)):
                num_img = len(self.radial_var_split[i])
                grid_size = int(np.around(np.sqrt(num_img)))
                if (num_img - grid_size**2) <= 0 and (num_img - grid_size**2) > -grid_size:
                    fig, ax = plt.subplots(grid_size, grid_size, figsize=(12, 12))
                else:
                    fig, ax = plt.subplots(grid_size, grid_size+1, figsize=(12, 10))
                for j in range(num_img):
                    var_map = np.sum(self.radial_var_split[i][j].isig[self.sv_range[0]:self.sv_range[1]].data, axis=2)
                    mean_var_map.append(np.mean(var_map))
                    std_var_map.append(np.std(var_map))
                    ax.flat[j].imshow(var_map, cmap='inferno')
                    ax.flat[j].set_title(os.path.basename(self.loaded_data_path[i][j])[:15])
                for a in ax.flat:
                    a.axis('off')
                fig.suptitle(self.subfolders[i]+' - scattering vector range %.3f-%.3f (1/Å)'%(self.sv_range[0], self.sv_range[1]))
                fig.tight_layout()
                plt.show()
            
    
            # to specify the absolute threshold value to make the binary variance map
            total_num = 0
            fig, ax = plt.subplots(1, 1, figsize=(10, 6))
            for i in range(0, len(self.subfolders)):
                num_img = len(self.radial_var_split[i])
                if i == 0:
                    num_range = np.arange(0, num_img)
                    ax.plot(num_range, mean_var_map[:num_img], c=self.color_rep[i+1], marker='s', label=self.subfolders[i])
                    ax.errorbar(num_range, mean_var_map[:num_img], yerr=std_var_map[:num_img], capsize=5, c=self.color_rep[i+1])
            
                else:
                    num_range = np.arange(total_num, total_num+num_img)
                    ax.plot(num_range, mean_var_map[total_num:total_num+num_img], c=self.color_rep[i+1], marker='s', label=self.subfolders[i])
                    ax.errorbar(num_range, mean_var_map[total_num:total_num+num_img], 
                                yerr=std_var_map[total_num:total_num+num_img], capsize=5, c=self.color_rep[i+1])
                total_num += num_img
            ax.grid()
            ax.legend()
            fig.suptitle("mean and standard deviation of the variance maps above")
            fig.tight_layout()
            plt.show()
        
        else:
            print("The scattering vector range must be specified!")
            return
 

    def high_variance_map(self, abs_threshold=None, peaks=None, fill_width=0.1, percentile_threshold=90):
        # binary variance map (leave only large variances for the range specified above)
        # abosulte variance map threshold (pixel value > abs_threshold will be 1, otherwise it will be 0)
        if peaks != None:
            for p, peak in enumerate(peaks):
                fig_tot, ax_tot = plt.subplots(1, 2, figsize=(16, 6))
                sp_tot = np.zeros(self.profile_length)
                total_num = 0
                sv_range = [peak-fill_width, peak+fill_width]
                
                for i in range(len(self.subfolders)):
                    sp_sub = np.zeros(self.profile_length)
                    sub_num = 0
                    num_img = len(self.radial_var_split[i])
                    grid_size = int(np.around(np.sqrt(num_img)))
                    if (num_img - grid_size**2) <= 0 and (num_img - grid_size**2) > -grid_size:
                        fig, ax = plt.subplots(grid_size, grid_size, figsize=(12, 12))
                    else:
                        fig, ax = plt.subplots(grid_size, grid_size+1, figsize=(12, 10))
                    for j in range(num_img):
                        var_map = np.sum(self.radial_var_split[i][j].isig[sv_range[0]:sv_range[1]].data, axis=2)
                        abs_threshold = np.percentile(var_map, percentile_threshold)
                        var_map[var_map<=abs_threshold] = 0
                        var_map[var_map>abs_threshold] = 1
                        ax.flat[j].imshow(var_map, cmap='gray')
                        ax.flat[j].set_title(os.path.basename(self.loaded_data_path[i][j])[:15]+"_threshold value=%f"%abs_threshold)

                        tmp_num = len(np.where(var_map==1)[0])
                        total_num += tmp_num
                        sub_num += tmp_num
                        sp_tot += np.sum(self.radial_var_split[i][j].data[np.where(var_map==1)], axis=0)
                        sp_sub += np.sum(self.radial_var_split[i][j].data[np.where(var_map==1)], axis=0)

                    if sub_num != 0:
                        sp_sub /= sub_num
                    ax_tot[1].plot(self.x_axis, sp_sub[self.range_ind[0]:self.range_ind[1]], c=self.color_rep[i], label=self.subfolders[i])
                    
                    for a in ax.flat:
                        a.axis('off')
                    fig.suptitle(self.subfolders[i]+' - scattering vector range %.3f-%.3f (1/Å)'%(sv_range[0], sv_range[1]))
                    fig.tight_layout()

                ax_tot[1].legend()
                if total_num != 0:
                    sp_tot /= total_num
                ax_tot[0].plot(self.x_axis, sp_tot[self.range_ind[0]:self.range_ind[1]], 'k-')
                fig_tot.tight_layout()
                plt.show()

        elif percentile_threshold != None:     
            thresh_var_split = []
            fig_tot, ax_tot = plt.subplots(1, 2, figsize=(16, 6))
            sp_tot = np.zeros(self.profile_length)
            total_num = 0

            # to obtain the threshold value
            temp_stored_values = []
            for i in range(len(self.subfolders)):
                num_img = len(self.radial_var_split[i])
                for j in range(num_img):
                    var_map = np.sum(self.radial_var_split[i][j].isig[self.sv_range[0]:self.sv_range[1]].data, axis=2)
                    temp_stored_values.extend(var_map.flatten().tolist())
            self.abs_threshold = np.percentile(temp_stored_values, percentile_threshold)

            # leave the pixels of the high variances
            for i in range(len(self.subfolders)):
                sp_sub = np.zeros(self.profile_length)
                sub_num = 0
                thresh_var = []
                num_img = len(self.radial_var_split[i])
                grid_size = int(np.around(np.sqrt(num_img)))
                if (num_img - grid_size**2) <= 0 and (num_img - grid_size**2) > -grid_size:
                    fig, ax = plt.subplots(grid_size, grid_size, figsize=(12, 12))
                else:
                    fig, ax = plt.subplots(grid_size, grid_size+1, figsize=(12, 10))
                for j in range(num_img):
                    var_map = np.sum(self.radial_var_split[i][j].isig[self.sv_range[0]:self.sv_range[1]].data, axis=2)
                    var_map[var_map<=self.abs_threshold] = 0
                    var_map[var_map>self.abs_threshold] = 1
                    thresh_var.append(var_map)
                    ax.flat[j].imshow(var_map, cmap='gray')
                    ax.flat[j].set_title(os.path.basename(self.loaded_data_path[i][j])[:15])

                    tmp_num = len(np.where(var_map==1)[0])
                    total_num += tmp_num
                    sub_num += tmp_num
                    sp_tot += np.sum(self.radial_var_split[i][j].data[np.where(var_map==1)], axis=0)
                    sp_sub += np.sum(self.radial_var_split[i][j].data[np.where(var_map==1)], axis=0)
                if sub_num != 0:
                    sp_sub /= sub_num
                ax_tot[1].plot(self.x_axis, sp_sub[self.range_ind[0]:self.range_ind[1]], c=self.color_rep[i], label=self.subfolders[i])
                
                for a in ax.flat:
                    a.axis('off')
                fig.suptitle(self.subfolders[i]+' - scattering vector range %.3f-%.3f (1/Å)'%(self.sv_range[0], self.sv_range[1]))
                fig.tight_layout()
                thresh_var_split.append(thresh_var)
                
            ax_tot[1].legend()
            if total_num != 0:
                sp_tot /= total_num
            ax_tot[0].plot(self.x_axis, sp_tot[self.range_ind[0]:self.range_ind[1]], 'k-')
            fig_tot.tight_layout()
            plt.show()
                
            self.thresh_var_split = thresh_var_split
            return sp_tot

        elif abs_threshold != None:     
            thresh_var_split = []
            self.abs_threshold = abs_threshold
            fig_tot, ax_tot = plt.subplots(1, 2, figsize=(16, 6))
            sp_tot = np.zeros(self.profile_length)
            total_num = 0
            
            for i in range(len(self.subfolders)):
                sp_sub = np.zeros(self.profile_length)
                sub_num = 0
                thresh_var = []
                num_img = len(self.radial_var_split[i])
                grid_size = int(np.around(np.sqrt(num_img)))
                if (num_img - grid_size**2) <= 0 and (num_img - grid_size**2) > -grid_size:
                    fig, ax = plt.subplots(grid_size, grid_size, figsize=(12, 12))
                else:
                    fig, ax = plt.subplots(grid_size, grid_size+1, figsize=(12, 10))
                for j in range(num_img):
                    var_map = np.sum(self.radial_var_split[i][j].isig[self.sv_range[0]:self.sv_range[1]].data, axis=2)
                    var_map[var_map<=self.abs_threshold] = 0
                    var_map[var_map>self.abs_threshold] = 1
                    thresh_var.append(var_map)
                    ax.flat[j].imshow(var_map, cmap='gray')
                    ax.flat[j].set_title(os.path.basename(self.loaded_data_path[i][j])[:15])
                    
                    tmp_num = len(np.where(var_map==1)[0])
                    total_num += tmp_num
                    sub_num += tmp_num                    
                    sp_tot += np.sum(self.radial_var_split[i][j].data[np.where(var_map==1)], axis=0)
                    sp_sub += np.sum(self.radial_var_split[i][j].data[np.where(var_map==1)], axis=0)
                    
                if sub_num != 0:
                    sp_sub /= sub_num
                ax_tot[1].plot(self.x_axis, sp_sub[self.range_ind[0]:self.range_ind[1]], c=self.color_rep[i], label=self.subfolders[i])
                
                for a in ax.flat:
                    a.axis('off')
                fig.suptitle(self.subfolders[i]+' - scattering vector range %.3f-%.3f (1/Å)'%(self.sv_range[0], self.sv_range[1]))
                fig.tight_layout()
                thresh_var_split.append(thresh_var)
                
            ax_tot[1].legend()
            if total_num != 0:
                sp_tot /= total_num
            ax_tot[0].plot(self.x_axis, sp_tot[self.range_ind[0]:self.range_ind[1]], 'k-')
            fig_tot.tight_layout()
            plt.show()
                
            self.thresh_var_split = thresh_var_split
            return sp_tot
            
        else:
            print("The absolute threshold value or the percentile threshold must be specified")
            return

    
    def Xcorrel(self, str_name=None, profile_type="mean"):
        xcor_val_split = []
        xcor_sh_split = []

        self.xcor_profile = profile_type
        self.xcor_str = str_name
        
        for i in range(len(self.subfolders)):
            num_img = len(self.radial_var_split[i])
            xcor_val_list = []
            xcor_sh_list = []
            for j in range(num_img):
                if profile_type=="variance":
                    var_data = self.radial_var_split[i][j].data
                elif profile_type=="mean":
                    var_data = self.radial_avg_split[i][j].data
                else:
                    print("Warning! wrong profile type!")
                    return
                    
                xcor_val = []
                xcor_sh = []
                for sy in range(var_data.shape[0]):
                    for sx in range(var_data.shape[1]):
                        sp = var_data[sy, sx][self.range_ind[0]:self.range_ind[1]]
                        xcor = np.correlate(self.int_sf[str_name]/np.max(self.int_sf[str_name]), sp/np.max(sp), mode='full')
                        xcor_val.append(np.max(xcor))
                        xcor_sh.append(np.argmax(xcor))
                xcor_val = np.asarray(xcor_val).reshape(var_data.shape[:2])
                xcor_sh = np.asarray(xcor_sh).reshape(var_data.shape[:2])*self.pixel_size_inv_Ang - np.median(self.x_axis)
                xcor_val_list.append(xcor_val)
                xcor_sh_list.append(xcor_sh)
            xcor_val_split.append(xcor_val_list)
            xcor_sh_split.append(xcor_sh_list)

        self.xcor_val_split = xcor_val_split
        self.xcor_sh_split = xcor_sh_split

        for i in range(len(self.subfolders)):
            num_img = len(self.radial_var_split[i])
            grid_size = int(np.around(np.sqrt(num_img)))
            if (num_img - grid_size**2) <= 0 and (num_img - grid_size**2) > -grid_size:
                fig, ax = plt.subplots(grid_size, grid_size*2, figsize=(12*2, 12))
            else:
                fig, ax = plt.subplots(grid_size, (grid_size+1)*2, figsize=(12*2, 10))
            for j in range(num_img):     
                ax.flat[j*2].imshow(xcor_val_split[i][j], cmap='inferno')
                ax.flat[j*2].set_title(self.loaded_data_path[i][j][-29:-14])
                ax.flat[j*2].axis("off")
        
                ax.flat[j*2+1].hist(xcor_val_split[i][j].flatten(), bins=100)
                ax.flat[j*2+1].set_title("cross-correlation values")
                ax.flat[j*2+1].set_facecolor("lightgray")
        
            fig.suptitle(self.subfolders[i]+' cross-correlation - value')
            fig.tight_layout()
            plt.show()

    
    def high_Xcorr(self, value_threshold=5.0, shift_threshold=0.3):
        thresh_xcor_split = []
        fig_tot, ax_tot = plt.subplots(1, 2, figsize=(16, 6))
        sp_tot = np.zeros(self.profile_length)
        total_num = 0
        for i in range(len(self.subfolders)):
            sp_sub = np.zeros(self.profile_length)
            thresh_xcor = []
            num_img = len(self.radial_var_split[i])
            grid_size = int(np.around(np.sqrt(num_img)))
            sub_num = 0
            
            if (num_img - grid_size**2) <= 0 and (num_img - grid_size**2) > -grid_size:
                fig, ax = plt.subplots(grid_size, grid_size*2, figsize=(12*2, 12))
            else:
                fig, ax = plt.subplots(grid_size, (grid_size+1)*2, figsize=(12*2, 10))
            for j in range(num_img):
                xcor_val_map = self.xcor_val_split[i][j].copy()
                xcor_sh_map = self.xcor_sh_split[i][j].copy()
                val_map = self.xcor_val_split[i][j].copy()
                sh_map = self.xcor_sh_split[i][j].copy()        
                xcor_val_map[val_map<=value_threshold] = 0
                xcor_val_map[val_map>value_threshold] = 1
                xcor_sh_map[np.abs(sh_map)>shift_threshold] = 0
                xcor_sh_map[np.abs(sh_map)<=shift_threshold] = 1
        
                bool_mask = xcor_val_map * xcor_sh_map
                thresh_xcor.append(bool_mask)
                ax.flat[j*2].imshow(bool_mask, cmap='gray')
                ax.flat[j*2].set_title(self.loaded_data_path[i][j][-29:-14])
                ax.flat[j*2].axis("off")
                
                if len(np.nonzero(bool_mask)[0]) != 0:
                    if self.xcor_profile == "variance":
                        avg_rv = np.sum(self.radial_var_split[i][j].data[np.where(bool_mask==1)], axis=0)
                    elif self.xcor_profile == "mean":
                        avg_rv = np.sum(self.radial_avg_split[i][j].data[np.where(bool_mask==1)], axis=0)
                    else:
                        print("Warning! wrong profile type!")
                        return

                    tmp_num = len(np.where(bool_mask==1)[0])
                    total_num += tmp_num
                    sub_num += tmp_num
                    sp_tot += avg_rv
                    sp_sub += avg_rv
                    if np.max(avg_rv) != 0:
                        avg_rv /= np.max(avg_rv)
                    ax.flat[j*2+1].plot(self.x_axis, avg_rv[self.range_ind[0]:self.range_ind[1]], 'k-')
                    ax_twin = ax.flat[j*2+1].twinx()
                    ax_twin.plot(self.x_axis, self.int_sf[self.xcor_str], 'k:')
                    ax.flat[j*2+1].set_facecolor("lightgray")

            if sub_num != 0:
                sp_sub /= sub_num
            ax_tot[1].plot(self.x_axis, sp_sub[self.range_ind[0]:self.range_ind[1]], c=self.color_rep[i], label=self.subfolders[i])

            thresh_xcor_split.append(thresh_xcor)
            fig.suptitle(self.subfolders[i]+' large cross-correlation - value')
            fig.tight_layout()
        
        ax_tot[1].legend()
        if total_num != 0:
            sp_tot /= total_num
        ax_tot[0].plot(self.x_axis, sp_tot[self.range_ind[0]:self.range_ind[1]], 'k-')
        fig_tot.tight_layout()
        plt.show()
        self.thresh_xcor_split = thresh_xcor_split
        return sp_tot

    def edx_classification(self, threshold_map="NMF"):
        if threshold_map == "variance":
            fig_tot, ax_tot = plt.subplots(1, 2, figsize=(16, 6))
            sp_tot = np.zeros_like(self.edx_range)
            total_num = 0
            for i in range(len(self.subfolders)):
                num_img = len(self.edx_split[i])
                grid_size = int(np.around(np.sqrt(num_img)))
                sub_num = 0
                
                if (num_img - grid_size**2) <= 0 and (num_img - grid_size**2) > -grid_size:
                    fig, ax = plt.subplots(grid_size, grid_size*2, figsize=(12*2, 12))
                else:
                    fig, ax = plt.subplots(grid_size, (grid_size+1)*2, figsize=(12*2, 10))

                sp_sub = np.zeros_like(self.edx_range)
                for j in range(num_img):
                    thresh_map = self.thresh_var_split[i][j]
                    ax.flat[j*2].imshow(thresh_map, cmap='gray')
                    ax.flat[j*2].set_title(os.path.basename(self.loaded_data_path[i][j])[:15])
                    ax.flat[j*2].axis("off")
                    
                    tmp_num = len(np.where(thresh_map==1)[0])
                    total_num += tmp_num
                    sub_num += tmp_num
                    edx_sum = np.sum(self.edx_split[i][j].data[np.where(thresh_map==1)], axis=0)
                    sp_tot += edx_sum
                    sp_sub += edx_sum
                    ax.flat[j*2+1].plot(self.edx_range[self.edx_range_ind[0]:self.edx_range_ind[1]], sp_sub[self.edx_offset_ind[0]:self.edx_offset_ind[1]], 'k-')

                if sub_num != 0:
                    sp_sub /= sub_num
                ax_tot[1].plot(self.edx_range[self.edx_range_ind[0]:self.edx_range_ind[1]], sp_sub[self.edx_offset_ind[0]:self.edx_offset_ind[1]], c=self.color_rep[i], label=self.subfolders[i])
                fig.suptitle(self.subfolders[i]+' mean EDX spectrum for each high-variance map')
                fig.tight_layout()
                
            if total_num != 0:
                sp_tot /= total_num
            ax_tot[0].plot(self.edx_range[self.edx_range_ind[0]:self.edx_range_ind[1]], sp_tot[self.edx_offset_ind[0]:self.edx_offset_ind[1]], 'k-')
            ax_tot[1].legend()
            fig_tot.suptitle(self.subfolders[i]+' mean EDX spectrum for all high-variance maps')
            fig_tot.tight_layout()
            plt.show()

            return sp_tot

        elif threshold_map == "cross-correlation":
            fig_tot, ax_tot = plt.subplots(1, 2, figsize=(16, 6))
            sp_tot = np.zeros_like(self.edx_range)
            total_num = 0
            for i in range(len(self.subfolders)):
                num_img = len(self.edx_split[i])
                grid_size = int(np.around(np.sqrt(num_img)))
                sub_num = 0
                
                if (num_img - grid_size**2) <= 0 and (num_img - grid_size**2) > -grid_size:
                    fig, ax = plt.subplots(grid_size, grid_size*2, figsize=(12*2, 12))
                else:
                    fig, ax = plt.subplots(grid_size, (grid_size+1)*2, figsize=(12*2, 10))

                sp_sub = np.zeros_like(self.edx_range)
                for j in range(num_img):
                    thresh_map = self.thresh_xcor_split[i][j]
                    ax.flat[j*2].imshow(thresh_map, cmap='gray')
                    ax.flat[j*2].set_title(os.path.basename(self.loaded_data_path[i][j])[:15])
                    ax.flat[j*2].axis("off")
                    
                    edx_sum = np.sum(self.edx_split[i][j].data[np.where(thresh_map==1)], axis=0)
                    tmp_num = len(np.where(thresh_map==1)[0])
                    total_num += tmp_num
                    sub_num += tmp_num
                    sp_tot += edx_sum
                    sp_sub += edx_sum
                    ax.flat[j*2+1].plot(self.edx_range[self.edx_range_ind[0]:self.edx_range_ind[1]], sp_sub[self.edx_offset_ind[0]:self.edx_offset_ind[1]], 'k-')

                if sub_num != 0:
                    sp_sub /= sub_num
                ax_tot[1].plot(self.edx_range[self.edx_range_ind[0]:self.edx_range_ind[1]], sp_sub[self.edx_offset_ind[0]:self.edx_offset_ind[1]], c=self.color_rep[i], label=self.subfolders[i])
                fig.suptitle(self.subfolders[i]+' mean EDX spectrum for each high-cross-correlation map')
                fig.tight_layout()

            if total_num != 0:
                sp_tot /= total_num
            ax_tot[0].plot(self.edx_range[self.edx_range_ind[0]:self.edx_range_ind[1]], sp_tot[self.edx_offset_ind[0]:self.edx_offset_ind[1]], 'k-')
            ax_tot[1].legend()
            fig_tot.suptitle(self.subfolders[i]+' mean EDX spectrum for all high-cross-correlation maps')
            fig_tot.tight_layout()
            plt.show()

            return sp_tot
        
        elif threshold_map == "NMF":
            lv_tot = []
            for lv in range(self.num_comp):
                fig_tot, ax_tot = plt.subplots(1, 2, figsize=(16, 6))
                sp_tot = np.zeros_like(self.edx_range)
                total_num = 0
                for i in range(len(self.subfolders)):
                    num_img = len(self.edx_split[i])
                    grid_size = int(np.around(np.sqrt(num_img)))
                    sub_num = 0
                    
                    if (num_img - grid_size**2) <= 0 and (num_img - grid_size**2) > -grid_size:
                        fig, ax = plt.subplots(grid_size, grid_size*2, figsize=(12*2, 12))
                    else:
                        fig, ax = plt.subplots(grid_size, (grid_size+1)*2, figsize=(12*2, 10))
    
                    sp_sub = np.zeros_like(self.edx_range)
                    for j in range(num_img):
                        thresh_map = self.thresh_coeff_split[lv][i][j]
                        ax.flat[j*2].imshow(thresh_map, cmap='gray')
                        ax.flat[j*2].set_title(os.path.basename(self.loaded_data_path[i][j])[:15])
                        ax.flat[j*2].axis("off")
                        
                        edx_sum = np.sum(self.edx_split[i][j].data[np.where(thresh_map==1)], axis=0)
                        tmp_num = len(np.where(thresh_map==1)[0])
                        total_num += tmp_num
                        sub_num += tmp_num
                        sp_tot += edx_sum
                        sp_sub += edx_sum
                        ax.flat[j*2+1].plot(self.edx_range[self.edx_range_ind[0]:self.edx_range_ind[1]], sp_sub[self.edx_offset_ind[0]:self.edx_offset_ind[1]], 'k-')

                    if sub_num != 0:
                        sp_sub /= sub_num
                    ax_tot[1].plot(self.edx_range[self.edx_range_ind[0]:self.edx_range_ind[1]], sp_sub[self.edx_offset_ind[0]:self.edx_offset_ind[1]], c=self.color_rep[i], label=self.subfolders[i])
                    fig.suptitle(self.subfolders[i]+' mean EDX spectrum for each high-coefficient map for loading vector %d'%(lv+1))
                    fig.tight_layout()
                if total_num != 0:
                    sp_tot /= total_num
                lv_tot.append(sp_tot)
                ax_tot[0].plot(self.edx_range[self.edx_range_ind[0]:self.edx_range_ind[1]], sp_tot[self.edx_offset_ind[0]:self.edx_offset_ind[1]], 'k-')
                ax_tot[1].legend()
                fig_tot.suptitle(self.subfolders[i]+' mean EDX spectrum for all high-coefficient maps for loading vector %d'%(lv+1))
                fig_tot.tight_layout()

            fig_lv, ax_lv = plt.subplots(1, 1, figsize=(12, 4))
            for l, line in enumerate(lv_tot):
                ax_lv.plot(self.edx_range[self.edx_range_ind[0]:self.edx_range_ind[1]], 
                           line[self.edx_offset_ind[0]:self.edx_offset_ind[1]], c=self.color_rep[l+1], label='lv %d'%(l+1))
            ax_lv.legend()
            fig_lv.suptitle("Compare the mean of EDX spectra between loading vectors")
            fig_lv.tight_layout()
            plt.show()

            return lv_tot
        
        else:
            print("Warning! unavailable type!")

    
    def summary_save(self, sv_range=None, percentile_threshold=None, save=False, obtain_dp=False, log_scale_dp=False):
        
        for i in range(len(self.subfolders)):
            num_img = len(self.radial_var_split[i])
            max_dps = []
            mean_dps = []
            for j in range(num_img):
                save_path = os.path.dirname(self.loaded_data_path[i][j]) # able to change the base directory for saving
                print("save directory: ", save_path)
                data_name = os.path.basename(self.loaded_data_path[i][j]).split("_")
                data_name = data_name[0]+'_'+data_name[1]
                print("save prefix: ", data_name)
                top, bottom, left, right = self.crop
                fig, ax = plt.subplots(3, 3, figsize=(15, 15))
                ax[0, 0].imshow(self.BF_disc_align[i][j][top:bottom, left:right], cmap='inferno')
                ax[0, 0].set_title("Aligned BF disc")
                ax[0, 0].axis("off")

                sum_map = np.sum(self.radial_avg_split[i][j].data, axis=2)
                ax[0, 1].imshow(sum_map, cmap='inferno')
                ax[0, 1].set_title("Intensity map")
                ax[0, 1].axis("off")                 
        
                rv = self.radial_var_sum_split[i][j]
                ax[0, 2].plot(self.x_axis, rv[self.range_ind[0]:self.range_ind[1]], 'k-', label="var_sum")
                ax[0, 2].set_title("Sum of radial variance/mean profiles")
                ax[0, 2].legend(loc='upper right')
                
                ra = self.radial_avg_sum_split[i][j]
                ax_twin = ax[0, 2].twinx()
                ax_twin.plot(self.x_axis, ra[self.range_ind[0]:self.range_ind[1]], 'r:', label="mean_sum")
                ax_twin.legend(loc='right')

                if sv_range != None:
                    var_map = np.sum(self.radial_var_split[i][j].isig[sv_range[0]:sv_range[1]].data, axis=2)
                else:
                    var_map = np.sum(self.radial_var_split[i][j].isig[self.sv_range[0]:self.sv_range[1]].data, axis=2)
                ax[1, 0].imshow(var_map, cmap='inferno')
                ax[1, 0].set_title('Variance map\nscattering vector range %.3f-%.3f (1/Å)'%(self.sv_range[0], self.sv_range[1]))
        
                th_map = var_map.copy()
                if percentile_threshold != None:
                    abs_threshold = np.percentile(var_map, percentile_threshold)
                    th_map[var_map<=abs_threshold] = 0
                    th_map[var_map>abs_threshold] = 1
                else:
                    th_map[var_map<=self.abs_threshold] = 0
                    th_map[var_map>self.abs_threshold] = 1                    
                ax[1, 1].imshow(th_map, cmap='gray')
                ax[1, 1].set_title('High-variance map\nabsolute threshold %.3f'%self.abs_threshold)

                if obtain_dp and len(np.nonzero(th_map)[0]) != 0:
                    if self.new_process_flag:
                        dataset = hs.load(self.loaded_data_path[i][j][:-18]+'calibrated_and_corrected.zspy')
                    else:      
                        cali = py4DSTEM.read(self.loaded_data_path[i][j][:-13]+"braggdisks_cali.h5")
                        dataset = py4DSTEM.read(self.loaded_data_path[i][j][:-13]+"prepared_data.h5")
                        dataset = py4DSTEM.DataCube(dataset.data)
                        dataset = dataset.filter_hot_pixels(thresh = 0.1, return_mask=False)
                        dataset.calibration = cali.calibration
                        dataset.calibrate()
                        
                    mean_dp = np.mean(dataset.data[np.where(th_map==1)], axis=0)
                    mean_dps.append(np.sum(dataset.data[np.where(th_map==1)], axis=0))
                    if log_scale_dp:
                        mean_dp[mean_dp <= 0] = 1.0
                        ax[2, 1].imshow(np.log(mean_dp), cmap='inferno')
                        ax[2, 1].set_title('(log-scale) Mean diffraction pattern\nfor the high-variance map')
                    else:
                        ax[2, 1].imshow(mean_dp, cmap='inferno')
                        ax[2, 1].set_title('Mean diffraction pattern\nfor the high-variance map')
                        
                    if save:
                        mean_dp = hs.signals.Signal2D(mean_dp)
                        mean_dp.axes_manager[0].scale = self.radial_var_split[i][j].axes_manager[-1].scale
                        mean_dp.axes_manager[1].scale = self.radial_var_split[i][j].axes_manager[-1].scale
                        mean_dp.save(save_path+'/'+data_name+"_mean_diffraction_pattern_for_threshold_map.hspy", overwrite=True)
        
                    max_dp = np.max(dataset.data[np.where(th_map==1)], axis=0)
                    max_dps.append(max_dp)
                    if log_scale_dp:
                        max_dp[max_dp <= 0] = 1.0
                        ax[1, 2].imshow(np.log(max_dp), cmap='inferno')
                        ax[1, 2].set_title('(log-scale) Maximum diffraction pattern\nfor the thresholding map')
                    else:
                        ax[1, 2].imshow(max_dp, cmap='inferno')
                        ax[1, 2].set_title('Maximum diffraction pattern\nfor the high-variance map')
                        
                    if save:
                        max_dp = hs.signals.Signal2D(max_dp)
                        max_dp.axes_manager[0].scale = self.radial_var_split[i][j].axes_manager[-1].scale
                        max_dp.axes_manager[1].scale = self.radial_var_split[i][j].axes_manager[-1].scale
                        max_dp.save(save_path+'/'+data_name+"_max_diffraction_pattern_for_threshold_map.hspy", overwrite=True)

                    del dataset # release the occupied memory
                    
                if len(np.nonzero(th_map)[0]) != 0:
                    avg_rv = np.mean(self.radial_var_split[i][j].data[np.where(th_map==1)], axis=0)
                    ax[2, 2].plot(self.x_axis, avg_rv[self.range_ind[0]:self.range_ind[1]], 'k-')
                    ax[2, 2].set_title('Averaged radial variance profile\nfor the high-variance map')
                    if save:
                        avg_rv = hs.signals.Signal1D(avg_rv)
                        avg_rv.axes_manager[0].scale = self.pixel_size_inv_Ang
                        avg_rv.save(save_path+'/'+data_name+"_mean_radial_variance_profile_for_threshold_map.hspy", overwrite=True) 
        
                ax[1, 0].axis("off")
                ax[1, 1].axis("off")
                ax[1, 2].axis("off")
                ax[2, 0].axis("off")
                ax[2, 1].axis("off")
         
                fig.suptitle(self.subfolders[i]+" - "+os.path.basename(self.loaded_data_path[i][j])[:15])
                fig.tight_layout()
        
                if save:
                    sum_map = hs.signals.Signal2D(sum_map)
                    sum_map.axes_manager[0].scale = self.radial_var_split[i][j].axes_manager[0].scale
                    sum_map.axes_manager[1].scale = self.radial_var_split[i][j].axes_manager[1].scale
                    sum_map.save(save_path+'/'+data_name+"_intensity_map.hspy", overwrite=True)
                    rv = hs.signals.Signal1D(rv)
                    rv.axes_manager[0].scale = self.radial_var_split[i][j].axes_manager[-1].scale
                    rv.save(save_path+'/'+data_name+"_mean_radial_variance_profile.hspy", overwrite=True)            
                    var_map = hs.signals.Signal2D(var_map)
                    var_map.axes_manager[0].scale = self.radial_var_split[i][j].axes_manager[0].scale
                    var_map.axes_manager[1].scale = self.radial_var_split[i][j].axes_manager[1].scale
                    var_map.save(save_path+'/'+data_name+"_variance_map.hspy", overwrite=True)
                    th_map = hs.signals.Signal2D(th_map)
                    th_map.axes_manager[0].scale = self.radial_var_split[i][j].axes_manager[0].scale
                    th_map.axes_manager[1].scale = self.radial_var_split[i][j].axes_manager[1].scale
                    th_map.save(save_path+'/'+data_name+"_threshold_map.hspy", overwrite=True)
                    fig.savefig(save_path+'/'+data_name+"_summary.png")

            max_dps = np.asarray(max_dps)
            mean_dps = np.asarray(mean_dps)
            fig_dp, ax_dp = plt.subplots(1, 2, figsize=(12, 6))
            if log_scale_dp:
                ax_dp[0].imshow(np.log(np.mean(max_dps, axis=0)), cmap="inferno")
            else:
                ax_dp[0].imshow(np.sum(max_dps, axis=0), cmap="inferno")
            ax_dp[0].axis("off")
            ax_dp[0].set_title("sum of all max diffraction patterns from each data")
            if log_scale_dp:
                ax_dp[1].imshow(np.log(np.mean(mean_dps, axis=0)), cmap="inferno")
            else:
                ax_dp[1].imshow(np.sum(mean_dps, axis=0), cmap="inferno")
            ax_dp[1].axis("off")
            ax_dp[1].set_title("sum of all diffraction patterns")
            fig_dp.tight_layout()
            plt.show()


# The code below is the original script of 'drca' (https://github.com/jinseuk56/drca)
# You can find the related research work in the following link: https://doi.org/10.1016/j.ultramic.2021.113314
# This is used to integrate many 3D variance profile data into one input data matrix,
# to perform NMF, and to visualize the decomposition result
# If you have any questions about it, please contact me by email (jinseok.ryu@diamond.ac.uk or jinseuk56@gmail.com)

# create a customized colorbar
color_rep = ["black", "red", "green", "blue", "orange", "purple", "yellow", "lime", 
             "cyan", "magenta", "lightgray", "peru", "springgreen", "deepskyblue", 
             "hotpink", "darkgray"]

rgb_rep = {"black":[1,1,1,1], "red":[1,0,0,1], "green":[0,1,0,1], "blue":[0,0,1,1], "orange":[1,0.5,0,1], 
           "purple":[1,0,1,1],"yellow":[1,1,0,1], "lime":[0,1,0.5,1], "cyan":[0,1,1,1]}

custom_cmap = mcolors.ListedColormap(color_rep)
bounds = np.arange(-1, len(color_rep))
norm = mcolors.BoundaryNorm(boundaries=bounds, ncolors=len(color_rep))
sm = cm.ScalarMappable(cmap=custom_cmap, norm=norm)
sm.set_array([])

cm_rep = ["gray", "Reds", "Greens", "Blues", "Oranges", "Purples"]  
    
class drca():
    def __init__(self, adr, dat_dim, dat_unit, cr_range=None, dat_scale=1, rescale=True, DM_file=True, verbose=True):
        self.file_adr = adr
        self.num_img = len(adr)
        self.dat_dim = dat_dim
        if dat_dim == 4:
            cr_range = None
        self.dat_unit = dat_unit
        self.cr_range = cr_range
        
        if cr_range:
            self.dat_dim_range = np.arange(cr_range[0], cr_range[1], cr_range[2]) * dat_scale
            self.num_dim = len(self.dat_dim_range)
        
        if dat_dim == 3:
            self.data_storage, self.data_shape = data_load_3d(adr, cr_range, rescale, DM_file, verbose)
        
        else:
            self.data_storage, self.data_shape = data_load_4d(adr, rescale, verbose)
            
        self.original_data_shape = self.data_shape.copy()

        if len(self.dat_dim_range) > self.original_data_shape[0, 2]:
            difference = len(self.dat_dim_range) - self.original_data_shape[0, 2]
            self.dat_dim_range = self.dat_dim_range[:-difference]
            self.num_dim = len(self.dat_dim_range)
            print("Data shape")
            print(self.original_data_shape)
            print("Spectrum length: %d"%self.num_dim)

        elif len(self.dat_dim_range) < self.original_data_shape[0, 2]:
            difference = self.original_data_shape[0, 2] - len(self.dat_dim_range)
            self.dat_dim_range = np.arange(cr_range[0], cr_range[1]+difference*cr_range[2], cr_range[2]) * dat_scale
            self.num_dim = len(self.dat_dim_range)
            print("Data shape")
            print(self.original_data_shape)
            print("Spectrum length: %d"%self.num_dim)

        else:
            print("Data shape")
            print(self.original_data_shape)
            print("Spectrum length: %d"%self.num_dim)

             
    def binning(self, bin_y, bin_x, str_y, str_x, offset=0, rescale_0to1=True):
        dataset = []
        data_shape_new = []
        
        for img in self.data_storage:
            print(img.shape)
            processed = binning_SI(img, bin_y, bin_x, str_y, str_x, offset, self.num_dim, rescale_0to1) # include the step for re-scaling the actual input
            print(processed.shape)
            data_shape_new.append(processed.shape)
            dataset.append(processed)

        data_shape_new = np.asarray(data_shape_new)
        print(data_shape_new)
        
        self.data_storage = dataset
        self.data_shape = data_shape_new
        
    def find_center(self, cbox_edge, center_remove, result_visual=True, log_scale=True):
        if self.dat_dim != 4:
            print("data dimension error")
            return
        
        self.center_pos = []
        
        for i in range(self.num_img):
            mean_dp = np.mean(self.data_storage[i], axis=(0, 1))
            cbox_outy = int(mean_dp.shape[0]/2 - cbox_edge/2)
            cbox_outx = int(mean_dp.shape[1]/2 - cbox_edge/2)
            center_box = mean_dp[cbox_outy:-cbox_outy, cbox_outx:-cbox_outx]
            Y, X = np.indices(center_box.shape)
            com_y = np.sum(center_box * Y) / np.sum(center_box)
            com_x = np.sum(center_box * X) / np.sum(center_box)
            c_pos = [np.around(com_y+cbox_outy), np.around(com_x+cbox_outx)]
            self.center_pos.append(c_pos)
        print(self.center_pos)
        
        if result_visual:
            np.seterr(divide='ignore')
            for i in range(self.num_img):
                fig, ax = plt.subplots(1, 1, figsize=(5, 5))
                if log_scale:
                    ax.imshow(np.log(np.mean(self.data_storage[i], axis=(0, 1))), cmap="viridis")
                else:
                    ax.imshow(np.mean(self.data_storage[i], axis=(0, 1)), cmap="viridis")
                ax.scatter(self.center_pos[i][1], self.center_pos[i][0], c="r", s=10)
                ax.axis("off")
                plt.show()
        
        self.center_removed = False
        if center_remove != 0:
            self.center_removed = True
            data_cr = []
            for i in range(self.num_img):
                ri = radial_indices(self.data_storage[i].shape[2:], [center_remove, np.max(self.data_shape[2:])], center=self.center_pos[i])
                data_cr.append(np.multiply(self.data_storage[i], ri))
                
            self.data_storage = data_cr
            
            if result_visual:
                for i in range(self.num_img):
                    fig, ax = plt.subplots(1, 1, figsize=(5, 5))
                    if log_scale:
                        ax.imshow(np.log(np.mean(self.data_storage[i], axis=(0, 1))), cmap="viridis")
                    else:
                        ax.imshow(np.mean(self.data_storage[i], axis=(0, 1)), cmap="viridis")
                    ax.scatter(self.center_pos[i][1], self.center_pos[i][0], c="r", s=10)
                    ax.axis("off")
                    plt.show()
                    
    def make_input(self, min_val=0.0, max_normalize=True, rescale_0to1=False, log_scale=False, radial_flat=True, w_size=0, radial_range=None, final_dim=1):

        dataset_flat = []
        if self.dat_dim == 3:
            for i in range(self.num_img):
                dataset_flat.extend(self.data_storage[i].clip(min=min_val).reshape(-1, self.num_dim).tolist())

            dataset_flat = np.asarray(dataset_flat)
            print(dataset_flat.shape)
            
            
        if self.dat_dim == 4:
            self.radial_flat = radial_flat
            self.w_size = w_size
            self.radial_range = radial_range
            
            dataset = []
            
            if radial_flat:
                self.k_indx = []
                self.k_indy = []
                self.a_ind = []

                for r in range(radial_range[0], radial_range[1], radial_range[2]):
                    tmp_k, tmp_a = indices_at_r((radial_range[1]*2, radial_range[1]*2), r, (radial_range[1], radial_range[1]))
                    self.k_indx.extend(tmp_k[0].tolist())
                    self.k_indy.extend(tmp_k[1].tolist())
                    self.a_ind.extend(tmp_a.tolist())

                self.s_length = len(self.k_indx)
                

                for i in range(self.num_img):
                    flattened = circle_flatten(self.data_storage[i], radial_range, self.center_pos[i])

                    tmp = np.zeros((radial_range[1]*2, radial_range[1]*2))
                    tmp[self.k_indy, self.k_indx] = np.sum(flattened, axis=(0, 1))

                    fig, ax = plt.subplots(1, 1, figsize=(5, 5))
                    ax.imshow(tmp, cmap="viridis")
                    ax.axis("off")
                    fig.tight_layout()
                    plt.show()

                    dataset.append(flattened)
                    
                for i in range(self.num_img):
                    print(dataset[i].shape)
                    dataset_flat.extend(dataset[i].reshape(-1, self.s_length))
                
                    
            else:
                for i in range(self.num_img):
                    flattened = flattening(self.data_storage[i], flat_option="box", crop_dist=w_size, c_pos=self.center_pos[i])
                    if final_dim == 1:
                        dataset.append(flattened)
                    elif final_dim == 2:
                        dataset.append(flattened.reshape(self.data_shape[i][0], self.data_shape[i][1], self.w_size*2, self.w_size*2))
                    else:
                        print("Warning! 'final_dim' must be 1 or 2")
                self.s_length = (w_size*2)**2
                
                for i in range(self.num_img):
                    print(dataset[i].shape)
                    if final_dim == 1:
                        dataset_flat.extend(dataset[i].reshape(-1, self.s_length))
                    else:
                        dataset_flat.extend(dataset[i].reshape(-1, self.w_size*2, self.w_size*2))
                    
            dataset_flat = np.asarray(dataset_flat)
            print(dataset_flat.shape)
            
        if log_scale:
            dataset_flat[np.where(dataset_flat==0.0)] = 1.0
            dataset_flat = np.log(dataset_flat)
            print(np.min(dataset_flat), np.max(dataset_flat))
            
        if max_normalize:
            if final_dim == 1:
                print(np.max(dataset_flat, axis=1).shape)
                dataset_flat = dataset_flat / np.max(dataset_flat, axis=1)[:, np.newaxis]
            else:
                dataset_flat = dataset_flat / np.max(dataset_flat, axis=(1,2))[:, np.newaxis, np.newaxis]
            print(np.min(dataset_flat), np.max(dataset_flat))
            
        if rescale_0to1:
            for i in range(len(dataset_flat)):
                dataset_flat[i] = zero_one_rescale(dataset_flat[i])
                
        dataset_flat = dataset_flat.clip(min=min_val)
        print(np.min(dataset_flat), np.max(dataset_flat))
        self.total_num = len(dataset_flat)
        self.dataset_flat = dataset_flat
        self.ri = np.random.choice(self.total_num, self.total_num, replace=False)

        self.dataset_input = dataset_flat[self.ri]
        self.dataset_input = self.dataset_input.astype(np.float32)
        
    def ini_DR(self, method="nmf", num_comp=5, result_visual=True, intensity_range = "absolute"):
        self.DR_num_comp = num_comp
        if method=="nmf":
            self.DR = NMF(n_components=num_comp, init="nndsvda", solver="mu", max_iter=2000, verbose=True)
            
            self.DR_coeffs = self.DR.fit_transform(self.dataset_input)
            self.DR_comp_vectors = self.DR.components_
            
        elif method=="pca":
            self.DR = PCA(n_components=num_comp, whiten=False, 
                     random_state=np.random.randint(100), svd_solver="auto")
            
            self.DR_coeffs = self.DR.fit_transform(self.dataset_input)
            self.DR_comp_vectors = self.DR.components_
        
        elif method=="cae":
            print("in preparation...")
            return
            
        else:
            print(method+" not supported")
            return
        
        coeffs = np.zeros_like(self.DR_coeffs)
        coeffs[self.ri] = self.DR_coeffs.copy()
        self.DR_coeffs = coeffs
        self.coeffs_reshape = reshape_coeff(self.DR_coeffs, self.data_shape)
        
        if result_visual:
            if self.dat_dim == 3:
                fig, ax = plt.subplots(1, 1, figsize=(6, 4)) # all loading vectors
                for i in range(self.DR_num_comp):
                    ax.plot(self.dat_dim_range, self.DR_comp_vectors[i], "-", c=color_rep[i+1], label="loading vector %d"%(i+1))
                ax.legend(fontsize="large")
                ax.set_xlabel(self.dat_unit, fontsize=10)
                ax.tick_params(axis="x", labelsize=10)
                ax.set_facecolor("lightgray")

                fig.tight_layout()
                plt.show()
                
            elif self.dat_dim == 4:
                if self.radial_flat:
                    for i in range(self.DR_num_comp):
                        tmp = np.zeros((self.radial_range[1]*2, self.radial_range[1]*2))
                        tmp[self.k_indy, self.k_indx] = self.DR_comp_vectors[i]

                        fig, ax = plt.subplots(1, 1, figsize=(5, 5))
                        ax.imshow(tmp, cmap="inferno")
                        ax.axis("off")
                        fig.tight_layout()
                        plt.show()

                else:
                    for i in range(self.DR_num_comp):
                        fig, ax = plt.subplots(1, 1, figsize=(5, 5))
                        ax.imshow(self.DR_comp_vectors[i].reshape((self.w_size*2, self.w_size*2)), cmap="inferno")
                        ax.axis("off")
                        fig.tight_layout()
                        plt.show()

            if intensity_range == "relative":
                for i in range(self.num_img):
                    fig, ax = plt.subplots(1, self.DR_num_comp, figsize=(5*self.DR_num_comp, 5))
                    for j in range(self.DR_num_comp):
                        tmp = ax[j].imshow(self.coeffs_reshape[i][:, :, j], cmap="inferno")
                        ax[j].set_title("loading vector %d map"%(j+1), fontsize=10)
                        ax[j].axis("off")
                        fig.colorbar(tmp, cax=fig.add_axes([0.92, 0.15, 0.04, 0.7]))
                    fig.suptitle(self.file_adr[i])
                    plt.show()
            else:               
                min_val = np.min(coeffs)
                max_val = np.max(coeffs)
                for i in range(self.num_img):
                    fig, ax = plt.subplots(1, self.DR_num_comp, figsize=(5*self.DR_num_comp, 5))
                    for j in range(self.DR_num_comp):
                        tmp = ax[j].imshow(self.coeffs_reshape[i][:, :, j], vmin=min_val, vmax=max_val, cmap="inferno")
                        ax[j].set_title("loading vector %d map"%(j+1), fontsize=10)
                        ax[j].axis("off")
                        fig.colorbar(tmp, cax=fig.add_axes([0.92, 0.15, 0.04, 0.7]))
                    fig.suptitle(self.file_adr[i])
                    plt.show()

                    
    def aug_DR(self, num_comp, method="tsne", perplex=[50]):
        start = time.time()
        embeddings = []
        self.num_comp_vis = num_comp # number of dimensions of final data before clustering
        
        if method=="tsne":
            for order, p in enumerate(perplex):
                tmp_tsne = TSNE(n_components=num_comp, perplexity=p, early_exaggeration=5.0, learning_rate=300.0, 
                            init="random", n_iter=1000, verbose=0)
                tmp_tsne.fit_transform(self.DR_coeffs)
                embeddings.append(tmp_tsne.embedding_)
                print("%d perplexity %.1f finished"%(order+1, p))
                print("%.2f min have passed"%((time.time()-start)/60))
                
                fig, ax = plt.subplots(1, 1, figsize=(5, 5))
                ax.scatter(tmp_tsne.embedding_[:, 0], tmp_tsne.embedding_[:, 1], s=1, c="black")
                ax.set_title("perplexity %.1f"%p)
                fig.tight_layout()
                plt.show()

        self.embeddings = embeddings
        
    def prepare_clustering(self, sel_ind, quick_visual=True):
        
        self.aDR_coeffs = self.embeddings[sel_ind-1]
        
        comp_axes = np.arange(self.num_comp_vis)
        
        if len(comp_axes) == 2:
            self.X = np.stack((self.aDR_coeffs[:, comp_axes[0]], self.aDR_coeffs[:, comp_axes[1]]), axis=1)
            print(self.X.shape)

        elif len(comp_axes) == 3:
            self.X = np.stack((self.aDR_coeffs[:, comp_axes[0]], self.aDR_coeffs[:, comp_axes[1]], self.aDR_coeffs[:, comp_axes[2]]), axis=1)
            print(self.X.shape)
            
        if quick_visual:    
            center = np.mean(self.X, axis=0)
            dist_from_center = np.sqrt(np.sum((self.X-center)**2, axis=1))
            max_radius = np.max(dist_from_center)

            X_shift = self.X - center

            r_point = [0, -2*max_radius]
            g_point = [3**(1/2)*max_radius, max_radius]
            b_point = [-3**(1/2)*max_radius, max_radius]

            red = np.sqrt(np.sum((X_shift-r_point)**2, axis=1))
            red = red - np.max(red)*1.5
            red = -red
            red = red / np.max(red)
            green = np.sqrt(np.sum((X_shift-g_point)**2, axis=1))
            green = green - np.max(green)*1.5
            green = -green
            green = green / np.max(green)
            blue = np.sqrt(np.sum((X_shift-b_point)**2, axis=1))
            blue = blue - np.max(blue)*1.5
            blue = -blue
            blue = blue / np.max(blue)
            alpha = np.ones_like(red)
            point_colors = np.stack((red, green, blue, alpha), axis=1)

            sectors = []
            th_r = max_radius*3/5
            center_r = max_radius*1/5
            for i in range(len(X_shift)):
                if ((X_shift[i, 0]**2 + X_shift[i, 1]**2 >= th_r**2) and 
                    (X_shift[i, 0]**2 + X_shift[i, 1]**2 <= max_radius**2) and
                    (X_shift[i, 1]/3**(1/2)+X_shift[i, 0] < 0) and
                    (-X_shift[i, 1]/3**(1/2)+X_shift[i, 0] > 0)):
                    sectors.append(0)

                elif ((X_shift[i, 0]**2 + X_shift[i, 1]**2 >= th_r**2) and 
                    (X_shift[i, 0]**2 + X_shift[i, 1]**2 <= max_radius**2) and
                    (X_shift[i, 1]/3**(1/2)+X_shift[i, 0] > 0) and
                    (X_shift[i, 1] < 0)):
                    sectors.append(1)

                elif ((X_shift[i, 0]**2 + X_shift[i, 1]**2 >= th_r**2) and 
                    (X_shift[i, 0]**2 + X_shift[i, 1]**2 <= max_radius**2) and
                    (-X_shift[i, 1]/3**(1/2)+X_shift[i, 0] > 0) and
                    (X_shift[i, 1] > 0)):
                    sectors.append(2)

                elif ((X_shift[i, 0]**2 + X_shift[i, 1]**2 >= th_r**2) and 
                    (X_shift[i, 0]**2 + X_shift[i, 1]**2 <= max_radius**2) and
                    (X_shift[i, 1]/3**(1/2)+X_shift[i, 0] > 0) and
                    (-X_shift[i, 1]/3**(1/2)+X_shift[i, 0] < 0)):
                    sectors.append(3)     

                elif ((X_shift[i, 0]**2 + X_shift[i, 1]**2 >= th_r**2) and 
                    (X_shift[i, 0]**2 + X_shift[i, 1]**2 <= max_radius**2) and
                    (X_shift[i, 1]/3**(1/2)+X_shift[i, 0] < 0) and
                    (X_shift[i, 1] > 0)):
                    sectors.append(4)

                elif ((X_shift[i, 0]**2 + X_shift[i, 1]**2 >= th_r**2) and 
                    (X_shift[i, 0]**2 + X_shift[i, 1]**2 <= max_radius**2) and
                    (-X_shift[i, 1]/3**(1/2)+X_shift[i, 0] < 0) and
                    (X_shift[i, 1] < 0)):
                    sectors.append(5)

                elif X_shift[i, 0]**2 + X_shift[i, 1]**2 < center_r**2:
                    sectors.append(6)

                else:
                    sectors.append(-1)

            sectors = np.asarray(sectors, dtype=np.int32)

            fig, ax = plt.subplots(1, 2, figsize=(14, 7))
            ax[0].scatter(r_point[1], r_point[0], s=10, c="red", marker="*")
            ax[0].scatter(g_point[1], g_point[0], s=10, c="green", marker="*")
            ax[0].scatter(b_point[1], b_point[0], s=10, c="blue", marker="*")
            ax[0].scatter(X_shift[:, 1], X_shift[:, 0], s=3, c=point_colors)
            ax[0].scatter(center[1], center[0], s=5, c="red", marker="D")
            ax[1].scatter(X_shift[:, 1], X_shift[:, 0], s=3, c=sectors, cmap=custom_cmap, norm=norm)
            fig.tight_layout()
            plt.show()

            self.color_reshape = reshape_coeff(point_colors, self.data_shape)
            self.red_reshape = reshape_coeff(np.expand_dims(red, axis=1), self.data_shape)
            self.green_reshape = reshape_coeff(np.expand_dims(green, axis=1), self.data_shape)
            self.blue_reshape = reshape_coeff(np.expand_dims(blue, axis=1), self.data_shape)

            for j in range(self.num_img):
                fig, ax = plt.subplots(1, 4, figsize=(5*4, 5))
                ax[0].imshow(self.color_reshape[j])
                ax[0].axis("off")
                ax[1].imshow(self.red_reshape[j], cmap="Reds")
                ax[1].axis("off")
                ax[2].imshow(self.green_reshape[j], cmap="Greens")
                ax[2].axis("off")
                ax[3].imshow(self.blue_reshape[j], cmap="Blues")
                ax[3].axis("off")
                fig.tight_layout()
                plt.show()

            sector_label = np.array([-1,0,1,2,3,4,5,6], dtype=np.int32)
            num_sector = len(sector_label)

            if self.dat_dim == 3:
                self.sector_avg = np.zeros((num_sector, self.num_dim))

                for i in range(num_sector):
                    ind = np.where(sectors == sector_label[i])
                    if len(ind[0]) != 0:
                        self.sector_avg[i] = np.mean(self.dataset_flat[ind], axis=0)
                    else:
                        self.sector_avg[i] = np.zeros(self.num_dim)

                fig, ax = plt.subplots(1, 2, figsize=(15, 8))

                denominator = np.max(self.sector_avg, axis=1)
                self.sector_avg = self.sector_avg / denominator[:, np.newaxis]

                if -1 in sector_label:
                    for i in range(1, num_sector):
                        ax[0].plot(self.dat_dim_range, (self.sector_avg[i]), label="sector %d"%(i), c=color_rep[i])
                        ax[1].plot(self.dat_dim_range, (self.sector_avg[i]+(i-1)*0.25), label="sector %d"%(i), c=color_rep[i])

                else:
                    for i in range(0, num_sector):
                        ax[0].plot(self.dat_dim_range, (self.sector_avg[i]), label="sector %d"%(i+1), c=color_rep[i+1])
                        ax[1].plot(self.dat_dim_range, (self.sector_avg[i]+i*0.25), label="sector %d"%(i+1), c=color_rep[i+1])

                ax[0].legend(fontsize="x-large")
                ax[0].set_xlabel(self.dat_unit)
                ax[0].set_facecolor("lightgray")

                ax[1].set_xlabel(self.dat_unit)
                ax[1].set_facecolor("lightgray")

                fig.tight_layout()
                plt.show()
                
            elif self.dat_dim == 4:
                self.sector_avg = np.zeros((num_sector, self.s_length))

                for i in range(num_sector):
                    ind = np.where(sectors == int(sector_label[i]))
                    if len(ind[0]) != 0:
                        self.sector_avg[i] = np.mean(self.dataset_flat[ind], axis=0)
                    else:
                        self.sector_avg[i] = np.zeros(self.s_length)

                row_n = num_sector
                col_n = 1
                fig, ax = plt.subplots(row_n, col_n, figsize=(7, 50))


                if self.radial_flat:
                    for i, la in enumerate(sector_label):
                        tmp = np.zeros((self.radial_range[1]*2, self.radial_range[1]*2))
                        tmp[self.k_indy, self.k_indx] = self.sector_avg[i]

                        ax[i].imshow(tmp, cmap="viridis")
                        ax[i].axis("off")

                        if la == -1:
                            ax[i].set_title("not classfied")
                        else:
                            ax[i].set_title("sector %d"%(la)) 

                else:
                    for i, la in enumerate(sector_label):
                        ax[i].imshow(self.sector_avg[i].reshape((self.w_size*2, self.w_size*2)), cmap="viridis")
                        ax[i].axis("off")
                        if la == -1:
                            ax[i].set_title("not classified")
                        else:
                            ax[i].set_title("sector %d"%(la))

                fig.tight_layout()
                plt.show()


            """
            XY = np.zeros((X_shift.shape[0], 3,), dtype=float)
            dist_scale = dist_from_center / max_radius
            for i in range(X_shift.shape[0]):
                XY[i] = np.angle(np.complex(X_shift[i, 1], X_shift[i, 0])) / (2 * np.pi) % 1, 1, dist_scale[i]

            self.Xdir = hsv_to_rgb(XY)

            self.wheel_reshape = reshape_coeff(self.Xdir, self.data_shape)

            x_, y_ = np.meshgrid(np.linspace(-1, 1, 100, endpoint=True), np.linspace(-1, 1, 100, endpoint=True))
            X_, Y_ = x_ * (x_ ** 2 + y_ ** 2 < 1.0 ** 2), y_ * (x_ ** 2 + y_ ** 2 < 1.0 ** 2)
            ref_color = np.zeros(X_.shape + (3,), dtype=float)

            rad_map = np.sqrt(X_ ** 2 + Y_ ** 2) / np.amax(np.sqrt(X_ ** 2 + Y_ ** 2))
            for i in range(X_.shape[0]):
                for j in range(X_.shape[1]):
                    ref_color[i, j] = np.angle(np.complex(X_[i, j], Y_[i, j])) / (2 * np.pi) % 1, 1, rad_map[i, j]
            self.color_wheel = hsv_to_rgb(ref_color)

            fig, ax = plt.subplots(1, 2, figsize=(10, 5))
            ax[0].scatter(X_shift[:, 1], X_shift[:, 0], s=3, c=self.Xdir, alpha=0.5)
            ax[0].scatter(center[1], center[0], s=5, c="red", marker="D")
            ax[1].imshow(self.color_wheel, origin="lower")
            ax[1].axis("off")
            fig.tight_layout()
            plt.show()

            for j in range(self.num_img):
                fig, ax = plt.subplots(1, 1, figsize=(5*4, 5))
                ax.imshow(self.wheel_reshape[j])
                ax.axis("off")
                fig.tight_layout()
                plt.show()
            """            
            

    def cluster_analysis(self, method="optics", ini_params=None):
        
        self.fig = plt.figure(figsize=(10, 8))
        G = gridspec.GridSpec(2, 4)
        self.ax1 = plt.subplot(G[0, :])

        if self.num_comp_vis == 3:
            self.ax2 = plt.subplot(G[1, :2], projection="3d")

        elif self.num_comp_vis == 2:
            self.ax2 = plt.subplot(G[1, :2])

        self.ax3 = plt.subplot(G[1, 2:])

        self.optics_before = [-1, -1, -1]
        
        self.first_params = [0.05, 0.001, 0.05]
        if ini_params:
            self.first_params = ini_params
        
        st = {"description_width": "initial"}
        msample_wg = pyw.FloatText(value=self.first_params[0], description="min. # of samples in a neighborhood", style=st)
        steep_wg = pyw.FloatText(value=self.first_params[1], description="min. steepness", style=st)
        msize_wg = pyw.FloatText(value=self.first_params[2], description="min. # of samples in a cluster", style=st)
        img_wg = pyw.Select(options=np.arange(self.num_img)+1, value=1, description="image selection", style=st)

        self.clustering_widgets = pyw.interact(self.clustering, msample=msample_wg, steep=steep_wg, msize=msize_wg,  img_sel=img_wg)
        plt.show()

    def clustering(self, msample, steep, msize, img_sel):
        start = time.time()
        if msample <= 0:
            print("'min_sample' must be larger than 0")
            return

        if steep <= 0:
            print("'steepness' must be larger than 0")
            return

        if msize <= 0:
            print("'min_cluster_size' must be larger than 0")
            return

        optics_check = [msample, steep, msize]

        if self.optics_before != optics_check:
            self.ax1.cla()

            print("optics activated")
            clust = OPTICS(min_samples=msample, xi=steep, min_cluster_size=msize).fit(self.X)

            space = np.arange(len(self.X))
            reachability = clust.reachability_[clust.ordering_]
            labels = clust.labels_[clust.ordering_]
            print("activated?")
        
            for klass, color in zip(range(0, len(color_rep)), color_rep[1:]):
                Xk = space[labels == klass]
                Rk = reachability[labels == klass]
                self.ax1.plot(Xk, Rk, color, alpha=0.3)

            self.ax1.plot(space[labels == -1], reachability[labels == -1], "k.", alpha=0.3)
            self.ax1.set_ylabel('Reachability-distance')
            self.ax1.set_title('Reachability-Plot')
            #self.ax1.grid()

            self.ax2.cla()
            labels = clust.labels_
            self.labels = labels
            if self.num_comp_vis == 3:
                for klass, color in zip(range(0, len(color_rep)), color_rep[1:]):
                    Xo = self.X[labels == klass]
                    self.ax2.scatter(Xo[:, 0], Xo[:, 1], Xo[:, 2], color=color, alpha=0.3, marker='.')
                self.ax2.plot(self.X[labels == -1, 0], self.X[labels == -1, 1], self.X[labels == -1, 2], 'k+', alpha=0.1)
                self.ax2.set_title('Automatic Clustering\nOPTICS(# of clusters=%d)\n(%f, %f, %f)'%(len(np.unique(labels)), msample, steep, msize))

            elif self.num_comp_vis == 2:
                for klass, color in zip(range(0, len(color_rep)), color_rep[1:]):
                    Xo = self.X[labels == klass]
                    self.ax2.scatter(Xo[:, 0], Xo[:, 1], color=color, alpha=0.3, marker='.')
                self.ax2.plot(self.X[labels == -1, 0], self.X[labels == -1, 1], 'k+', alpha=0.1)
                self.ax2.set_title('Automatic Clustering\nOPTICS(# of clusters=%d)\n(%f, %f, %f)'%(len(np.unique(labels)), msample, steep, msize))

        self.ax3.cla()
        
        label_reshape, _, _ = label_arrangement(self.labels, self.data_shape)

        self.ax3.imshow(label_reshape[img_sel-1], cmap=custom_cmap, norm=norm)
        self.ax3.set_title("image %d"%(img_sel), fontsize=10)
        self.ax3.axis("off")

        self.fig.tight_layout()

        del self.optics_before[:]
        for i in range(len(optics_check)):
            self.optics_before.append(optics_check[i])
        print("minimum number of samples in a neighborhood: %f"%msample)
        print("minimum steepness: %f"%steep)
        print("minumum number of samples in a cluster: %f"%msize)
        print("%.2f min have passed"%((time.time()-start)/60))

        return self.labels
        
    def clustering_result(self, tf_map=False, normalize='max', log_scale=True):
        
        self.clustering_widgets.widget.close_all()
        self.label_selected = self.clustering_widgets.widget.result
        self.label_sort = np.unique(self.label_selected)
        self.label_reshape, selected, hist = label_arrangement(self.label_selected, self.data_shape)
        self.num_label = len(self.label_sort)
        print(self.label_sort) # label "-1" -> not a cluster
        print(hist) # number of data points in each cluster
        
        fig, ax = plt.subplots(1, 1, figsize=(5, 5))
        for klass, color in zip(range(0, len(color_rep)), color_rep[1:]):
            Xo = self.X[self.label_selected == klass]
            ax.scatter(Xo[:, 0], Xo[:, 1], color=color, alpha=0.3, marker='.')
        ax.plot(self.X[self.label_selected == -1, 0], self.X[self.label_selected == -1, 1], 'k+', alpha=0.1)
        fig.tight_layout()
        plt.show()
        
        # clustering result - spatial distribution of each cluster

        
        for i in range(self.num_img):
            fig, ax = plt.subplots(1, 1, figsize=(8, 8))
            ax.imshow(self.label_reshape[i], cmap=custom_cmap, norm=norm)
            ax.set_title("image %d"%(i+1), fontsize=10)
            ax.axis("off")
            fig.tight_layout()
            plt.show()

        
        if tf_map:
            for i in range(self.num_img):
                fig, ax = plt.subplots(1, self.num_label, figsize=(3*self.num_label, 3))
                for j in range(self.num_label):
                    ax[j].imshow(selected[j][i], cmap="afmhot")
                    ax[j].set_title("label %d map"%(self.label_sort[j]+1), fontsize=10)
                    ax[j].axis("off")
                    fig.tight_layout()
                plt.show()
                    
                    
        # clustering result - representative spectra (cropped)
        # average all of the spectra in each cluster
        
        if self.dat_dim == 3:
            self.lines = np.zeros((self.num_label, self.num_dim))

            for i in range(self.num_label):
                ind = np.where(self.label_selected == self.label_sort[i])
                print("number of pixels in the label %d cluster: %d"%(self.label_sort[i], hist[i]))
                self.lines[i] = np.mean(self.dataset_flat[ind], axis=0)

            fig, ax = plt.subplots(1, 2, figsize=(15, 8))

            # normalize representative spectra for comparison
            if normalize == 'max':
                denominator = np.max(self.lines, axis=1)
            elif normalize == 'min':
                denominator = np.min(self.lines, axis=1)
            self.lines = self.lines / denominator[:, np.newaxis]

            if -1 in self.label_sort:
                for i in range(1, self.num_label):
                    ax[0].plot(self.dat_dim_range, (self.lines[i]), label="cluster %d"%(i), c=color_rep[i])
                    ax[1].plot(self.dat_dim_range, (self.lines[i]+(i-1)*0.25), label="cluster %d"%(i), c=color_rep[i])

            else:
                for i in range(0, self.num_label):
                    ax[0].plot(self.dat_dim_range, (self.lines[i]), label="cluster %d"%(i+1), c=color_rep[i+1])
                    ax[1].plot(self.dat_dim_range, (self.lines[i]+i*0.25), label="cluster %d"%(i+1), c=color_rep[i+1])

            ax[0].legend(fontsize="x-large")
            ax[0].set_xlabel(self.dat_unit)
            ax[0].set_facecolor("lightgray")

            ax[1].set_xlabel(self.dat_unit)
            ax[1].set_facecolor("lightgray")

            fig.tight_layout()
            plt.show()
            
        elif self.dat_dim == 4:
            self.lines = np.zeros((self.num_label, self.s_length))

            for i in range(self.num_label):
                ind = np.where(self.label_selected == self.label_sort[i])
                print("number of pixels in the label %d cluster: %d"%(self.label_sort[i], hist[i]))
                self.lines[i] = np.mean(self.dataset_flat[ind], axis=0)

            row_n = self.num_label
            col_n = 1
            fig, ax = plt.subplots(row_n, col_n, figsize=(7, 50))


            if self.radial_flat:
                for i, la in enumerate(self.label_sort):
                    tmp = np.zeros((self.radial_range[1]*2, self.radial_range[1]*2))
                    tmp[self.k_indy, self.k_indx] = self.lines[i]

                    ax[i].imshow(tmp, cmap="viridis")
                    ax[i].axis("off")

                    if la == -1:
                        ax[i].set_title("not cluster")
                    else:
                        ax[i].set_title("cluster %d"%(la+1)) 

            else:
                for i, la in enumerate(self.label_sort):
                    if log_scale:
                        ax[i].imshow(np.log(self.lines[i].reshape((self.w_size*2, self.w_size*2))), cmap="viridis") # log scale - optional
                    else:
                        ax[i].imshow(self.lines[i].reshape((self.w_size*2, self.w_size*2)), cmap="viridis")
                    ax[i].axis("off")
                    if la == -1:
                        ax[i].set_title("not cluster")
                    else:
                        ax[i].set_title("cluster %d"%(la+1))

            fig.tight_layout()
            plt.show()

#####################################################
# functions #
#####################################################
def data_load_3d(adr, crop=None, rescale=True, DM_file=True, verbose=True):
    """
    load a spectrum image
    """
    storage = []
    shape = []
    for i, ad in enumerate(adr):
        if DM_file:
            if crop:
                temp = hs.load(ad)
                #print(temp.axes_manager)
                temp = temp.isig[crop[0]:crop[1]]
                temp = temp.data
                if rescale:
                    temp = temp/np.max(temp)
                
            else:
                temp = hs.load(ad).data
                if rescale:
                    temp = temp/np.max(temp)
        
        else:
            if crop:
                temp = tifffile.imread(ad)
                temp = temp[:, :, crop[0]:crop[1]]
                if rescale:
                    temp = temp/np.max(temp)
                
            else:
                temp = tifffile.imread(ad)
                if rescale:
                    temp = temp/np.max(temp)               

        if verbose:
            print(ad)
            print(temp.shape)
        shape.append(temp.shape)
        storage.append(temp)       
    
    shape = np.asarray(shape)
    return storage, shape


def data_load_4d(adr, rescale=False, verbose=True):
    storage = []
    shape = []   
    for i, ad in enumerate(adr):
        tmp = tifffile.imread(ad)
        if rescale:
            tmp = tmp / np.max(tmp)
        if len(tmp.shape) == 3:
            try:
                tmp = tmp.reshape(int(tmp.shape[0]**(1/2)), int(tmp.shape[0]**(1/2)), tmp.shape[1], tmp.shape[2])
                print("The scanning shape is automatically corrected")
            except:
                print("The input data is not 4-dimensional")
                print("Please confirm that all options are correct")

        if verbose:
            print(ad)
            print(tmp.shape)
        shape.append(list(tmp.shape))
        storage.append(tmp)
    
    shape = np.asarray(shape)
    return storage, shape

def zero_one_rescale(spectrum):
    """
    normalize one spectrum from 0.0 to 1.0
    """
    spectrum = spectrum.clip(min=0.0)
    min_val = np.min(spectrum)
    
    rescaled = spectrum - min_val
    
    if np.max(rescaled) != 0:
        rescaled = rescaled / np.max(rescaled)
    
    return rescaled

def binning_SI(si, bin_y, bin_x, str_y, str_x, offset, depth, rescale=True):
    """
    re-bin a spectrum image
    """
    si = np.asarray(si)
    rows = range(0, si.shape[0]-bin_y+1, str_y)
    cols = range(0, si.shape[1]-bin_x+1, str_x)
    new_shape = (len(rows), len(cols))
    
    binned = []
    for i in rows:
        for j in cols:
            temp_sum = np.mean(si[i:i+bin_y, j:j+bin_x, offset:(offset+depth)], axis=(0, 1))
            if rescale:
                binned.append(zero_one_rescale(temp_sum))
            else:
                binned.append(temp_sum)
            
    binned = np.asarray(binned).reshape(new_shape[0], new_shape[1], depth)
    
    return binned


def radial_indices(shape, radial_range, center=None):
    y, x = np.indices(shape)
    if not center:
        center = np.array([(y.max()-y.min())/2.0, (x.max()-x.min())/2.0])
    
    r = np.hypot(y - center[0], x - center[1])
    ri = np.ones(r.shape)
    
    if len(np.unique(radial_range)) > 1:
        ri[np.where(r <= radial_range[0])] = 0
        ri[np.where(r > radial_range[1])] = 0
        
    else:
        r = np.round(r)
        ri[np.where(r != round(radial_range[0]))] = 0
    
    return ri

def flattening(fdata, flat_option="box", crop_dist=None, c_pos=None):
    
    fdata_shape = fdata.shape
    if flat_option == "box":
        if crop_dist:     
            box_size = np.array([crop_dist, crop_dist])
        
            h_si = np.floor(c_pos[0]-box_size[0]).astype(int)
            h_fi = np.ceil(c_pos[0]+box_size[0]).astype(int)
            w_si = np.floor(c_pos[1]-box_size[1]).astype(int)
            w_fi = np.ceil(c_pos[1]+box_size[1]).astype(int)

            tmp = fdata[:, :, h_si:h_fi, w_si:w_fi]
            
            fig, ax = plt.subplots(1, 1, figsize=(5, 5))
            ax.imshow(np.log(np.mean(tmp, axis=(0, 1))), cmap="viridis")
            ax.axis("off")
            plt.show()
            
            tmp = tmp.reshape(fdata_shape[0], fdata_shape[1], -1)
            return tmp

        else:
            tmp = fdata.reshape(fdata_shape[0], fdata_shape[1], -1)
            return tmp

        
    elif flat_option == "radial":
        if len(crop_dist) != 3:
            print("Warning! 'crop_dist' must be a list containing 3 elements")
            
        tmp = circle_flatten(fdata, crop_dist, c_pos)
        return tmp
        
    else:
        print("Warning! Wrong option ('flat_option')")
        return
    
def circle_flatten(f_stack, radial_range, c_pos):
    k_indx = []
    k_indy = []
    
    for r in range(radial_range[0], radial_range[1], radial_range[2]):
        tmp_k, tmp_a = indices_at_r(f_stack.shape[2:], r, c_pos)
        k_indx.extend(tmp_k[0].tolist())
        k_indy.extend(tmp_k[1].tolist())
    
    k_indx = np.asarray(k_indx)
    k_indy = np.asarray(k_indy)
    flat_data = f_stack[:, :, k_indy, k_indx]
    
    return flat_data

def indices_at_r(shape, radius, center=None):
    y, x = np.indices(shape)
    if not center:
        center = np.array([(y.max()-y.min())/2.0, (x.max()-x.min())/2.0])
    r = np.hypot(y - center[0], x - center[1])
    r = np.around(r)
    
    ri = np.where(r == radius)
    
    angle_arr = np.zeros(shape)
    for i in range(shape[0]):
        for j in range(shape[1]):
            angle_arr[i, j] = np.angle(complex(x[i, j]-center[1], y[i, j]-center[0]), deg=True)
            
    angle_arr = angle_arr + 180
    angle_arr = np.around(angle_arr)
    
    ai = np.argsort(angle_arr[ri])
    r_sort = (ri[1][ai], ri[0][ai])
    a_sort = np.sort(angle_arr[ri])
        
    return r_sort, a_sort

def reshape_coeff(coeffs, new_shape):
    """
    reshape a coefficient matrix to restore the original scanning shapes.
    """
    coeff_reshape = []
    for i in range(len(new_shape)):
        temp = coeffs[:int(new_shape[i, 0]*new_shape[i, 1]), :]
        coeffs = np.delete(coeffs, range(int(new_shape[i, 0]*new_shape[i, 1])), axis=0)
        temp = np.reshape(temp, (new_shape[i, 0], new_shape[i, 1], -1))
        #print(temp.shape)
        coeff_reshape.append(temp)
        
    return coeff_reshape

def label_arrangement(label_arr, new_shape):
    """
    reshape a clustering result obtained by performing OPTICS
    """
    label_sort = np.unique(label_arr)
    num_label = len(label_sort)
    hist, edge = np.histogram(label_arr, bins=num_label)
    label_reshape = reshape_coeff(label_arr.reshape(-1, 1), new_shape)
    
    #for i in range(len(label_reshape)):
    #    label_reshape[i] = np.squeeze(label_reshape[i])
        
    selected = []
    for i in range(num_label):
        temp = []
        for j in range(len(label_reshape)):
            img_temp = np.zeros_like(label_reshape[j])
            img_temp[np.where(label_reshape[j] == label_sort[i])] = 1.0
            temp.append(img_temp)
        selected.append(temp)    
        
    return label_reshape, selected, hist