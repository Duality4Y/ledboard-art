import math
import time
import socket
from Surface import Surface
import urllib
import json

panel_width, panel_height = 32, 16
ledboard_width, ledboard_height = 96, 48

# panelorder = [(2, 0), (2, 1), (2, 2),
#               (1, 2), (1, 1), (1, 0),
#               (0, 0), (0, 1), (0, 2),
#               ]

panelorder = []
for x in range(0, 3):
    for y in range(0, 3):
        pos = (x, y)
        panelorder.append(pos)

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
        this object discribes a networkconnection,
        for a thing such as the ledboard @ tkkrlab
    """
    def __init__(self, ip, port, maxsend_size=512, send_timeout=0.005):
        self.ip = ip
        self.port = port
        self.target = (self.ip, self.port)
        self.maxsend_size = maxsend_size
        self.send_timeout = send_timeout

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.packet_start = '\x00'

    def compress(self, data):
        """ 'compress' a list of data in to a single string of bytes."""
        compressed = ''
        for i, value in enumerate(data):
            for c in value:
                compressed += chr(c)
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
                # print(i, len(chunk), chunk)
                if i:
                    self.sock.sendto('\x00' + self.compress(chunk), self.target)
                else:
                    self.sock.sendto('\x80', self.target)
                    time.sleep(0.02)
                    self.sock.sendto('\x00' + self.compress(chunk), self.target)
                time.sleep(self.send_timeout)
        else:
            self.sock.sendto('\x80' + self.compress(data),
                             self.target)
            self.sock.sendto('\x00' + self.compress(data),
                             self.target)

netcon = NetworkConnector('ledboard', 1337)


class Graphics(Surface):
    def __init__(self, width, height):
        Surface.__init__(self, width=width, height=height)

    def fill(self, color):
        self.surface = self.gen_surface(color)

    def drawPixel(self, x, y, color):
        pos = (x, y)
        if not isinstance(color, tuple):
            color = (color, )
        self.surface[pos] = color

    # http://rosettacode.org/wiki/Bitmap/Bresenham's_line_algorithm#Python
    def drawLine(self, x0, y0, x1, y1, color):
        "Bresenham's line algorithm"
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        x, y = x0, y0
        sx = -1 if x0 > x1 else 1
        sy = -1 if y0 > y1 else 1
        if dx > dy:
            err = dx / 2.0
            while x != x1:
                self.drawPixel(x, y, color)
                err -= dy
                if err < 0:
                    y += sy
                    err += dx
                x += sx
        else:
            err = dy / 2.0
            while y != y1:
                self.drawPixel(x, y, color)
                err -= dx
                if err < 0:
                    x += sx
                    err += dy
                y += sy
        self.drawPixel(x, y, color)

    def drawRect(self, x, y, width, height, color):
        x, y = int(x), int(y)
        width, height = int(width), int(height)
        # because cordinate system starts at 0
        width, height = width - 1, height - 1
        self.drawLine(x, y, x + width, y, color)
        self.drawLine(x, y + height, x + width, y + height, color)
        self.drawLine(x, y, x, y + height, color)
        self.drawLine(x + width, y, x + width, y + height, color)

    def drawCircle(self, x0, y0, radius, color):
        x0, y0 = int(x0), int(y0)
        radius = int(radius)
        # brensenham circle
        error = 1 - radius
        errory = 1
        errorx = -2 * radius
        x = radius
        y = 0
        self.drawPixel(x0, y0 + radius, color)
        self.drawPixel(x0, y0 - radius, color)
        self.drawPixel(x0 + radius, y0, color)
        self.drawPixel(x0 - radius, y0, color)
        while(y < x):
            if(error > 0):
                x -= 1
                errorx += 2
                error += errorx
            y += 1
            errory += 2
            error += errory
            self.drawPixel(x0 + x, y0 + y, color)
            self.drawPixel(x0 - x, y0 + y, color)
            self.drawPixel(x0 + x, y0 - y, color)
            self.drawPixel(x0 - x, y0 - y, color)
            self.drawPixel(x0 + y, y0 + x, color)
            self.drawPixel(x0 - y, y0 + x, color)
            self.drawPixel(x0 + y, y0 - x, color)
            self.drawPixel(x0 - y, y0 - x, color)
            self.drawPixel(x0 - y, y0 + x, color)
            self.drawPixel(x0 + y, y0 - x, color)
            self.drawPixel(x0 - y, y0 - x, color)

    """
        ledgraphics object info print.
    """
    def __repr__(self):
        return ""
        # fmtstr = "<LedBoard {Dim:%dx%d Size:%d ColorDepth: %d Surface: %s}>"
        # fmt = (self.width, self.height, self.size, self.color_depth,
        #        self.__str__())
        # return fmtstr % fmt


class AnalogClock(Graphics):
    def __init__(self, width, height, offset=(0, 0)):
        self.width, self.height = width, height
        Graphics.__init__(self, width=self.width, height=self.height)

        self.color = 0x7f
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


def ledboard_test():
    """
        test drawing on the whole led board.
        to see if indexes fit.
    """
    ledboard = Surface(width=ledboard_width, height=ledboard_height)
    for i in range(2, ledboard_height - 2):
        pos, c = (i, i), (0x7f, )
        ledboard[pos] = c
        pos, c = (i + 48, i), c
        ledboard[pos] = c

    netcon.send_packet(ledboard)


def line_test():
    ledboard = Graphics(ledboard_width, ledboard_height)
    ledboard.drawLine(0, 0, ledboard_width, ledboard_height, 0x7f)
    ledboard.drawLine(0, ledboard_height, ledboard_width, 0, 0x7f)
    ledboard.drawLine(50, 0, ledboard_width / 4, ledboard_height, 0x7f)
    ledboard.drawLine(50, ledboard_height / 3, ledboard_width / 4, 0, 0x7f)
    netcon.send_packet(ledboard)


def analog_clock_test():
    pos = (ledboard_width / 4, 0)
    clock = AnalogClock(ledboard_width, ledboard_height, pos)
    clock.generate()
    while(True):
        clock.generate()
        netcon.send_packet(clock)


def generate_image():
    url = 'http://tamahive.spritesserver.nl/gettama.php'
    response = urllib.urlopen(url)
    data = json.loads(response.read())
    tama = data['tama']
    first_hive = tama[0]
    pixeldata = first_hive['pixels']

    ledboard = Surface(width=96, height=48)

    p = 0
    for y in range(0, 32):
        for x in range(0, 48):
            value = ord(pixeldata[p])
            if value == ord('A'):
                value = 0x7f
            else:
                value = 0x00
            ledboard[(x, y + 8)] = (value, )
            p += 1

    second_hive = tama[1]
    pixeldata = second_hive['pixels']

    p = 0
    for y in range(0, 32):
        for x in range(0, 48):
            value = ord(pixeldata[p])
            if value == ord('A'):
                value = 0x7f
            else:
                value = 0x00
            ledboard[(x + 48, y + 8)] = (value, )
            p += 1

    return ledboard


def tama_test():
    while(True):
        netcon.send_packet(generate_image())
        time.sleep(0.02)


def main():
    # surface = Surface(width=48, height=96)
    # surface.set_color_rep((0, ))
    # surface.set_color_depth(0x7f)
    # surface[(1, 1)] = (0x7f,)
    # netcon.send_packet(surface)
    # analog_clock_test()
    # ledboard_test()
    # line_test()
    tama_test()

if __name__ == "__main__":
    main()
