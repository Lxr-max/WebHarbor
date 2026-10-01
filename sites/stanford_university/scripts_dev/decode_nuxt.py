#!/usr/bin/env python3
"""Minimal decoder for Nuxt __NUXT_DATA__ devalue payloads."""
import json
import sys

MARKERS = ("ShallowReactive", "Reactive", "ShallowRef", "Ref", "EmptyShallowRef", "EmptyRef")


class Decoder:
    def __init__(self, data):
        self.data = data
        self.cache = {}

    def at(self, i):
        if i in self.cache:
            return self.cache[i]
        v = self.data[i]
        out = self.resolve(v, i)
        self.cache[i] = out
        return out

    def resolve(self, v, i):
        if isinstance(v, list):
            if v and isinstance(v[0], str) and v[0] in MARKERS:
                if len(v) == 2 and isinstance(v[1], int):
                    return self.at(v[1])
                return [self.resolve(x, i) for x in v]
            # dict: alternating string keys / value indices
            if v and all(isinstance(x, str) for x in v[::2]) and len(v) % 2 == 0:
                return {v[k]: self.at(v[k + 1]) for k in range(0, len(v), 2)}
            return [self.at(x) if isinstance(x, int) else self.resolve(x, i) for x in v]
        if isinstance(v, dict):
            return {k: (self.at(x) if isinstance(x, int) else self.resolve(x, i)) for k, x in v.items()}
        return v


def decode(data):
    d = Decoder(data)
    root = 0
    # data[0] is usually a marker list; the root object follows
    if isinstance(data[0], list) and data[0] and isinstance(data[0][0], str):
        root = 1
    return d.at(root)


if __name__ == "__main__":
    payload = json.load(open(sys.argv[1]))
    out = decode(payload)
    json.dump(out, sys.stdout, indent=1)
