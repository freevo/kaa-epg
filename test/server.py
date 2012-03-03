import time
import kaa.epg

kaa.epg.load('test.db')
print kaa.epg.get_channels()

kaa.epg.listen(('localhost', 10000))
kaa.main.run()
