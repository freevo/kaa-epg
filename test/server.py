import time
import kaa.epg


def callback(id, extrainfo):
    extrainfo['test'] = 'db_id : %d' % id

guide = kaa.epg.load('test.db')
guide.register_program_callback(callback)

print kaa.epg.get_channels()

kaa.epg.listen(('localhost', 10000))
kaa.main.run()
