#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "allheaders.h"

/*
    leptseg - Leptonica-based segmentation for microfilm scans

    Bring together Leptonica functions for select
    segmentation functions. These all build on Leptonica's
    existing examples, in particular:

        prog/binarize_set.c
        src/pageseg.c

    Note the Leptonica license below. 

    - art rhyno <https://github.com/artunit/>
*/

/*====================================================================*
 -  Copyright (C) 2001-2020 Leptonica.  All rights reserved.
 -
 -  Redistribution and use in source and binary forms, with or without
 -  modification, are permitted provided that the following conditions
 -  are met:
 -  1. Redistributions of source code must retain the above copyright
 -     notice, this list of conditions and the following disclaimer.
 -  2. Redistributions in binary form must reproduce the above
 -     copyright notice, this list of conditions and the following
 -     disclaimer in the documentation and/or other materials
 -     provided with the distribution.
 -
 -  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 -  ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 -  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 -  A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL ANY
 -  CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
 -  EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
 -  PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
 -  PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
 -  OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
 -  NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 -  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *====================================================================*/

static const char *jsonstart = "{\"boxes\":[";

void getBoxes(const char * imgfile, char * lbuffer, 
    int bflag, int cflag, int dflag, int fflag, 
    int boxw, int boxh) 
{
    PIX     *pix0, *pix1, *pix2;
    PIX     *pixs, *pixg, *pixg2, *pixr;
    PIXA    *pixa, *pixadb;

    /* see prog/binarize_set.c */
    PIX     *pixtext;  /* text pixels only */
    PIX     *pixhm2;   /* halftone mask; 2x reduction */
    PIX     *pixhm;    /* halftone mask;  */
    PIX     *pixtm2;   /* textline mask; 2x reduction */
    PIX     *pixtm;    /* textline mask */
    PIX     *pixvws;   /* vertical white space mask */
    PIX     *pixtb2;   /* textblock mask; 2x reduction */
    PIX     *pixtbf2;  /* textblock mask; 2x reduction; small comps filtered */
    PIX     *pixtb;    /* textblock mask */

    l_int32  d, h, i, n, w, htfound, ival, tlfound;
    l_int32  xb, yb, wb, hb, threshval;
    l_uint32 val;

    char    buffer[100];

    strcpy(lbuffer,jsonstart);

    if ((pix0 = pixRead(imgfile)) == NULL) {
        strcat(lbuffer,"[0,0,0,0]");
    } else {
        if (bflag) {
            /* Use Contrast normalization followed by background normalization, and
                  thresholding, as per prog/binarize_sets (example 5) - seems
                  to work the best with microfilm scans. */
            pixa = pixaCreate(5);
            pixGetDimensions(pix0, &w, NULL, &d);
            pixg = pixConvertTo8(pix0, 0);
            pix1 = pixMaskedThreshOnBackgroundNorm(pixg, NULL, 10, 15, 100,
                       50, 2, 2, 0.10, &threshval);
            pixaAddPix(pixa, pix1, L_INSERT);
            pixDestroy(&pixg); 

            if (d == 32)
                pixg = pixConvertRGBToGray(pix0, 0.2, 0.7, 0.1);
            else
                pixg = pixConvertTo8(pix0, 0);

            pixOtsuAdaptiveThreshold(pixg, 5000, 5000, 0, 0, 0.1, &pix1, NULL);
            pixGetPixel(pix1, 0, 0, &val);
            ival = (l_int32)val;
            pixDestroy(&pix1);

            pixContrastNorm(pixg, pixg, 50, 50, 130, 2, 2);
            pixg2 = pixBackgroundNorm(pixg, NULL, NULL, 20, 20, 70, 40, 200, 2, 2);

            ival = L_MIN(ival, 110);
            pix1 = pixThresholdToBinary(pixg2, ival);
            pixaAddPix(pixa, pix1, L_INSERT);

            sprintf(buffer, "%s.png", imgfile);
            if (dflag) pixWrite("leptseg_000.png", pix1, IFF_PNG);
            if (fflag) pixWrite(buffer, pix1, IFF_PNG);
            pixDestroy(&pixg);
            pixDestroy(&pixg2);
        }//if

        pixadb = pixaCreate(0);
        if (bflag) 
            pixs = pixConvertTo1(pix1,128);
        else
            pixs = pixConvertTo1(pix0,128);
        pixDestroy(&pix0);
        if (dflag) pixWrite("leptseg_001.png", pixs, IFF_PNG);
                
        /* 1x reduce, to 150 -200 ppi */
        pixr = pixReduceRankBinaryCascade(pixs, 1, 0, 0, 0);
        if (dflag) pixWrite("leptseg_002.png", pixr, IFF_PNG);
     
        /* Get the halftone mask */
        pixhm2 = pixGenerateHalftoneMask(pixr, &pixtext, &htfound, pixadb);
        if (dflag) pixWrite("leptseg_003.png", pixhm2, IFF_PNG);

        /* Get the textline mask from the text pixels */
        pixtm2 = pixGenTextlineMask(pixtext, &pixvws, &tlfound, pixadb);
        if (dflag) pixWrite("leptseg_004.png", pixtm2, IFF_PNG);

        /* Get the textblock mask from the textline mask */
        pixtb2 = pixGenTextblockMask(pixtm2, pixvws, pixadb);
        if (dflag) pixWrite("leptseg_005.png", pixtb2, IFF_PNG);

        pixDestroy(&pixr);
        pixDestroy(&pixtext);
        pixDestroy(&pixvws);

        /* Remove small components from the mask, where a small
               component is defined as one with both width and height < 60 */
        pixtbf2 = NULL;
        if (pixtb2) {
            pixtbf2 = pixSelectBySize(pixtb2, 60, 60, 4, L_SELECT_IF_EITHER,
                          L_SELECT_IF_GTE, NULL);
            pixDestroy(&pixtb2);
            if (pixadb) pixaAddPix(pixadb, pixtbf2, L_COPY);
        }//if

        /* Expand all masks to full resolution, and do filling or
               small dilations for better coverage. */
        pixhm = pixExpandReplicate(pixhm2, 2);
        pix1 = pixSeedfillBinary(NULL, pixhm, pixs, 8);
        if (dflag) pixWrite("leptseg_006.png", pixhm, IFF_PNG);
        pixOr(pixhm, pixhm, pix1);
        pixDestroy(&pixhm2);
        pixDestroy(&pix1);
        if (pixadb) pixaAddPix(pixadb, pixhm, L_COPY);

        pix1 = pixExpandReplicate(pixtm2, 2);
        pixtm = pixDilateBrick(NULL, pix1, 3, 3);
        if (dflag) pixWrite("leptseg_007.png", pixhm, IFF_PNG);
        pixDestroy(&pixtm2);
        pixDestroy(&pix1);
        if (pixadb) pixaAddPix(pixadb, pixtm, L_COPY);

        if (pixtbf2) {
            pixGetDimensions(pixtbf2, &w, &h, &d);
            pix1 = pixExpandReplicate(pixtbf2, 2);
            pixtb = pixDilateBrick(NULL, pix1, 3, 3);
            if (dflag) pixWrite("leptseg_008.png", pixtb, IFF_PNG);
            pixDestroy(&pixtbf2);
            pixDestroy(&pix1);
            if (pixadb) pixaAddPix(pixadb, pixtb, L_COPY);
        } else {
            pixtb = pixCreateTemplate(pixs);  /* empty mask */
        }//if
        if (dflag) pixWrite("leptseg_009.png", pixtb, IFF_PNG);

        /* Debug: identify objects that are neither text nor halftone image */
        if (pixadb) {
            pix1 = pixSubtract(NULL, pixs, pixtm);  /* remove text pixels */
            pix2 = pixSubtract(NULL, pix1, pixhm);  /* remove halftone pixels */
            if (dflag) pixWrite("leptseg_010.png", pix2, IFF_PNG);
            pixaAddPix(pixadb, pix2, L_INSERT);
            pixDestroy(&pix1);

            if (cflag) {
                /* column based */
                PIXCMAP  *cmap;
                PTAA     *ptaa;
                PTA      *pta;
                BOX      *box;

                ptaa = pixGetOuterBordersPtaa(pixtb);
                pix1 = pixRenderRandomCmapPtaa(pixtb, ptaa, 1, 16, 1);
                if (dflag) pixWrite("leptseg_011.png", pix1, IFF_PNG);
                n = ptaaGetCount(ptaa);
                for (i = 0; i < n; i++) {
                    pta = ptaaGetPta(ptaa, i, L_CLONE);
                    box = ptaGetBoundingRegion(pta);
                    boxGetGeometry(box, &xb, &yb, &wb, &hb);
                    if (wb > boxw && hb > boxh) { 
                        if (strlen(lbuffer) != strlen(jsonstart)) strcat(lbuffer,",");
                        sprintf(buffer,"[%d,%d,%d,%d]",xb,yb,wb,hb);
                        strcat(lbuffer,buffer);
                    }//if
                    boxDestroy(&box);
                    ptaDestroy(&pta);
                }//for
                cmap = pixGetColormap(pix1);
                pixcmapResetColor(cmap, 0, 130, 130, 130);
                pixaAddPix(pixadb, pix1, L_INSERT);
                ptaaDestroy(&ptaa);
            } else {
                /* text based */
                BOXA    *boxa;
                PIXA    *pixa;
                boxa = pixConnComp(pixtm, &pixa, 8);
                pixGetDimensions(pixtm, &w, &h, NULL);
                pix1 = pixaDisplayRandomCmap(pixa, w, h);
                if (dflag) pixWrite("leptseg_011.png", pix1, IFF_PNG);
                n = pixaGetCount(pixa);
                for (i = 0; i < n; i++) {
                    pixaGetBoxGeometry(pixa, i, &xb, &yb, &wb, &hb);
                    if (wb > boxw && hb > boxh) { 
                        if (strlen(lbuffer) != strlen(jsonstart)) strcat(lbuffer,",");
                        sprintf(buffer,"[%d,%d,%d,%d]",xb,yb,wb,hb);
                        strcat(lbuffer,buffer);
                    }//if
                }//for
                pixcmapResetColor(pixGetColormap(pix1), 0, 255, 255, 255);
                pixaAddPix(pixadb, pix1, L_INSERT);
                pixaDestroy(&pixa);
                boxaDestroy(&boxa);
            }//if
        }//if
        if (dflag) pixWrite("leptseg_012.png", pix1, IFF_PNG);
        if (pixadb && dflag) {
            pixaConvertToPdf(pixadb, 0, 1.0, 0, 0, "Debug page segmentation",
                         "leptseg_debug.pdf");
        }//if
        pixaDestroy(&pixadb);
    }//if
    strcat(lbuffer,"]}");
}//getBoxes

char * leptSeg(const char * imgfile, int bflag, int cflag, int dflag,
    int fflag, int boxw, int boxh) 
{
    char    lbuffer[100000];

    getBoxes(imgfile,lbuffer, bflag, cflag, dflag, fflag, boxw, boxh);
    size_t msg_len = strlen(lbuffer) + 1;
    char * json_msg = (char *)(malloc((msg_len) * sizeof(char)));
    snprintf(json_msg, msg_len, "%s", lbuffer);

    return json_msg;
}//leptSeg
