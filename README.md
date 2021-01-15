leptseg
=======

This project attempts to leverage [Leptonica](https://github.com/DanBloomberg/leptonica)
for segmenting multicolumn scans for use with [Tesseract](https://github.com/tesseract-ocr/tesseract)
from a Python environment. The calls to Leptonica have been done
with [ctypes](https://docs.python.org/3/library/ctypes.html), with the
results passed back in JSON format. There are some examples in this
[Google Drive folder](https://drive.google.com/drive/folders/1-471-cpDftxVYjX9bs6lFg1RGiInVh2h?usp=sharing),
it is hard to generalize when this approach might be useful but 
a possible workflow would be to select some representative images and use the "-i"
parameter to get a sense of the segmentation layout. Pages with less
than 3 columns probably will not benefit much, this work is far more geared to
the multicolumn wonders that are historic newspapers.

The Leptonica code in _leptseg.c_ can be compiled with gcc:

```
make
```

For the most part it simply brings together samples from the Leptonica
distribution, particularly:

```
prog/binarize_set.c
src/pageseg.c
```
 
For _leptseg.py_, there are several options:

```
usage: leptseg.py [-h] [-f FILE] [-sd] [-ft] [-l LANG] [-n] [-i] [-t] [-d]
                  [-e EDGE] [-r ERODE] [-s] [-m] [-mw MINWIDTH]
                  [-mh MINHEIGHT]

optional arguments:
  -h, --help            show this help message and exit

required named arguments:
  -f FILE, --file FILE  input image, for example: imgs/my_image.tif
  -sd, --skipdefault    do not use default Tesseract for regions left after
                        segmentation
  -ft, --finishtext     use text detection for regions left after columns
  -l LANG, --lang LANG  language for Tesseract (defaults to "eng")
  -n, --nobinarize      skip binarization step for image
  -i, --image           image only, no ocr (useful for planning)
  -t, --text            use text detection instead of column detection
  -d, --debug           create images for each step of Leptonica segmenting
  -e EDGE, --edge EDGE  edge/margin to add to crop
  -r ERODE, --erode ERODE
                        erode black text on image
  -s, --save            save binarization image from Leptonica step
  -m, --missing         fill in missing block(s)
  -mw MINWIDTH, --minwidth MINWIDTH
                        minimum width for region
  -mh MINHEIGHT, --minheight MINHEIGHT
                        minimum height for region
```

With the caveat that there is probably much more that is possible
with Leptonica than what is described here, an often useful strategy
for newspaper digitization is to 
use Leptonica to identify possible columns and text lines in a scanned
image. Using a newspaper page that was highlighted in 
[a great post](http://blog.archive.org/2020/08/21/can-you-help-us-make-the-19th-century-searchable/)
from [Brewster Kahle](http://blog.archive.org/author/brewster/) of
the amazing [Internet Archive](https://archive.org/), the
front page of the December 15, 1848 edition of *The North Star* is
shown below.
![North Start front page](https://github.com/OurDigitalWorld/leptseg/blob/main/misc/north_star.jpg?raw=true)
You can see right away that there are several columns on the page, and that the
page itself is very text-rich. To get a sense of what can
be detected with the Leptonica code here, the following syntax
could be used:

```
leptseg.py -f north_star.tif -ft -i
```

Depending on the image format, you might see a few warning errors, 
for example, *Error in numaGetIValue: index not valid*,
but the command will hopefully complete and give some indication
of the number of segments or _regions_ detected. The use of the
"-i" or "--image" flag is key, it ensures that the command does not invoke 
Tesseract (or, more specifically, [pytesseract](https://pypi.org/project/pytesseract/)),
but produces two new images. One has a *_regions* suffix and one has a *_final* suffix. 
The regions file is usually of more interest, but the "final" file, in
this case, *north_star_final.jpg*, will show the original page with
the identified regions removed. Unless the "-sd" or "--skip-default" flag is used,
this page will get a final pass through Tesseract to catch any
text missed by the regions. 

It is well worth determining ahead of time if there is any advantage in
using additional segmentation. The *regions* image, in this case, *north_star_regions.jpg*,
will show the original image with boxes drawn around the identified 
segments, as shown below.

![North Start front page with segments](https://github.com/OurDigitalWorld/leptseg/blob/main/misc/north_star_regions.jpg?raw=true)

The <span style="color:green">green</span> boxes will be potential
columns and the <span style="color:red">red</span> boxes will be 
individual text lines or bigger groupings of text in regions where
columns are not detected. There is a "-m" or "--missing'
flag to simply define leftover boxes
based on what is _not_ detected but the text line approach is usually preferable
since the margins and other spurious non-text areas of the page will get included
otherwise.

Although Leptonica can do a remarkable job of detecting individual lines,
it is usually preferable to use the closest approximation to a column
as possible. Tesseract has built-in segmentation on its own, it is really
only the extremes found in newspapers and other column-centric publications where
these steps are sometimes worthwhile. As well, breaking down a page into lines will
often mean much slower throughput, as can be seen in the results described in
the [Google Drive folder](https://drive.google.com/drive/folders/1-471-cpDftxVYjX9bs6lFg1RGiInVh2h?usp=sharing).
If the segmentation looks promising, re-issue the command without the 
"-i" parameter to include Tesseract processing. The results should end
up in one file in [hOCR] (https://en.wikipedia.org/wiki/HOCR) format,
in this case, *north_star.hocr*.

An advantage of Tesseract's hOCR implementation is that it includes coordinate
information for each word. This is useful for many purposes, including highlighting
terms on an image for discovery purposes, but it also allows collecting words
based on the geometry of the image. This is utilized in comparing the OCR
of the image in the shared [Google Drive folder](https://drive.google.com/drive/folders/1-471-cpDftxVYjX9bs6lFg1RGiInVh2h?usp=sharing)
and the associated XSLT file, *hocr_text.xsl* is included here. For example,
extracting the words in the second of the *North Star* page column could be done as follows.

```
saxonb-xslt -o second_column.txt north_star.hocr hocr_text.xsl x0=1550 y0=1500 x1=2500 y1=9475
```

Comparing OCR results can be a painful process, especially with newspapers,
but using coordinates can break the task up into more manageable subsets. The
workbooks in the shared folder illustrate this approach in more detail.

My thanks to the Internet Archive for all of the great work they do,
and to my colleagues at [OurDigitalWorld](https://ourdigitalworld.net/) and the 
[Centre for Digital Scholarship](https://cdigs.uwindsor.ca/) for supporting
and encouraging these kinds of projects to help digitize newspaper collections.

art rhyno [ourdigitalworld/cdigs](https://github.com/artunit)
