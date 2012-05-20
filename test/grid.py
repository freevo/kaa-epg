import time
import kaa
import kaa.epg



def local():
    def callback(id, extrainfo):
        extrainfo['test'] = 'db_id : %d' % id
    guide = kaa.epg.load('test.db')
    guide.register_program_callback(callback)


@kaa.coroutine()
def remote():
    g = kaa.epg.connect(('localhost', 10000))
    yield kaa.inprogress(g.signals['connected'])

def test():
    channels = kaa.epg.get_channels()
    programs= kaa.epg.search(channels[:2], time=(time.time(), time.time() + (3 * 60 * 60))).wait()

    #Separate into grid arrays
    channel_programs = [[], []]
    map_channel_programs = {channels[0]:channel_programs[0], channels[1]:channel_programs[1]}
    for program in programs:
        map_channel_programs[program.channel].append(program)


    for i,programs in enumerate(channel_programs):
        print channels[i].name, len(programs)
        for program in programs:
            print 'Title:', program.title, '(', program.start, '->', program.stop, ')'
            assert(program.channel == channels[i])
            assert(hasattr(program, 'test'))
            assert(program.test == 'db_id : %d' % program.db_id[1])
        print


if 0:
    print 'Local'
    local()

if 1:
    print 'Remote'
    remote().wait()

test()