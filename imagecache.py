#
#       Copyright (c) 2023 John Moore
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with XBMC; see the file COPYING.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#


from glob import glob
import os, os.path
from shutil import copyfile
from time import sleep
import xbmcvfs
from utils import ROOT, Progress, TITLE

_VERSION = 1.3

ROOTx = xbmcvfs.translatePath(ROOT)
IMAGECACHE = os.path.join(ROOTx,"ImageCache")
SPECIAL = 'special:'



def getConfigfiles():
    target = os.path.join(ROOTx, rf"Super Favourites{os.sep}*{os.sep}*.cfg")

    def extract(barray):
        def clean(str):
            items = ["'\n",'',"\\'",'\n']

            tmp = os.path.normpath(str)
            tmp = tmp.split('\\n')
            tmp = [x for x in tmp if x not in items]
            return tmp

        xx = barray.find('\\n')
        if xx > 0:
            tmp = barray[xx+2:].replace(')','')
            tmp = clean(tmp.replace('"',''))
            return tmp
        else:
            return [barray.replace('\n','')]

        return tmp


    files = glob(target, recursive=True)
    data = {}
    msg = "Finding Config files"
    dp = Progress(TITLE,msg)
    nfiles = float(len(files))

    for n, file in enumerate(files):
        flist = []
        dp.update(int(n/nfiles * 100), msg)
        with open(file) as fp:
            for line in fp:
                tmp = extract(line)
                flist.extend(tmp)

            data[file] = flist

    dp.update(100, msg)
    dp.close()
    return data


def cacheImage(path, copyflag=True):
    if path.find(SPECIAL) == 0:
        return path

    parent, fname = os.path.split(path)
    newfname = os.path.join(IMAGECACHE, fname)
    if parent != IMAGECACHE:
        if not os.path.exists(newfname) and copyflag:
            # print(f'copying {fname} to {newfname}')
            copyfile(path, newfname)

    return newfname



def processConfigFiles(d):
    i = 0
    msg = "Converting Config Files"
    dp = Progress(TITLE, msg)
    nitems = len(d)
    if nitems == 0:
        return

    nitems = float(nitems)
    delta = 1.0 / nitems
    n = 0

    for cfgfile, filelist in d.items():
        i += 1
        dp.update(int(float(i)/nitems * 100), msg)
        numfiles = float(len(filelist))
        i = 1
        # print(f"\n******Level {i}  ({numfiles} {'Files' if numfiles >1 else 'File'})")
        with open(cfgfile, 'w') as fp:
            for ifile in filelist:
                dp.update(int(((float(i) / numfiles) * delta + delta * n) * 100), msg)
                tag,fname = ifile.split('=')
                fname = cacheImage(fname)
                # print(f"writing out {tag}={ifile} to {cfgfile}")
                fp.write(f"{tag}={fname}\n")
                i += 1
        n += 1

    dp.update(100, msg)
    dp.close()


def checkImageCacheStatus():
    if not os.path.exists(IMAGECACHE):
        os.mkdir(IMAGECACHE)
        d = getConfigfiles()
        processConfigFiles(d)


def validateConfigFiles():
    def filelistIsValid(filelist):
        _, path = filelist[0].split('=')
        parent, _ = os.path.split(path)
        return parent == IMAGECACHE

    d = getConfigfiles()
    nitems = float(len(d))
    delta = 1.0/nitems
    n = 0
    msg = "Verifying Imported Config Files"
    dp = Progress(TITLE, msg)

    for cfgfile, filelist in d.items():
        dp.update(int(float(n)/nitems * 100), msg)
        numfiles = float(len(filelist))
        i = 1
        if len(filelist) and not filelistIsValid(filelist):
            with open(cfgfile, 'w') as fp:
                for ifile in filelist:
                    dp.update(int(((float(i) / numfiles)*delta+delta*n) * 100), msg)
                    tag,fname = ifile.split('=')
                    fname = fname.replace('\\',os.sep)
                    fname = cacheImage(fname, copyflag=False)
                    fp.write(f"{tag}={fname}\n")
                    i += 1
        n += 1

    sleep(2)
    dp.close()