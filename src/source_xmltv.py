# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# source_xmltv.py - XMLTV source for the epg
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# kaa.epg - EPG Database
# Copyright (C) 2004-2006 Jason Tackaberry, Dirk Meyer, Rob Shortt
#
# First Edition: Jason Tackaberry <tack@sault.org>
#
# Please see the file AUTHORS for a complete list of authors.
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version
# 2.1 as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA
#
# -----------------------------------------------------------------------------

__all__ = [ 'config', 'update' ]

# Python imports
import time
import os
import calendar
import shutil
import logging

# kaa imports
from kaa import xml, TEMP
from kaa.config import Var, Group
from kaa.notifier import Timer, Thread

# get logging object
log = logging.getLogger('xmltv')

# configuration
config = \
       Group(name='xmltv', desc='''
       XMLTV settings

       You can use a xmltv rabber to populate the epg database. To activate the xmltv
       grabber you need to set 'activate' to True and specify a data_file which already
       contains the current listing or define a grabber to fetch the listings.
       Optionally you can define arguments for that grabber and the location of a
       sort program to sort the data after the grabber has finished.
       ''',
             desc_type='group',
             schema = [

    Var(name='activate',
        default=False,
        desc='Use XMLTV file to populate database.'
       ),

    Var(name='data_file',
        default='',
        desc='Location of XMLTV data file.'
       ),

    Var(name='grabber',
        default='',
        desc='If you want to run an XMLTV grabber to fetch your listings\n' +\
        'set this to the full path of your grabber program plus any\n' +\
        'additional arguments.'
       ),

    Var(name='days',
        default=5,
        desc='How many days of XMLTV data you want to fetch.'
       ),

    Var(name='sort',
        default='',
        desc='Set this to the path of the tv_sort program if you need to\n'
        'sort your listings.'
       ),
    ])


def timestr2secs_utc(timestr):
    """
    Convert a timestring to UTC (=GMT) seconds.

    The format is either one of these two:
    '20020702100000 CDT'
    '200209080000 +0100'
    """
    # This is either something like 'EDT', or '+1'
    try:
        tval, tz = timestr.split()
    except ValueError:
        tval = timestr
        tz   = str(-time.timezone/3600)

    if tz == 'CET':
        tz='+1'

    # Is it the '+1' format?
    if tz[0] == '+' or tz[0] == '-':
        tmTuple = ( int(tval[0:4]), int(tval[4:6]), int(tval[6:8]),
                    int(tval[8:10]), int(tval[10:12]), 0, -1, -1, -1 )
        secs = calendar.timegm( tmTuple )

        adj_neg = int(tz) >= 0
        try:
            min = int(tz[3:5])
        except ValueError:
            # sometimes the mins are missing :-(
            min = 0
        adj_secs = int(tz[1:3])*3600+ min*60

        if adj_neg:
            secs -= adj_secs
        else:
            secs += adj_secs
    else:
        # No, use the regular conversion

        ## WARNING! BUG HERE!
        # The line below is incorrect; the strptime.strptime function doesn't
        # handle time zones. There is no obvious function that does. Therefore
        # this bug is left in for someone else to solve.

        try:
            secs = time.mktime(strptime.strptime(timestr, xmltv.date_format))
        except ValueError:
            timestr = timestr.replace('EST', '')
            secs = time.mktime(strptime.strptime(timestr, xmltv.date_format))
    return secs



def parse_channel(info):
    """
    Parse channel information
    """
    channel_id = info.node.getattr('id')
    channel = station = name = display = None

    for child in info.node:
        # This logic expects that the first display-name that appears
        # after an all-numeric and an all-alpha display-name is going
        # to be the descriptive station name.  XXX: check if this holds
        # for all xmltv source.
        if child.name == "display-name":
            if not channel and child.content.isdigit():
                channel = child.content
            elif not station and child.content.isalpha():
                station = child.content
            elif channel and station and not name:
                name = child.content
            else:
                # something else, just remeber it in case we
                # don't have a name later
                display = child.content

    if not name:
        # set name to something. XXX: this is needed for the german xmltv
        # stuff, maybe others work different. Maybe check the <tv> tag
        # for the used grabber somehow.
        name = display or station

    db_id = info.epg.add_channel(tuner_id=channel, name=station, long_name=name)
    info.channel_id_to_db_id[channel_id] = [db_id, None]


# mapping for xmltv -> epgdb
ATTR_MAPPING = {
    'desc': 'desc',
    'sub-title': 'subtitle',
    'episode-num': 'episode',
    'category': 'genre' }

def parse_programme(info):
    """
    Parse a program node.
    """
    channel_id = info.node.getattr('channel')
    if channel_id not in info.channel_id_to_db_id:
        log.warning("Program exists for unknown channel '%s'" % channel_id)
        return

    title = None
    attr = {}

    for child in info.node.children:
        if child.name == "title":
            title = child.content
        elif child.name == "date":
            fmt = "%Y-%m-%d"
            if len(child.content) == 4:
                fmt = "%Y"
            attr['date'] = int(time.mktime(time.strptime(child.content, fmt)))
        elif child.name in ATTR_MAPPING.keys():
            attr[ATTR_MAPPING[child.name]] = child.content

    if not title:
        return

    start = timestr2secs_utc(info.node.getattr("start"))
    db_id, last_prog = info.channel_id_to_db_id[channel_id]
    if last_prog:
        # There is a previous program for this channel with no stop time,
        # so set last program stop time to this program start time.
        # XXX This only works in sorted files. I guess it is ok to force the
        # user to run tv_sort to fix this. And IIRC tv_sort also takes care of
        # this problem.
        last_start, last_title, last_attr = last_prog
        info.epg.add_program(db_id, last_start, start, last_title, **last_attr)
    if not info.node.getattr("stop"):
        info.channel_id_to_db_id[channel_id][1] = (start, title, attr)
    else:
        stop = timestr2secs_utc(info.node.getattr("stop"))
        info.epg.add_program(db_id, start, stop, title, **attr)


class UpdateInfo:
    """
    Simple class holding information we need for update information.
    """
    pass


def _update_parse_xml_thread(epg):
    """
    Thread to parse the xml file. It will also call the grabber if needed.
    """
    if config.grabber:
        log.info('grabbing listings using %s', config.grabber)
        xmltv_file = os.path.join(TEMP, 'TV.xml')
        if config.data_file:
            xmltv_file = config.data_file
        log_file = os.path.join(TEMP, 'TV.xml.log')
        # TODO: using os.system is ugly because it blocks ... but we can make this
        # nicer using kaa.notifier.Process later. We are inside a thread so it
        # seems to be ok.
        ec = os.system('%s --output %s --days %s >%s 2>%s' % \
                       (config.grabber, xmltv_file, config.days, log_file, log_file))
        if not os.path.exists(xmltv_file) or ec:
            log.error('grabber failed, see %s', log_file)
            epg.guide_changed()
            return

        if config.sort:
            log.info('sorting listings')
            shutil.move(xmltv_file, xmltv_file + '.tmp')
            os.system('%s --output %s %s.tmp >>%s 2>>%s' % \
                      (config.sort, xmltv_file, xmltv_file, log_file, log_file))
            os.unlink(xmltv_file + '.tmp')
            if not os.path.exists(xmltv_file):
                log.error('sorting failed, see %s', log_file)
                epg.guide_changed()
                return
        else:
            log.info('not configured to use tv_sort, skipping')
    else:
        xmltv_file = config.data_file

    # Now we have a xmltv file and need to parse it
    log.info('parse xml file')
    try:
        doc = xml.Document(xmltv_file, 'tv')
    except:
        log.exception('error parsing xmltv file')
        epg.guide_changed()
        return

    channel_id_to_db_id = {}
    nprograms = 0

    for child in doc:
        if child.name == "programme":
            nprograms += 1

    info = UpdateInfo()
    info.doc = doc
    info.node = doc.first
    info.channel_id_to_db_id = channel_id_to_db_id
    info.total = nprograms
    info.epg = epg
    info.progress_step = info.total / 100

    # start parser in main loop again, thread is done
    timer = Timer(_update_process_step, info)
    timer.start(0)


def _update_process_step(info):
    """
    Step in main loop for the parsing of the xmltv file. This function
    will be called in a Timer until everything is parsed.
    """
    t0 = time.time()
    while info.node:
        if info.node.name == "channel":
            parse_channel(info)
        if info.node.name == "programme":
            parse_programme(info)

        info.node = info.node.get_next()
        if time.time() - t0 > 0.1:
            # time to return to the main loop
            break

    if not info.node:
        info.epg.guide_changed()
        return False

    return True


def update(epg):
    """
    Interface to source_xmltv. This function will start the update
    process.
    """
    if not config.data_file and not config.grabber:
        log.error('XMLTV gabber not configured.')
        epg.guide_changed()
        return False
    thread = Thread(_update_parse_xml_thread, epg)
    thread.start()
    return True
