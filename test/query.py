import time
import kaa
import kaa.epg

def local():
    print 'Starting'
    kaa.epg.load('test.db')
    print kaa.epg.get_channels()
    t1 = time.time()
    result = kaa.epg.search(time=(time.time(), time.time() + 60*60)).wait()
    t2 = time.time()
    for r in result:
        print r.title, r.channel
        print r.start, r.stop
        print r.credits
        print r.date
        print r.year
        print
    print t2 - t1
    result = kaa.epg.get_genres().wait()
    print result
    result = kaa.epg.search(genres=u'film').wait()
    print result

@kaa.coroutine()
def rpc():
    kaa.epg.connect(('localhost', 10000))
    yield kaa.epg.guide.signals.subset('connected').any()
    print kaa.epg.get_channels()
    print kaa.epg.guide.num_programs
    t1 = time.time()
    result = yield kaa.epg.search(time=time.time())
    t2 = time.time()
    print result
    print t2 - t1
    result = yield kaa.epg.get_genres()
    print result
    result = yield kaa.epg.get_keywords()
    print result


if 0:
    rpc()
    kaa.main.run()

if 1:
    local()

