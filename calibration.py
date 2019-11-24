import numpy as np


class Calibration:
    def __init__(self):
        self.a = None
        self.b = None
        self.c = None
        self.t = None

    def apply_calibration(self, frame):
        e_frame = np.zeros(65536, dtype="float32")
        hit = np.nonzero(frame)

        for y in hit[0]:
            tot = frame[y]
            energy = 0
            A = self.a[y]
            T = self.t[y]
            B = self.b[y] - A * T - tot
            C = T * frame[y] - self.b[y] * T - self.c[y]

            if A != 0 and (B * B - 4.0 * A * C) >= 0:
                energy = ((B * -1) + np.sqrt(B * B - 4.0 * A * C)) / 2.0 / A
                if energy < 0:
                    energy = 0

            e_frame[y] = energy
        return e_frame

    def load_file(self, fobj):
        return [list(map(float, line.split())) for line in fobj.readlines()]

    def load_calib_a(self, filename):
        with open(filename, 'r') as a:
            file_a = self.load_file(a)
            self.a = np.array(file_a).flatten()

    def load_calib_b(self, filename):
        with open(filename, 'r') as b:
            file_b = self.load_file(b)
            self.b = np.array(file_b).flatten()

    def load_calib_c(self, filename):
        with open(filename, 'r') as c:
            file_c = self.load_file(c)
            self.c = np.array(file_c).flatten()

    def load_calib_t(self, filename):
        with open(filename, 'r') as t:
            file_t = self.load_file(t)
            self.t = np.array(file_t).flatten()
