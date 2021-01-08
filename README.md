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
the multicolumn monsters that are historic newspapers.

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
                  [-e EDGE] [-s] [-m] [-mw MINWIDTH] [-mh MINHEIGHT]

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
  -s, --save            save binarization image from Leptonica step
  -m, --missing         fill in missing block(s)
  -mw MINWIDTH, --minwidth MINWIDTH
                        minimum width for region
  -mh MINHEIGHT, --minheight MINHEIGHT
                        minimum height for region
```

To simplify a bit of what is possible with Leptonica, and to
flag from the outset that there's probably much more that is possible
than what is described here, a seemingly useful approach is to 
use Leptonica to identify possible columns and text lines in a scanned
image. Using a newspaper page that was highlighted in 
[a great post](http://blog.archive.org/2020/08/21/can-you-help-us-make-the-19th-century-searchable/)
from [Brewster Kahle](http://blog.archive.org/author/brewster/) of
the amazing [Internet Archive](https://archive.org/), the
front page of *The North Star*.
