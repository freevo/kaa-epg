# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# source_vdr.py - Get EPG information from VDR.
# -----------------------------------------------------------------------------
# $Id: $
#
# -----------------------------------------------------------------------------
# kaa-epg - Python EPG module
# Copyright (C) 2002-2005 Dirk Meyer, Rob Shortt, et al.
#
# First Edition: Rob Shortt <rob@tvcentric.com>
# Maintainer:    Rob Shortt <rob@tvcentric.com>
#
# Please see the file doc/AUTHORS for a complete list of authors.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MER-
# CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------------

# python imports
import os
import string
import logging

# vdr imports
from vdr.vdr import VDR

# get logging object
log = logging.getLogger('epg')


class UpdateInfo:
    pass

def _update_data_thread(guide, vdr_dir=None, channels_file=None, epg_file=None,
                        host=None, port=None, access_by='sid', 
                        limit_channels='conf', exclude_channels=None):
    """
    Update the guide.
    """
    log.debug('_update_data_thread')

    info = UpdateInfo()
    info.total = 0

    if not (isinstance(exclude_channels, list) or \
            isinstance(exclude_channels, tuple)):
        exclude_channels = []

    log.info('excluding channels: %s' % exclude_channels)

    info.vdr = VDR(host=host, port=port, videopath=vdr_dir,
                   channelsfile=channels_file, epgfile=epg_file,
                   close_connection=0)

    log.info('EPGFILE: %s' % vdr.epgfile)
    log.info('epg_file: %s' % epg_file)
    log.info('vdr_dir: %s' % vdr_dir)

    if vdr.epgfile and os.path.isfile(vdr.epgfile):
        log.info('Using VDR EPG from %s.' % vdr.epgfile)
        if os.path.isfile(vdr.channelsfile):
            vdr.readchannels()
        else:
            log.warning('VDR channels file not found: %s.' % vdr.channelsfile)
        vdr.readepg()
    elif vdr.host and vdr.port:
        log.info('Using VDR EPG from %s:%s.' % (vdr.host, vdr.port))
        vdr.retrievechannels()
        vdr.retrieveepg()
    else:
        log.info('No source for VDR EPG.')
        return False

    for c in info.vdr.channels:
        for e in c.events:
            info.total += 1

    info.access_by        = access_by
    info.limit_channels   = limit_channels
    info.exclude_channels = exclude_channels
    info.cur              = 0
    info.epg              = epg
    info.progress_step    = info.total / 100

    timer = kaa.notifier.Timer(_update_process_step, info)
    timer.set_prevent_recursion()
    timer.start(0)


def _update_process_step(info):

    chans = info.vdr.channels.values()
    for c in chans:
        if c.id in exclude_channels:  continue

        if string.lower(info.limit_channels) == 'epg' and not c.in_epg:
            continue
        elif string.lower(info.limit_channels) == 'conf' and not c.in_conf:
            continue
        elif string.lower(info.limit_channels) == 'both' and \
                 not (c.in_conf and c.in_epg):
            continue

        if access_by == 'name':
            access_id = c.name
        elif access_by == 'rid':
            access_id = c.rid
        else:
            access_id = c.sid

        log.info('Adding channel: %s as %s' % (c.id, access_id))

        chan_db_id = info.epg._add_channel_to_db(tuner_id=access_id, 
                                                 short_name=c.name, 
                                                 long_name=None)

        for e in c.events:
            subtitle = e.subtitle
            if not subtitle:
                subtitle = ''
            desc = e.desc
            if not desc:
                desc = ''

            info.epg._add_program_to_db(chan_db_id, e.start, int(e.start+e.dur),
                                        e.title, desc)

            info.cur +=1
            if info.cur % info.progress_step == 0:
                info.epg.signals["update_progress"].emit(info.cur, info.total)

    info.epg.signals["update_progress"].emit(info.cur, info.total)
    return False


def update(epg, vdr_dir=None, channels_file=None, epg_file=None,
           host=None, port=None, access_by='sid', limit_channels=''):
    log.debug('update')

    thread = kaa.notifier.Thread(_update_data_thread, epg, vdr_dir, 
                                 channels_file, epg_file, host, port, access_by,
                                 limit_channels)
    thread.start()

