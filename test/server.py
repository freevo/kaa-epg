import time
import kaa.epg


def callback(row, extrainfo):
    extrainfo['test'] = 'db_id : %d' % row['id']

guide = kaa.epg.load('test.db')
guide.signals['program-retrieved'].connect(callback)

print kaa.epg.get_channels()

kaa.epg.listen(('localhost', 10000))
kaa.main.run()
