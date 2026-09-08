"""Minimal indexed, video-only MJPEG AVI muxer (no image re-encoding).

RIFF/AVI layout: https://learn.microsoft.com/en-us/windows/win32/directshow/avi-riff-file-reference
The caller rotates paired files before the AVI 1.0 size limit.
"""
import struct


def _chunk(tag, data):
    return tag + struct.pack('<I', len(data)) + data + (b'\0' if len(data) & 1 else b'')


class MjpegAvi:
    def __init__(self, path, width, height, fps):
        self.width, self.height, self.fps = width, height, fps
        self.index = bytearray()
        self.frames = self.max_packet = 0
        self.fp = open(path, 'xb', buffering=1024 * 1024)
        self.fp.write(self._header(0, 0))
        self.movi_start = self.fp.tell() - 4  # offset of the 'movi' FOURCC

    def _header(self, file_size, movi_size):
        w, h, fps = self.width, self.height, self.fps
        avih = struct.pack('<14I', round(1e6 / fps), round(self.max_packet * fps),
                           0, 0x10, self.frames, 0, 1, self.max_packet, w, h, 0, 0, 0, 0)
        strh = struct.pack('<4s4sIHH8I4h', b'vids', b'MJPG', 0, 0, 0,
                           0, 1000, round(fps * 1000), 0, self.frames,
                           self.max_packet, 0xffffffff, 0, 0, 0, w, h)
        strf = struct.pack('<IiiHH4sIiiII', 40, w, h, 1, 24, b'MJPG', w * h * 3, 0, 0, 0, 0)
        hdrl = _chunk(b'LIST', b'hdrl' + _chunk(b'avih', avih) +
                      _chunk(b'LIST', b'strl' + _chunk(b'strh', strh) + _chunk(b'strf', strf)))
        return (b'RIFF' + struct.pack('<I', file_size) + b'AVI ' + hdrl +
                b'LIST' + struct.pack('<I', movi_size) + b'movi')

    def projected_size(self, jpeg):
        return self.fp.tell() + 8 + len(jpeg) + (len(jpeg) & 1) + 8 + len(self.index) + 16

    def write(self, jpeg):
        offset = self.fp.tell() - self.movi_start
        self.fp.write(_chunk(b'00dc', jpeg))
        self.index.extend(struct.pack('<4sIII', b'00dc', 0x10, offset, len(jpeg)))
        self.max_packet = max(self.max_packet, len(jpeg))
        self.frames += 1

    def release(self):
        if self.fp.closed:
            return
        try:
            movi_size = self.fp.tell() - self.movi_start
            self.fp.write(_chunk(b'idx1', self.index))
            file_size = self.fp.tell() - 8
            self.fp.seek(0)
            self.fp.write(self._header(file_size, movi_size))
        finally:
            self.fp.close()
