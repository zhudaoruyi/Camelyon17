import cv2
import numpy as np
import math
import pdb

from skimage.filters import threshold_otsu
from skimage.transform.integral import integral_image
from openslide import OpenSlide
from openslide import open_slide
from matplotlib import pyplot as plt
from xml.etree.ElementTree import parse


def find_contours_of_xml_label(file_path_xml, level_scale):

    list_blob = []
    tree = parse(file_path_xml)
    for parent in tree.getiterator():
        for index1, child1 in enumerate(parent):
            for index2, child2 in enumerate(child1):
                for index3, child3 in enumerate(child2):
                    list_point = []
                    for index4, child4 in enumerate(child3):
                        p_x = float(child4.attrib['X'])
                        p_y = float(child4.attrib['Y'])
                        p_x = p_x * level_scale
                        p_y = p_y * level_scale
                        list_point.append([p_x, p_y])
                    if len(list_point):
                        list_blob.append(list_point)

    contours = []
    for list_point in list_blob:
        list_point_int = [[[int(round(point[0])), int(round(point[1]))]] \
                            for point in list_point]
        contour = np.array(list_point_int, dtype=np.int32)
        contours.append(contour)

    return contours 
                    

def make_mask(mask_shape, contours):

    wsi_empty = np.zeros(mask_shape[:2])
    wsi_empty = wsi_empty.astype(np.uint8)
    cv2.drawContours(wsi_empty, contours, -1, 255, -1)
    
    return wsi_empty 


def visualize_one(img):

    cv2.namedWindow("img", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("img", 1000, 1000)
    cv2.imshow("img", img)
    cv2.waitKey()
    cv2.destroyAllWindows()

def extract_patch_from_label_mask_at_x20 \
        (file_path, file_path_xml, size_patch): 

    slide_tif = OpenSlide(file_path)
    
    print('==> making contours of tissue region..')

    wsi_pil_lv_4 = slide_tif.read_region((0, 0), 4,\
            slide_tif.level_dimensions[4])
    wsi_ary_lv_4 = np.array(wsi_pil_lv_4)
    wsi_bgr_lv_4 = cv2.cvtColor(wsi_ary_lv_4, cv2.COLOR_RGBA2BGR)
    wsi_gray_lv_4 = cv2.cvtColor(wsi_bgr_lv_4, cv2.COLOR_BGR2GRAY)

# Debugging opencv coordinate system
    """
    x = 10
    y = 5
    print('before', wsi_gray_lv_4[y][x])
    cv2.circle(wsi_gray_lv_4, (x, y), 1,  255, thickness=3) 
    print('after', wsi_gray_lv_4[y][x])
    exit()
    """


    blur_lv_4 = cv2.GaussianBlur(wsi_gray_lv_4, (5, 5), 0)
    ret, wsi_bin_0255_lv_4 = cv2.threshold(blur_lv_4, 0, 255, \
                    cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
# morphology test
    """
    kernel = np.ones((5,5), dtype=np.uint8)
    otsumorph = cv2.morphologyEx(wsi_bin_0255_lv_4, cv2.MORPH_OPEN, (5,5), kernel)
    morph = cv2.morphologyEx(wsi_gray_lv_4, cv2.MORPH_OPEN, (5,5), kernel)

    cv2.namedWindow("otsu", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("otsu", 1000, 1000)
    cv2.imshow("otsu", wsi_bin_0255_lv_4)
    cv2.namedWindow("otsumorph", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("otsumorph", 1000, 1000)
    cv2.imshow("otsumorph", otsumorph)
    cv2.namedWindow("morph", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("morph", 1000, 1000)
    cv2.imshow("morph", morph)
    cv2.waitKey()
    cv2.destroyAllWindows()
    exit()
    """

    _, contours_tissue_lv_4, hierarchy = \
            cv2.findContours(wsi_bin_0255_lv_4, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
     
    print('==> making tissue mask..')

    location_path = "./visual/tissue_mask_lv_4.png"
    img = cv2.imread(location_path, 0)
    if img is not None:
        tissue_mask_lv_4 = img
    else:
        mask_shape_lv_4 = wsi_gray_lv_4.shape
        tissue_mask_lv_4 = make_mask(mask_shape_lv_4, contours_tissue_lv_4) 
        cv2.imwrite(location_path, tissue_mask_lv_4)

# Debugging mask
    """
    cv2.namedWindow("tis", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("tis", 1000, 1000)
    cv2.imshow("tis", tissue_mask_lv_4)
    cv2.waitKey()
    cv2.destroyAllWindows()
    exit()
    """

#    level_scale_4 = slide_tif.level_downsamples[4]
#    contours_label_level_4 = \
#            find_contours_of_xml_label(file_path_xml, 1. / level_scale_4)
#   
#    wsi_lv_4_shape = slide_tif.level_dimensions[1]
#    wsi_lv_4_shape = wsi_lv_4_shape[1], wsi_lv_4_shape[0]

#    wsi_label_mask_level_4 = make_label_mask(\
#                 wsi_lv_4_shape, contours_label_level_4)
#
#    wsi_pil_lv_4 = slide_tif.read_region((0, 0), 4,\
#            slide_tif.level_dimensions[4])
#    wsi_ary_lv_4 = np.array(wsi_pil_lv_4)
#    wsi_bgr_lv_4 = cv2.cvtColor(wsi_ary_lv_4, cv2.COLOR_RGBA2BGR)


    print('==> extracting patch..')

    wsi_bgr_lv_4_circle = wsi_bgr_lv_4.copy()
     
    coord_y4, coord_x4 = np.nonzero(tissue_mask_lv_4)
    length_coord = coord_x4.shape[0]
    random_index = np.random.choice(length_coord, 10, replace=False)
    list_patch_location = []

    list_title = []
    list_patch_img = []

    downsample_lv_4 = slide_tif.level_downsamples[4]
    coord_x0 = np.round(coord_x4 * downsample_lv_4)
    coord_y0 = np.round(coord_y4 * downsample_lv_4)
    coord_x0 = coord_x0.astype(np.int32)
    coord_y0 = coord_y0.astype(np.int32)

    size_patch_lv_0 = size_patch
    size_patch_lv_4 = int(round(size_patch / downsample_lv_4)) 

    check_patch_choice_ary = np.zeros(wsi_gray_lv_4.shape, dtype=np.uint8)
    slide_w, slide_h = slide_tif.dimensions
   
    print('length : ', length_coord)
    pdb.set_trace()

    index = -1000
    cnt = 0

######## start while
    while len(list_patch_location) <= 10:
        index += 1000
        x0 = coord_x0[index]
        y0 = coord_y0[index]

# check if out of range
        if (x0 + size_patch_lv_0) > slide_w or \
           (y0 + size_patch_lv_0) > slide_h:
            continue

        x4 = int(round(x0 / downsample_lv_4))
        y4 = int(round(y0 / downsample_lv_4))

# check if already chosen
        if check_patch_choice_ary[y4][x4] == 255:
            continue

# check ratio of tissue region 
        mask_patch = tissue_mask_lv_4[y4:y4+size_patch_lv_4, \
                                      x4:x4+size_patch_lv_4]

        mask_patch = mask_patch / 255
        print(np.max(mask_patch))
        print(mask_patch.shape)

        tissue_ratio = \
                np.sum(mask_patch) / (float)(size_patch_lv_4*size_patch_lv_4)
        print(tissue_ratio)

        if tissue_ratio < 0.8:
            continue

# pick the patch
        check_patch_choice_ary[y4][x4] = 255
        patch_location = np.array([x0, y0])
        list_patch_location.append(patch_location) 

# visualizing patch
        patch_pil = slide_tif.read_region( \
                (x0, y0), 0, (size_patch_lv_0,size_patch_lv_0))
        patch_ary = np.array(patch_pil)
        patch_bgr = cv2.cvtColor(patch_ary, cv2.COLOR_RGBA2BGR) 
        location_path = "./visual/patch_" + str(cnt+1) + ".png"
        cv2.imwrite(location_path, patch_bgr) 
        list_title.append('patch ' + str(cnt))
        list_patch_img.append(patch_bgr)

        cnt += 1

# visualizing (x0, y0) -> (x4, y4) dot on wsi_lv_4
        x4 = int(round(x0 / downsample_lv_4))
        y4 = int(round(y0 / downsample_lv_4))

        cv2.rectangle(wsi_bgr_lv_4_circle, \
                (x4, y4), \
                (x4+size_patch_lv_4,y4+size_patch_lv_4),\
                (0,255,0), thickness=5)
######### finish while
    
    print('==> drawing patch..')

    cv2.imwrite("./visual/draw_dot.png", wsi_bgr_lv_4_circle)

    for i in range(10):
        plt.subplot(2, 5, i+1), plt.imshow(list_patch_img[i])
        plt.title(list_title[i]), plt.xticks([]), plt.yticks([])

    plt.show()


###### Debugging tumor mask
    """
######################
    level_scale_4 = get_level_scale_from_file_path_tif(file_path, 4)
    contours_label_level_4 = \
            find_contours_of_xml_label(file_path_xml, level_scale_4)
   
    wsi_pil_lv_4 = slide_tif.read_region((0, 0), 4,\
            slide_tif.level_dimensions[4])
    wsi_ary_lv_4 = np.array(wsi_pil_lv_4)
    wsi_bgr_lv_4 = cv2.cvtColor(wsi_ary_lv_4, cv2.COLOR_RGBA2BGR)
    

    level_4_dimension = slide_tif.level_dimensions[4]
    wsi_label_mask_level_4 = make_label_mask(\
                 wsi_bgr_lv_4.shape, contours_label_level_4)

    #cv2.drawContours(wsi_bgr_lv_4, contours_label_level_4, -1, (0, 255, 0), -1)

    #plt.subplot(1, 2, 1), plt.imshow(wsi_label_mask_level_4*255, 'gray')
    #plt.title('debug'), plt.xticks([]), plt.yticks([])

    #plt.subplot(1, 2, 2), plt.imshow(wsi_bgr_lv_4)
    #plt.title('origin '), plt.xticks([]), plt.yticks([])

    #plt.show()
##########################
    """

###### Debugging draw dot 
    """
##########################
    coord_y4, coord_x4 = np.nonzero(wsi_label_mask_level_4)

    length_coord = coord_y4.shape[0]
    print ('=>drawing circles..')
    for i in range(length_coord):

        if i % 100 == 0:
            cv2.circle(wsi_bgr_lv_4, (coord_x4[i], coord_y4[i]), 3, (0,255,0), \
                        thickness=2)


    coord_y, coord_x = np.nonzero(wsi_label_mask_level_1)

    level_scale_1 = slide_tif.level_downsamples[1]
    level_scale_4 = slide_tif.level_downsamples[4]
    coord_y4d = coord_y * level_scale_1
    coord_x4d = coord_x * level_scale_1
    coord_y4d = np.round(coord_y4d / level_scale_4)
    coord_x4d = np.round(coord_x4d / level_scale_4)
    coord_y4d = coord_y4d.astype(np.int32)
    coord_x4d = coord_x4d.astype(np.int32)
    length_coord = coord_y4d.shape[0]

    wsi_bgr_lv_4d = wsi_bgr_lv_4.copy()

    print ('=>drawing circles 2..')
    for i in range(length_coord):

        if i % 1000 == 0:
            cv2.circle(wsi_bgr_lv_4d, (coord_x4d[i], coord_y4d[i]), 3, (0,255,0), \
                        thickness=2)
    
    print ('=> showing image..')

    plt.subplot(1, 2, 1), plt.imshow(wsi_bgr_lv_4)
    plt.title("level_4"), plt.xticks([]), plt.yticks([])

    plt.subplot(1, 2, 2), plt.imshow(wsi_bgr_lv_4d)
    plt.title("level_4 debug"), plt.xticks([]), plt.yticks([])
    
    cv2.imwrite('./visiual/wsi_bgr_lv_4debug.png', wsi_bgr_lv_4d)
    plt.show()
#######################
    """




def main():
    file_path = "./data/patient_099_node_4.tif"
    file_path_xml = "./data/patient_099_node_4.xml"
    #wsi_tif = OpenSlide(file_path)
    #dimension_level_4 = wsi_tif.level_dimensions[4]
    #level = 4
    #level_scale = get_level_scale_from_file_path_tif(file_path, level)
    size_patch = 960

    extract_patch_from_label_mask_at_x20 \
        (file_path, file_path_xml, size_patch)



if __name__=="__main__":
    main()
