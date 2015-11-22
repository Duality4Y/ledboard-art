import math
import time
from Graphics.Graphics import Graphics

panelorder = [(2, 0), (2, 1), (2, 2),
              (1, 2), (1, 1), (1, 0),
              (0, 0), (0, 1), (0, 2),
              ]

ledboard_width, ledboard_height = 96, 48
destination = 'ledboard', 1337


def posgen(width, height):
    """ generates a sequence of positional tuples."""
    positions = []
    for y in range(0, height):
        for x in range(0, width):
            positions.append((x, y))
    return positions


def flattenl(l):
    """ Flatten a 2D list into a 1D."""
    return [x for sublist in l for x in sublist]


class NetworkConnector(object):
    """
        this object discribes a networkd connectionf,
    """
    def __init__(self, ip, port, maxsend_size=512, send_timeout=0.02):
        import socket
        self.ip = ip
        self.port = port
        self.target = (self.ip, self.port)
        self.maxsend_size = maxsend_size
        self.send_timeout = send_timeout

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.packet_start = chr(0x80)

    def compress(self, data):
        """ 'compress' a list of data in to a single string of bytes."""
        compressed = ''
        for i, byte in enumerate(data):
            compressed += chr(byte)
        return compressed

    def chunked(self, data, chunksize):
        """ yield sections 'chunks' of data, with iteration count."""
        chunk = []
        it = 0
        while(it < (len(data) / chunksize)):
            index = (it * chunksize)
            chunk = data[index:(index + chunksize)]
            yield (it, chunk)
            it += 1

    def send_packet(self, data):
        """
            first time send with reset, after send all other,
            chunks of data.
        """
        if len(data) > self.maxsend_size:
            for i, chunk in self.chunked(data, self.maxsend_size):
                if i:
                    self.sock.sendto(self.compress(chunk), self.target)
                else:
                    self.sock.sendto(self.packet_start + self.compress(chunk),
                                     self.target)
                time.sleep(self.send_timeout)
        else:
            self.sock.sendto(self.packet_start + self.compress(data),
                             self.target)

netcon = NetworkConnector('ledboard', 1337)


class LedPanel(object):
    """ this class describes a led panel of individual leds."""
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.size = width * height
        self.data = []
        for i in range(self.height):
            self.data.append([0x00] * self.width)

    """ set individual leds on the panel surface """
    def set_pixel(self, x, y, value):
        if x < 0 or x >= self.width:
            return
        if y < 0 or y >= self.height:
            return
        x, y = int(x), int(y)
        self.data[y][x] = int(value)

    """ return the value of a pixel on the panel surface"""
    def get_pixel(self, x, y):
        return self.data[y][x]

    """ return a single dimensional array"""
    def get_buffer(self):
        return flattenl(self.data)

    """ info object print"""
    def __repr__(self):
        fmtstr = "<LedPanel {Dim:%dx%d Size:%d}>"
        fmt = (self.width, self.height, self.size)
        return fmtstr % fmt


class LedBoard(object):
    """
        This class describes a object that is a ledboard
        it has multiple led panels, and the panels can be arranged,
        any way as to make the surface fit with reality of the layout,
        of the ledboard.
    """
    def __init__(self, width, height, colordepth=0x7f, numpanels=9):
        self.width = int(width)
        self.height = int(height)
        self.size = width * height
        self.numpanels = numpanels
        self.panelwidth = width / (numpanels / 3)
        self.panelheight = height / (numpanels / 3)
        self.panelsize = (self.panelwidth) * (self.panelheight)

        self.panelpositions = posgen(3, 3)

        """ create a list of panesl with known positions."""
        self.panels = {}
        for i in range(self.numpanels):
            pos = self.panelpositions[i]
            panel = LedPanel(self.panelwidth, self.panelheight)
            self.panels[pos] = panel

        self.surface = []

        self.colordepth = colordepth

    """
        this function determines in what panel which pixel
        should be set to value.
    """
    def set_pixel(self, x, y, value):
        if x < 0 or x >= self.width:
            return
        if y < 0 or y >= self.height:
            return
        if value > self.colordepth:
            value = self.colordepth
        elif value < 0:
            value = 0

        panel_pos = (x / self.panelwidth, y / self.panelheight)
        panel = self.panels[panel_pos]
        panel.set_pixel(x % self.panelwidth, y % self.panelheight, value)

    """
        with this function you can set the 2 dimensional surface directly.
        ledpanels are not updated.
    """
    def set_surface(self, surface):
        self.surface = surface

    """
        this function returns a single dimensional array,
        that represents the ledboard surface.
    """
    def get_surface(self):
        self.surface = []
        for pos in panelorder:
            panel = self.panels[pos]
            self.surface += panel.get_buffer()
        return self.surface

    """
        ledboard object info print.
    """
    def __repr__(self):
        fmtstr = "<LedBoard {Dim:%dx%d Size:%d ColorDepth: %d}>"
        fmt = (self.width, self.height, self.size, self.colordepth)
        return fmtstr % fmt


class Surface(object):
    def __init__(self, surface=None, **kwargs):
        self.__name__ = 'Surface'
        if isinstance(surface, Surface):
            self.width = surface.width
            self.height = surface.height
            self.size = surface.size
            self.color_rep = surface.color_rep
            self.color_depth = surface.color_depth
            # always create a copy, or else we get the reference.
            self.surface = dict(surface.surface)
        else:
            self.width = kwargs.get('width', 1)
            self.height = kwargs.get('height', 1)
            self.size = self.width * self.height
            self.color_rep = (0, 0, 0)
            self.color_depth = 0xFF
            self.surface = self.generate_indexes()

    """
        this function sets the thing the surface 'pixels'
        represent, by default that is a (r, g, b) tuple (red green blue)
        of values.
        but could be any compination of colors or color on it's own.
    """
    def set_color_rep(self, rep):
        self.color_rep = rep
        self.surface = self.generate_indexes()

    """
        set the color depth of the 'pixels' on a surface.
        by default this value is 0 - 0xff, and nothing higher then 0xff
        can be represented, and nothing lower then 0 can't be either.
    """
    def set_color_depth(self, depth):
        self.color_depth = depth

    """
        generates a raw dictionary with empty positional values.
        of which the value representation is self.color_rep
    """
    def generate_indexes(self):
        surface = {}
        for y in range(0, self.height):
            for x in range(0, self.width):
                index = (x, y)
                surface[index] = self.color_rep
        return surface

    """
        returns a list of positions that is sorted.
        and a list with values for those positional keys.
    """
    def get_sorted_surface(self):
        tempsurface = []
        indexes = sorted(self.surface.keys())
        for index in indexes:
            tempsurface.append(self.surface[index])
        return indexes, tempsurface

    """
        add two tuples, because point values are tuples.
    """
    def add_values(self, t1, t2):
        newval = []
        # create a copy of the values.
        t1, t2 = tuple(t1), tuple(t2)
        for i in range(0, len(t1)):
            newval.append(t1[i] + t2[i])
        return tuple(newval)

    def check_surface(self, s1, s2):
        if self.color_rep != s2.color_rep:
            raise(Exception("surface representations do not match."))
        if len(self) != len(s2):
            raise(Exception("surface size's do not match."))

    """
        add two surfaces together, only works if they are both
        the same size, and have the same color representation!
        values per pixel get added together.
    """
    def __add__(self, other):
        self.check_surface(self, other)
        surface = Surface(self)
        for pos, v1 in other:
            v2 = self[pos]
            surface[pos] = tuple(map(lambda a, b: a + b, v1, v2))
        return surface

    """
        iter through the surface.
    """
    def __getitem__(self, key):
        if(type(key) == int):
            if key < 0 or key > self.size:
                raise ValueError
            indexes, templist = self.get_sorted_surface()
            index = indexes[key]
            value = templist[key]
            return (index, value)
        if(type(key) == tuple):
            if(key not in self.surface):
                raise ValueError
            elif(len(key) == 3):
                print("point not implemented yet.")
            elif(len(key) == 2):
                return self.surface[key]
            else:
                raise ValueError
        else:
            raise TypeError

    """
        set value by position.
    """
    def __setitem__(self, key, value):
        if(type(key) == tuple and type(value) == tuple):
            if key not in self.surface:
                raise ValueError
            self.surface[key] = value
        else:
            print(type(key), type(value))
            raise TypeError

    """
        return a byte representation of of the surface.
        things like sockets need this.
    """
    def __str__(self):
        data = ''
        indexes, templist = self.get_sorted_surface()
        for color in templist:
            for component in color:
                data += str(int(component)) + ' '
        return data

    """
        return the size of the surface
    """
    def __len__(self):
        return len(self.surface)


class LedBoardGraphics(Graphics, LedBoard, Surface):
    """
        this object inherits from Graphics and LedBoard,
        so that we can do graphical things on the ledboard.
    """
    def __init__(self, width, height, colordepth=0x7F, numpanels=9):
        self.width = width
        self.height = height
        Surface.__init__(self, width, height)
        Graphics.__init__(self, width, height)
        LedBoard.__init__(self, width, height, colordepth, numpanels)

    """
        override this function so that we draw to a ledboard surface instead.
    """
    def writePixel(self, x, y, color):
        x, y = int(x), int(y)
        if x >= self.width or y >= self.height:
            return 0
        elif x < 0 or y < 0:
            return 0
        else:
            self.set_pixel(x, y, color)

    """
        scroll a surface in a axis.
    """
    def scroll(self, dir=1):
        surface = self.toMatrix(self.get_surface(), self.width)
        if dir == 1:
            surface.insert(0, surface.pop())
            LedBoard.set_surface(self, surface)
        elif dir == 2:
            pass
        elif dir == 3:
            pass
        elif dir == 4:
            pass

    """
        ledgraphics object info print.
    """
    def __repr__(self):
        fmtstr = "<LedBoard {Dim:%dx%d Size:%d ColorDepth: %d Surface: %s}>"
        fmt = (self.width, self.height, self.size, self.colordepth,
               self.__str__())
        return fmtstr % fmt


class AnalogClock(LedBoardGraphics):
    def __init__(self, width, height, offset=(0, 0)):
        self.width, self.height = width, height
        LedBoardGraphics.__init__(self, self.width, self.height)
        # self.ledGraphics = LedBoardGraphics(width, height)

        ip, port = destination

        self.color = 127
        self.x_off, self.y_off = offset
        self.radius = height / 2 - 2
        self.pos = (self.radius + 1 + self.x_off, height / 2 + self.y_off)
        self.secArmLen = self.radius - 2
        self.minArmLen = self.secArmLen - 4
        self.hourArmLen = self.minArmLen - 5

    def draw_sec_arm(self):
        ctime = math.radians(int((time.time() % 60 - 15) * 360 / 60))

        l = self.radius - 2
        cx, cy = ctime, ctime
        x, y = math.cos(cx) * l, math.sin(cy) * l
        xp, yp = self.pos
        self.drawCircle(x + xp, y + yp, 2, self.color)

    def draw_arm(self, len, time, divisor, color=0x7F):
        time = math.radians((time - 15) * (360 / divisor))
        cx, cy = time, time
        x, y = math.cos(cx) * len, math.sin(cy) * len
        xp, yp = self.pos
        x, y = x + xp, y + yp
        xs, ys = self.pos
        self.drawLine(xs, ys, x, y, color)

    def draw_face(self):
        for i in range(0, 360, 360 / 12):
            ir = math.radians(i)
            x, y = math.cos(ir) * self.radius, math.sin(ir) * self.radius
            xp, yp = self.pos
            self.drawCircle(x + xp, y + yp, 1, self.color)
            # self.ledGraphics.drawPixel(x + xp, y + yp, self.color)

    def draw(self):
        self.fill(0)
        self.draw_face()
        self.draw_arm(self.secArmLen, int(time.time() % 60), 60)
        self.draw_arm(self.minArmLen, time.time() % 3600. / 60., 60)
        self.draw_arm(self.hourArmLen, time.time() % 86400. / 3600. % 12. + 1, 12)

    def generate(self):
        self.draw()
        # for i in range(0, 10):
        #     self.ledGraphics.scroll(1)


def test_surface():
    surface = Surface(width=3, height=3)
    print("create surface: Surface(width=3, height=3)")
    alist = [surface]
    print("surface in [surface]: ", surface in alist)
    print("Surface in [surface]: ", Surface in alist)
    print("type(Surface), type(surface): ", type(Surface), type(surface))
    print("type(Surface) == type(surface): ", type(Surface) == type(surface))
    print("type(Surface) == surface: ", type(Surface) == surface)
    print("type(surface) == Surface: ", type(surface) == Surface)
    print("Surface == surface: ", Surface == surface)
    print("surface == surface: ", surface == surface)
    print("Surface is surface: ", Surface is surface)
    print("surface is surface: ", surface is surface)
    print("isinstance(Surface, surface): ", isinstance(surface, Surface))
    print("pass surface to a Surface: surface = Surface(surface)")
    surface = Surface(surface)
    print("len(surface): ", len(surface))
    print("itterate over surface with unzip values: ")
    for pos, value in surface:
        print("pos: ", pos, "value: ", value)
    print("itterate over surface with single value: ")
    for value in surface:
        print("value: ", value)
    print("value at surface[5]: ", surface[5])
    print("get value at coordinate surface[(0, 1)]: ", surface[(0, 1)])
    value = (ord('c'),) * 3
    surface[(2, 2)] = value
    print("set value at coordinate surface[(2, 2)] = ('c',)*3", surface[(2, 2)])
    value = (ord('*'),) * 3
    surface[(0, 0)] = value
    print("set value at coordinate surface[(0, 0)] = ('*',)*3", surface[(0, 0)])
    print("byte representation: ")
    print(surface)
    print("len of byte representation: ", len(str(surface)))

    print("make new surface: Surface(width=3, height=3)")
    surface = Surface(width=3, height=3)
    print("set color rep = (0)")
    surface.set_color_rep((0,))
    print("iterate and print surface: ")
    for pos, value in surface:
        print("pos: %s, value: %s" % (str(pos), str(value)))

    print("surface data test with values of 'helloword': ")
    hello = 'helloword'
    for i, (pos, value) in enumerate(surface):
        # if surface rep was (0, 0, 0)
        # then you would do (hello[i], ) * 3 for example
        surface[pos] = (ord(hello[i]), )
    print(surface)
    print("this is how you can directly "
          "manipulate data on a surface.")
    print("add two surface's s1 + s2.")
    print("incsurface: ")
    incsurface = Surface(width=3, height=3)
    incsurface.set_color_rep((0,))
    print("fill with (0x01, ).")
    for i, point in enumerate(incsurface):
        pos, value = point
        incsurface[pos] = (0x01, )
    print("incsurface: ")
    print(incsurface)
    print("combined surface: ")
    newsurface = (surface + incsurface)
    print(surface)
    print(incsurface)
    print(newsurface)


def panel_test():
    """
        test drawing on a single led panel.
    """
    panelheight = 16
    panelwidth = 32

    panel = LedPanel((0, 0), 32, 16)
    for x in range(0, panelwidth, ):
        y = math.sin(x * 32) * panelheight / 2 + 8
        panel.set_pixel(x, y, 0x7f)
    paneldata = panel.get_buffer()
    netcon.send_packet(paneldata)


def ledboard_test():
    """
        test drawing on the whole led board.
    """

    ledboard_width = 96
    ledboard_height = 48
    ledboard = LedBoard(ledboard_width, ledboard_height)
    for i in range(2, ledboard_height - 2):
        ledboard.set_pixel(i, i, 0x7f)
        ledboard.set_pixel(i + 48, i, 0x7f)
    netcon.send_packet(ledboard.get_surface())


def analog_clock_test():
    clock = AnalogClock(ledboard_width, ledboard_height)
    while(True):
        netcon.send_packet(clock)


def main():
    test_surface()

if __name__ == "__main__":
    main()
