import time
import kaa
import kaa.epg



def local():
    def callback(id, meta):
        meta.test = 'db_id : %d' % id
    guide = kaa.epg.load('test.db')
    guide.register_grid_callback(callback)


@kaa.coroutine()
def remote():
    g = kaa.epg.connect(('localhost', 10000))
    yield g.signals.subset('connected').any()

def test():
    channels = kaa.epg.get_channels()
    programs = kaa.epg.get_grid(channels[:2], time.time(), time.time() + (3 * 60 * 60)).wait()
    assert(len(programs) == 2)
    for i,channel in enumerate(programs):
        print 'len(Programs)', len(channel)
        for program in channel:
            assert(program.channel == channels[i])
            assert(hasattr(program, 'meta'))
            assert(program.meta.test == 'db_id : %d' % program.db_id[1])


if 1:
    print 'Local'
    local()

if 0:
    print 'Remote'
    remote().wait()

test()