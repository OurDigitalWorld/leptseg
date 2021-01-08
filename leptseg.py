"""
leptseg.py - use leptonica segmentation for multicolumn scans

Usage (see list of options):
    leptseg.py [-h] 

For example:
    leptseg.py -f comber.jpg -ft 
    leptseg.py -f comber.jpg -ft -i 

This is based on examples supplied with the Leptonica
distribution, see README.md for more information.

- art rhyno, u. of windsor & ourdigitalworld
"""

import random
import tempfile
import time
from collections import namedtuple
from PIL import Image, ImageDraw
from subprocess import call, run
import ctypes, ctypes.util
from ctypes import cdll
import json, glob
import argparse, os, sys, shutil
from pytesseract import pytesseract

#tesseract parameters                    
TESSERACT_CONFIG="--psm 6 -c tessedit_create_hocr=1 -c tessedit_pageseg_mode=6"

#tesseract timeout - set a limit for how long to process image
TIMEOUT = 300 #in seconds

#use different colors for indicating segment approach
INITIAL_COLOR = "green"
POST_COLOR = "red"

#use namedtuple for calculating unused rectangles
Clipping = namedtuple("Clipping", "x1 y1 x2 y2")

#use class for dealing with overlapping columns
class np_region:
    def __init__(self, x0, y0, x1, y1, marked):
        self.x0 = int(x0)
        self.y0 = int(y0)
        self.x1 = int(x1)
        self.y1 = int(y1)
        self.marked = marked

#ctypes call is handled here - see leptseg.c for details
def getTextRegionsFromLept(imgname,b_flag,c_flag,d_flag,f_flag,box_w,box_h):
    leptl = ctypes.CDLL(ctypes.util.find_library("lept"),mode = ctypes.RTLD_GLOBAL)
    leptseg = cdll.LoadLibrary("./leptseg.so")
    libc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("c"))
    leptseg.leptSeg.restype = ctypes.POINTER(ctypes.c_char)
    b_string = imgname.encode("utf-8")
    boxes_p = leptseg.leptSeg(b_string,b_flag,c_flag,d_flag,f_flag,box_w,box_h)
    boxes_s = ctypes.string_at(boxes_p)
    boxes_j = json.loads(boxes_s)
    libc.free(boxes_p) #free memory from Leptonica call

    return boxes_j["boxes"]

#used for filling in gaps
def intersects(b, r):
    return b.x1 < r.x2 and b.x2 > r.x1 and b.y1 < r.y2 and b.y2 > r.y1

#used for filling in gaps
def clip_rect(b, r):
    return Clipping(
        max(b.x1, r.x1), max(b.y1, r.y1),
        min(b.x2, r.x2), min(b.y2, r.y2)
    )

#used for filling in gaps
def clip_rects(b, rects):
    return [clip_rect(b, r) for r in rects if intersects(b, r)]

#define boxes in gaps - used for columns with missing flag
#see https://stackoverflow.com/questions/60509252/how-do-i-get-the-rectangles-which-would-fill-out-a-space-excluding-some-other
#this implementation was faster than mine, though might seem kinda moot compared to OCR timings
def split_rectangles(b, rects):
    if b.x1 >= b.x2 or b.y1 >= b.y2:
        pass
    elif not rects:
        yield b
    else:
        # randomize to avoid O(n^2) runtime in typical cases
        # change this if deterministic behaviour is required
        pivot = random.choice(rects)

        above = Clipping(b.x1,     b.y1,     b.x2,     pivot.y1)
        left  = Clipping(b.x1,     pivot.y1, pivot.x1, pivot.y2)
        right = Clipping(pivot.x2, pivot.y1, b.x2,     pivot.y2)
        below = Clipping(b.x1,     pivot.y2, b.x2,     b.y2)

        yield from split_rectangles(above, clip_rects(above, rects))
        yield from split_rectangles(left,  clip_rects(left,  rects))
        yield from split_rectangles(right, clip_rects(right, rects))
        yield from split_rectangles(below, clip_rects(below, rects))

#deal with overlaps in boxes
def sortOutRegions(idx,x0,y0,x1,y1,mw):
    global regions

    for i,region in enumerate(regions):
        if i != idx and not region.marked:
            #completely enclosed region
            if x0 < region.x0 and x1 > region.x0 and y0 < region.y0 and y0 > region.y0:
                if (region.x1 - x1) > mw:
                    region.x0 = x1
                else:
                    region.marked = True
                
            #left side overlap
            if x0 < region.x0 and x1 > region.x0 and y0 > region.y0 and y0 < region.y1:
                if (region.x1 - x1) > mw:
                    region.x0 = x1
                else:
                    region.marked = True

            #right side overlap
            if x0 > region.x0 and x0 < region.x1 and y0 < region.y0 and y1 > region.y0:
                if (x0 - region.x0) > mw:
                    region.x1 = x0
                else:
                    region.marked = True

            #somewhere in the middle
            if x0 > region.x0 and x0 < region.x1 and y0 > region.y0 and y0 < region.y1:
                if (x0 - region.x0) > mw:
                    region.x1 = x0
                else:
                    region.marked = True

#convert region layout to clippings format
def regions2Clippings(regions):
    clippings = []
    for region in regions:
        if not region.marked:
            clippings.append(Clipping(x1=region.x0,
                y1=region.y0,x2=region.x1,y2=region.y1))
    return clippings


#return width
def getW(r):
    return (r.x1 - r.x0)

#convert boxes from leptonica call
def sortOutBoxes(boxes):
    global regions

    #first assemble boxes
    for box in boxes:
        x0 = int(box[0])
        y0 = int(box[1])
        x1 = x0 + int(box[2])
        y1 = y0 + int(box[3])
        regions.append(np_region(x0,y0,x1,y1,False)) 

    #now sort by width
    regions.sort(key=getW)

#columns can be hit and miss, so more happens here than with text
def sortOutRegionsCols(boxes,missing,mw,mh):
    global regions
    global w,h

    sortOutBoxes(boxes)

    #go through and deal with intersections
    for idx, region in enumerate(regions):
        if not region.marked:
            sortOutRegions(idx,region.x0,region.y0,
                region.x1,region.y1,mw)

    if missing: #fill in missing rectangles
       clippings = regions2Clippings(regions)
       mrects = split_rectangles(Clipping(x1=0, y1=0, x2=w, y2=h), 
           clippings)
       for mrect in mrects:
           #add if new rectangles fit criteria
           #if (mrect.x2 - mrect.x1) > mw and (mrect.y2 - mrect.y1) > mh:
           regions.append(np_region(mrect.x1,mrect.y1,
               mrect.x2,mrect.y2,False))
    return idx + 1

#text boxes are typically numerous and used as is
def sortOutRegionsText(boxes,mw,mh):
    global regions

    sortOutBoxes(boxes)

    return len(regions)

#use hocr syntax for coordinates
def reCalc(box_line,x1,y1):
    bline = box_line.split("bbox",1)
    cline = bline[1].split(";",1)
    qflag = False
    if len(cline) < 2:
        cline = bline[1].split("\"",1)
        qflag = True
        
    vals = cline[0].split(" ")
    h0 = int(vals[1]) + x1
    h1 = int(vals[2]) + y1
    h2 = int(vals[3]) + x1
    h3 = int(vals[4]) + y1
    if qflag:
        nline = (("%sbbox %d %d %d %d\"") % (bline[0],h0,h1,h2,h3))
    else: 
        nline = (("%sbbox %d %d %d %d;") % (bline[0],h0,h1,h2,h3))
    return nline + cline[1]

#adjust coordinates for overall image
def adjCoords(tmp_path,hocr_file,region):
    hout = open("%s/%08d_%08d_%08d_%08d.hocr" % 
        (tmp_path,region.x0,region.y0,region.x1,region.y1),"w")
    with open(hocr_file) as fp:
         line = fp.readline()
         while line:
             hout_line = line
             if "class=\'ocr_carea\'" in hout_line or "class=\'ocr_par\'" in hout_line:
                 hout_line = reCalc(line,region.x0,region.y0)
             elif "class=\'ocr_line\'" in hout_line or "class=\'ocrx_word\'" in hout_line:
                 hout_line = reCalc(line,region.x0,region.y0)
             hout.write(hout_line)
             line = fp.readline()
    hout.close()
    fp.close()
                     
#write out modified hocr
def reVamp(line):
    global block_cnt, par_cnt, line_cnt, word_cnt
    hline = line.split("id=",1)
    bline = hline[1].split("bbox",1)
    nline = ""

    if "class=\'ocr_carea\'" in line:
        block_cnt += 1
        prefix = line.split( "class=\'ocr_carea\'")
        nline = "%sclass=\'ocr_carea\' id=\'block_1_%d\' " % (prefix[0],block_cnt)
        nline += "title=\"bbox"
    elif "class=\'ocr_par\'" in line:
        par_cnt += 1
        prefix = line.split("class=\'ocr_par\'")
        nline = "%sclass=\'ocr_par\' id=\'par_1_%d\' " % (prefix[0],par_cnt)
        nline += "title=\"bbox"
    elif "class=\'ocr_line\'" in line:
        line_cnt += 1
        prefix = line.split("class=\'ocr_line\'")
        nline = "%sclass=\'ocr_line\' id=\'line_1_%d\' " % (prefix[0],line_cnt)
        nline += "title=\"bbox"
    elif "class=\'ocr_caption\'" in line:
        line_cnt += 1
        prefix = line.split("class=\'ocr_caption\'")
        nline = "%sclass=\'ocr_caption\' id=\'line_1_%d\' " % (prefix[0],line_cnt)
        nline += "title=\"bbox"
    elif "class=\'ocr_textfloat\'" in line:
        line_cnt += 1
        prefix = line.split("class=\'ocr_textfloat\'")
        nline = "%sclass=\'ocr_textfloat\' id=\'line_1_%d\' " % (prefix[0],line_cnt)
        nline += "title=\"bbox"
    elif "class=\'ocrx_word\'" in line:
        word_cnt += 1
        prefix = line.split("class=\'ocrx_word\'")
        nline = "%sclass=\'ocrx_word\' id=\'word_1_%d\' " % (prefix[0],word_cnt)
        nline += "title=\'bbox"
    nline += bline[1]
    return nline

#bring together hocr files
def mergeHocr(hocr_set,hocr_file,img_file):
    global w, h
    global block_cnt, par_cnt, line_cnt, word_cnt

    #hocr counters
    block_cnt = 0
    par_cnt = 0 
    line_cnt = 0 
    word_cnt = 0

    hout = open(hocr_file,"w")
    hfiles = sorted(glob.glob(hocr_set))
    started = False
    section = False
    for hfile in hfiles:
        with open(hfile) as fp:
             line = fp.readline()
             while line:
                 if not started:
                     hout.write(line)
                     if "<body>" in line:
                         started = True
                         hout.write(" <div class=\'ocr_page\' id='page_1' ")
                         hout.write("title=\'image \"%s\"; bbox 0 0 " % img_file)
                         hout.write("%d %d; ppageno 0\'>\n" % (w,h))
                 if not "class=\'ocr_page" in line and "bbox " in line:
                     hout_line = reVamp(line)
                     hout.write(hout_line)
                     section = True
                 if section and "</div>" in line:
                     hout.write(line)
                     section = False
                 if section and (line.lstrip().startswith("</span>") or line.lstrip().startswith("</p>")):
                     hout.write(line)
                 line = fp.readline()

    hout.write(" </div>\n")
    hout.write("</body>\n")
    hout.write("</html>")

    hout.close()
    fp.close()

#run through region identification
def runThruSegProcess(infile,b_flag,c_flag,d_flag,f_flag,
    missing,minw,minh,edge,image_only,tmp_path):

    global regions
    global img, imgc, rimg

    rimgc = INITIAL_COLOR

    boxes = getTextRegionsFromLept(infile,b_flag,c_flag,d_flag,
        f_flag,minw,minh)

    if f_flag > 0: #use binarized image for processing
        img = Image.open(infile + ".png")

    if c_flag > 0: #columns
        lept_no = sortOutRegionsCols(boxes,missing,minw,minh)
        print("column(s) segmentation, ",end="", flush=True)
    else: #text - sentence-level segmentation
        lept_no = sortOutRegionsText(boxes,minw,minh)
        print("text/line(s) segmentation, ",end="", flush=True)
    
    print("# of regions: %d" % lept_no,end="", flush=True)
    for idx, region in enumerate(regions):
        if idx == lept_no or "_final.jpg" in infile:
            rimgc = POST_COLOR

        if not region.marked:
            #extract region
            pg_box = (region.x0-edge,region.y0-edge,
                region.x1+edge,region.y1+edge)
            roi_rect = img.crop(pg_box)

            #set up file name
            tf = tempfile.NamedTemporaryFile(suffix=".hocr")
            tf_name = tf.name.split(".hocr")
            tf_img = tf_name[0] + ".png"
            tf_hocr = tf_name[0] + "_region.hocr"
       
            roi_rect.save(tf_img)

            rw = region.x1 - region.x0
            rh = region.y1 - region.y0

            #blank out text region on original image
            img_bb = Image.new("RGB",[rw,rh],color="white")
            img.paste(img_bb,(region.x0,region.y0))

            #mark region on original image
            rimg.rectangle(((region.x0, region.y0), 
                (region.x1, region.y1)), fill=None, 
                outline=rimgc, width=5)

            #make sure source image exists
            if os.path.exists(tf_img) and not image_only:
                block = pytesseract.image_to_pdf_or_hocr(tf_img, timeout=TIMEOUT,
                    config=TESSERACT_CONFIG,
                    extension="hocr")
                writeHocr(block,tf_hocr)
                dimg = "%s/%08d_%08d_%08d_%08d.png" % (tmp_path,region.x0,region.y0,region.x1,region.y1)
                roi_rect.save(dimg)
                if os.path.exists(tf_hocr):
                    adjCoords(tmp_path,tf_hocr,region)
                roi_rect.save(dimg)
                #clean up files
                os.remove(tf_hocr)
                os.remove(tf_img)
            print(".",end="",flush=True)
        else: #region is marked to skip 
            print("-",end="",flush=True)

#write bytearray to hocr file
def writeHocr(block,fhocr):
    hfile = open(fhocr, "w+b")
    hfile.write(bytearray(block))
    hfile.close()

parser = argparse.ArgumentParser()
req_named = parser.add_argument_group("required named arguments")
req_named.add_argument("-f","--file", 
    help="input image, for example: imgs/my_image.tif")
req_named.add_argument("-sd","--skipdefault", default=False, action="store_true",
    help="do not use default Tesseract for regions left after segmentation")
req_named.add_argument("-ft","--finishtext", default=False, action="store_true",
    help="use text detection for regions left after columns")
req_named.add_argument("-l","--lang", default="eng",
    help="language for Tesseract (defaults to \"eng\")")
req_named.add_argument("-n","--nobinarize", default=False, action="store_true",
    help="skip binarization step for image")
req_named.add_argument("-i","--image", default=False, action="store_true",
    help="image only, no ocr (useful for planning)")
req_named.add_argument("-t","--text", default=False, action="store_true", 
    help="use text detection instead of column detection")
req_named.add_argument("-d","--debug", default=False, action="store_true",
    help="create images for each step of Leptonica segmenting")
req_named.add_argument("-e","--edge", default=5, type=int, 
    help="edge/margin to add to crop")
req_named.add_argument("-s","--save", default=False, action="store_true",
    help="save binarization image from Leptonica step")
req_named.add_argument("-m","--missing", default=False, action="store_true",
    help="fill in missing block(s)")
req_named.add_argument("-mw","--minwidth", default=50, type=int, 
    help="minimum width for region")
req_named.add_argument("-mh","--minheight", default=10, type=int, 
    help="minimum height for region")

args = parser.parse_args()

if args.file == None:
    print("missing input image, use '-h' parameter for syntax")
    sys.exit()

#make boolean flags C-friendly for ctypes
b_flag = 1 #binarize by default
c_flag = 1 #column regions by default
d_flag = 0 #no debug by default
f_flag = 0 #no file save by default

if args.nobinarize:
    b_flag = 0
if args.text:
    c_flag = 0
if args.debug:
    d_flag = 1
if args.save:
    f_flag = 1

img_base = args.file.split(".")[0]
img = Image.open(args.file)
w, h = img.size
imgc = img.copy()
imgc = imgc.convert("RGB")
rimg = ImageDraw.Draw(imgc)

regions = []
tmp_path = tempfile.mkdtemp()
runThruSegProcess(args.file,b_flag,c_flag,d_flag,f_flag,
    args.missing,args.minwidth,args.minheight,args.edge,args.image,
    tmp_path)

img.save(img_base + "_final.jpg")
if not args.text and not args.missing:
    if args.finishtext:
        print("!") 
        regions = []
        runThruSegProcess(img_base + "_final.jpg",b_flag,0,d_flag,f_flag,
             False,args.minwidth,args.minheight,args.edge,args.image,
             tmp_path)
        img.save(img_base + "_final.jpg") #reflect text processing
    if not args.skipdefault and not args.image:
        dimg = "%s/%08d_%08d_%08d_%08d.png" % (tmp_path,0,0,0,0)
        himg = "%s/%08d_%08d_%08d_%08d.hocr" % (tmp_path,0,0,0,0)
        img.save(dimg)
        block = pytesseract.image_to_pdf_or_hocr(dimg,
            timeout=TIMEOUT,
            extension="hocr")
        writeHocr(block,himg)

if os.path.exists(tmp_path) and not args.image:
    mergeHocr(tmp_path + "/*.hocr",img_base + ".hocr",args.file)
    shutil.rmtree(tmp_path) #clean up tmp directory

imgc.save(img_base + "_regions.jpg")
print("!") #all done
