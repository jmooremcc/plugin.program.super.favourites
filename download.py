'''
    Simple XBMC Download Script
    Copyright (C) 2013 Sean Poyser (seanpoyser@gmail.com)
    Portions Copyright (c) 2020 John Moore

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import inspect
import os
import sys
import urllib
import urllib.request
from urllib.request import urlopen
from urllib.parse import quote_plus, unquote_plus

import sfile
import utils
import xbmc
import xbmcgui


def getResponse(url, size, referer, agent, cookie):
    try:
        #url = quote_plus(url)
        req = urllib.request.Request(url)

        if len(referer) > 0:
            req.add_header('Referer', referer)

        if len(agent) > 0:
            req.add_header('User-Agent', agent)

        if len(cookie) > 0:
            req.add_header('Cookie', cookie)

        if size > 0:
            size = int(size)
            req.add_header('Range', 'bytes=%d-' % size)

        resp = urlopen(req, timeout=10)
        return resp, ''
    except Exception as e:
        return None, str(e)


def getRandomUserAgent():
    import random
    agents = []  
    agents.append('Mozilla/5.0 (Android; Mobile; rv:%d.0) Gecko/%d.0 Firefox/%d.0')

    agent = random.choice(agents) % (random.randint(10, 40), random.randint(10, 40), random.randint(10, 40))

    return agent


def download(url, dest, title=None, referer=None, agent=None, cookie=None, quiet=False):
    if not title:
        title  = 'Kodi Download'

    if not referer:
        items   = url.split('/', 3)       
        referer = items[0] + '//' + items[2]

    if not agent:
        agent  = getRandomUserAgent()

    if not cookie:
        cookie  = ''

    #quote parameters
    url     = quote_plus(url)
    dest    = quote_plus(dest)
    title   = quote_plus(title)
    referer = quote_plus(referer)
    agent   = quote_plus(agent)
    cookie  = quote_plus(cookie)

    script = inspect.getfile(inspect.currentframe())
    cmd    = 'RunScript(%s, %s, %s, %s, %s, %s, %s, %s)' % (script, url, dest, title, referer, agent, cookie, quiet)
    xbmc.executebuiltin(cmd)


def done(title, dest, downloaded):
    playing = xbmc.Player().isPlaying()

    text = xbmcgui.Window(10000).getProperty('SF-DOWNLOADED')

    if len(text) > 0:
        text += '[CR]'

    if downloaded:
        text += '%s : %s' % (dest.rsplit(os.sep)[-1], '[COLOR forestgreen]Download succeeded[/COLOR]')
    else:
        text += '%s : %s' % (dest.rsplit(os.sep)[-1], '[COLOR red]Download failed[/COLOR]')

    xbmcgui.Window(10000).setProperty('SF-DOWNLOADED', text)

    if (not downloaded) or (not playing): 
        xbmcgui.Dialog().ok(title, text)
        xbmcgui.Window(10000).clearProperty('SF-DOWNLOADED')


def doDownload(url, dest, title, referer='', agent='', cookie='', quiet=False):
    #unquote parameters
    url     = unquote_plus(url).split('|')[0]
    dest    = unquote_plus(dest)
    title   = unquote_plus(title)
    referer = unquote_plus(referer)
    agent   = unquote_plus(agent)
    cookie  = unquote_plus(cookie)

    file = dest.rsplit(os.sep, 1)[-1]

    resp, error = getResponse(url, 0, referer, agent, cookie)

    if not resp:
        xbmcgui.Dialog().ok(title, f"{dest}\nDownload failed\n{error}")
        return

    try:    content = int(resp.headers['Content-Length'])
    except: content = 0

    try:    resumable = 'bytes' in resp.headers['Accept-Ranges'].lower()
    except: resumable = False

    utils.log('Download Header')
    utils.log(resp.headers)
    utils.log(f"Quiet={quiet}")
    if resumable:
        utils.log('Download is resumable')

    if content < 1:
        xbmcgui.Dialog().ok(title, f"{file}\nUnknown filesize\nUnable to download")
        return

    size = 1024 * 1024
    mb   = content / (1024 * 1024)

    if content < size:
        size = content

    total   = 0
    notify  = 0
    errors  = 0
    count   = 0
    resume  = 0
    sleep   = 0

    if (not quiet) and xbmcgui.Dialog().yesno(title + ' - Confirm Download','Continue with download?', 'Confirm', 'Cancel') == 1:
        xbmcgui.Dialog().notification(title, 'Download Cancelled', xbmcgui.NOTIFICATION_INFO)
        return

    f = sfile.file(dest, type='wb')

    chunk  = None
    chunks = []

    while True:
        downloaded = total
        for c in chunks:
            downloaded += len(c)
        percent = min(100 * downloaded / content, 100)
        if percent >= notify:
            if not quiet:
                xbmc.executebuiltin(f"Notification({file}, {round(percent):3}% Downloaded, 10000)")

            utils.log('Download percent : %s %s %dMB downloaded : %sMB File Size : %sMB' % (str(percent)+'%', dest, mb, downloaded / 1000000, content / 1000000))

            notify += 10

        chunk = None
        error = False

        try:        
            chunk  = resp.read(size)
            if not chunk:
                if percent < 99:
                    error = True
                else:
                    while len(chunks) > 0:
                        c = chunks.pop(0)
                        f.write(c)
                        del c

                    f.close()
                    utils.log('%s download complete' % (dest))
                    if not quiet:
                        done(title, dest, True)
                    return

        except Exception as e:
            utils.log(str(e))
            error = True
            sleep = 10
            errno = 0

            if hasattr(e, 'errno'):
                errno = e.errno

            if errno == 10035: # 'A non-blocking socket operation could not be completed immediately'
                pass

            if errno == 10054: #'An existing connection was forcibly closed by the remote host'
                errors = 10 #force resume
                sleep  = 30

            if errno == 11001: # 'getaddrinfo failed'
                errors = 10 #force resume
                sleep  = 30

        if chunk:
            errors = 0
            chunks.append(chunk)
            if len(chunks) > 5:
                c = chunks.pop(0)
                f.write(c)
                total += len(c)
                del c

        if error:
            errors += 1
            count  += 1
            utils.log('%d Error(s) whilst downloading %s' % (count, dest))
            xbmc.sleep(sleep*1000)

        if (resumable and errors > 0) or errors >= 10:
            if (not resumable and resume >= 50) or resume >= 500:
                #Give up!
                utils.log('%s download canceled - too many error whilst downloading' % (dest))
                if not quiet:
                    done(title, dest, False)
                return

            resume += 1
            errors  = 0
            if resumable:
                chunks  = []
                #create new response
                utils.log('Download resumed (%d) %s' % (resume, dest))
                resp, error = getResponse(url, total, referer, agent, cookie)
            else:
                #use existing response
                pass


if __name__ == '__main__':
    if 'download.py' in sys.argv[0]:
        doDownload(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6], sys.argv[7] == 'True')