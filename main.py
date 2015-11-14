import math
import time

panelorder = [(2, 0), (2, 1), (2, 2),
              (1, 2), (1, 1), (1, 0),
              (0, 0), (0, 1), (0, 2),
              ]


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
    def __init__(self, ip, port, maxsend_size=512, send_timeout=0.1):
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
        self.width = width
        self.height = height
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
        if value < 0 or value > self.colordepth:
            return
        panel_pos = (x / self.panelwidth, y / self.panelheight)
        panel = self.panels[panel_pos]
        panel.set_pixel(x % self.panelwidth, y % self.panelheight, value)

    """
        this function returns a single dimensional array,
        that represents the ledboard surface.
    """
    def get_surface(self):
        for pos in panelorder:
            panel = self.panels[pos]
            self.surface += panel.get_buffer()
        return self.surface
    """
        ledboard object info print.
    """
    def __repr__(self):
        fmtstr = "<LedBoard {Dim:%dx%d Size:%d ColorDepth: %d}>"
        fmt = (self.width, self.height, self.size, self.colorDepth)
        return fmtstr % fmt


netcon = NetworkConnector('ledboard', 1337)


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


def main():
    ledboard_test()

main()